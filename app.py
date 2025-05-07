import os
import json
import logging
from flask import Flask, render_template, request, jsonify
from config import Config, get_project_root
from models.data_manager import DataManager
from models.subway_graph import SubwayGraph
from models.map_editor import MapEditor
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

# 获取项目根目录
PROJECT_ROOT = get_project_root()

# 确保数据目录存在
if not os.path.exists(Config.DATA_DIR):
    os.makedirs(Config.DATA_DIR)
# 确保地理数据目录存在
if not os.path.exists(Config.GEO_DATA_DIR):
    os.makedirs(Config.GEO_DATA_DIR)

# 初始化数据管理器 - 只使用实际需要的文件
data_manager = DataManager(
    stations_file=Config.STATIONS_FILE,
    lines_file=None,  # 这些文件未实际使用，设为None
    edges_file=None,
    schedules_file=None
)

# 辅助函数 - 加载数据并构建地铁网络
def _load_subway_graph():
    """加载站点、线路和边数据，并构建地铁网络"""
    stations = data_manager.load_stations()
    lines = []  # 如果不使用lines文件，提供空列表
    edges = []  # 如果不使用edges文件，提供空列表
    return SubwayGraph(stations, lines, edges)

# 主页路由
@app.route('/')
def index():
    return render_template('index.html', mapbox_token=Config.MAPBOX_TOKEN)

# 地图编辑页面路由
@app.route('/edit')
def edit_map():
    return render_template('edit_map.html', mapbox_token=Config.MAPBOX_TOKEN)

# 管理页面路由
@app.route('/admin')
def admin():
    return render_template('admin.html')

# 路径查询API
@app.route('/api/path/shortest_time', methods=['POST'])
def shortest_time_path():
    """API端点获取最短时间路径"""
    data = request.json
    start_station = data.get('start_station')
    end_station = data.get('end_station')
    date_type = data.get('date_type', '工作日')
    
    if not start_station or not end_station:
        return jsonify({'error': '起始站和终点站不能为空'}), 400
    
    try:
        from services.station_service import StationService
        from services.time_service import TimeService
        from services.time_path_service import TimePathService
        
        station_json_path = Config.STATION_DISTANCE_FILE
        time_file_path = Config.TIME_FILE
        
        station_service = StationService(data_file=station_json_path)
        time_service = TimeService(time_file_path, station_service)
        path_service = TimePathService(station_service, time_service)
        
        departure_time = datetime.now()
        
        path, total_time, time_details = path_service.find_optimized_shortest_time_path(
            start_station, end_station, departure_time, date_type
        )
        
        if not path:
            return jsonify({'error': f'无法找到从 {start_station} 到 {end_station} 的路径'}), 404
        
        transfers = path_service.count_transfers_correctly(path, time_details)
        total_actual_time = path_service.recalculate_time_with_backtracking(path, departure_time, time_details)
        
        total_distance_meters = 0
        for i in range(len(path) - 1):
            segment = (path[i], path[i+1])
            if segment in time_details:
                line = time_details[segment]['line']
                distance = station_service.get_distance(path[i], path[i+1], line)
                if distance > 0:
                    total_distance_meters += distance
        
        total_distance_km = total_distance_meters / 1000
        fare = path_service._calculate_fare(total_distance_km)
        
        formatted_result = path_service.format_path_details(path, time_details)
        
        import re
        pattern = r'总行程: .*站, \d+次换乘, [\d\.]+分钟'
        replacement = f'总行程: {len(path)}站, {transfers}次换乘, {total_actual_time:.1f}分钟'
        formatted_result = re.sub(pattern, replacement, formatted_result)
        
        json_time_details = {}
        for key, value in time_details.items():
            new_value = dict(value)
            if 'departure_time' in new_value:
                new_value['departure_time'] = new_value['departure_time'].isoformat()
            if 'arrival_time' in new_value:
                new_value['arrival_time'] = new_value['arrival_time'].isoformat()
            json_time_details[f"{key[0]},{key[1]}"] = new_value
        
        segments_info = []
        current_line = None
        transfer_points = []
        
        arrival_time = departure_time
        for i in range(len(path) - 1):
            segment = (path[i], path[i+1])
            if segment in time_details:
                details = time_details[segment]
                line = details['line']
                
                if current_line and current_line != line:
                    transfer_points.append({
                        'station': path[i],
                        'from_line': current_line,
                        'to_line': line
                    })
                
                current_line = line
                
                if 'arrival_time' in details:
                    arrival_time = details['arrival_time']
                
                segments_info.append({
                    'from_station': path[i],
                    'to_station': path[i+1],
                    'line': line,
                    'wait_time': details.get('wait_time', 0),
                    'travel_time': details.get('travel_time', 0),
                    'transfer_time': details.get('transfer_time', 0),
                    'departure_time': details.get('departure_time').isoformat() if 'departure_time' in details else None,
                    'arrival_time': details.get('arrival_time').isoformat() if 'arrival_time' in details else None,
                    'is_transfer': details.get('is_transfer', False)
                })
        
        total_wait_time = sum(details.get('wait_time', 0) for segment, details in time_details.items())
        total_transfer_time = sum(details.get('transfer_time', 0) for segment, details in time_details.items())
        total_travel_time = sum(details.get('travel_time', 0) for segment, details in time_details.items())
        total_stop_time = sum(details.get('stop_time', 0) for segment, details in time_details.items())
        
        return jsonify({
            'path': path,
            'total_time': round(total_actual_time, 1),
            'time_details': json_time_details,
            'transfers': transfers,
            'formatted_result': formatted_result,
            'distance_km': round(total_distance_km, 2),
            'fare': fare,
            'segments': segments_info,
            'transfer_points': transfer_points,
            'departure_time': departure_time.isoformat(),
            'arrival_time': arrival_time.isoformat(),
            'time_summary': {
                'wait_time': round(total_wait_time, 1),
                'transfer_time': round(total_transfer_time, 1),
                'travel_time': round(total_travel_time, 1),
                'stop_time': round(total_stop_time, 1)
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/path/least_transfers', methods=['POST'])
def least_transfers_path():
    """API端点获取最少换乘路径"""
    data = request.json
    start_station = data.get('start_station')
    end_station = data.get('end_station')
    
    if not start_station or not end_station:
        return jsonify({'error': '起始站和终点站不能为空'}), 400
    
    try:
        from services.station_service import StationService
        from services.time_service import TimeService
        from services.transfer_path_service import TransferPathService
        from datetime import datetime
        
        station_json_path = Config.STATION_DISTANCE_FILE
        time_file_path = Config.TIME_FILE
        
        station_service = StationService(data_file=station_json_path)
        
        if not station_service.get_station_info(start_station):
            return jsonify({'error': f'起始站 {start_station} 不存在于地铁网络中'}), 404
            
        if not station_service.get_station_info(end_station):
            return jsonify({'error': f'终点站 {end_station} 不存在于地铁网络中'}), 404
        
        try:
            time_service = TimeService(time_file_path, station_service)
            transfer_path_service = TransferPathService(station_service, time_service)
            
            departure_time = datetime.now()
            
            day_of_week = departure_time.weekday()
            date_type = '工作日' if day_of_week < 5 else '双休日'
            
            path, total_time, time_details = transfer_path_service.find_least_transfers_path(
                start_station, end_station, departure_time, date_type
            )
            
            if not path:
                return jsonify({'error': f'无法找到从 {start_station} 到 {end_station} 的最少换乘路径'}), 404
            
            transfers = transfer_path_service.count_transfers_correctly(path, time_details)
            
            total_distance_meters = 0
            for i in range(len(path) - 1):
                from_station = path[i]
                to_station = path[i+1]
                
                line = None
                for segment, details in time_details.items():
                    if segment[0] == from_station and segment[1] == to_station:
                        line = details['line']
                        break
                
                if line:
                    distance = station_service.get_distance(from_station, to_station, line)
                    if distance > 0:
                        total_distance_meters += distance
            
            total_distance_km = total_distance_meters / 1000
            fare = transfer_path_service._calculate_fare(total_distance_km)
            
            total_actual_time = transfer_path_service.recalculate_time_with_backtracking(path, departure_time, time_details)
            
            formatted_result = transfer_path_service.format_path_details(path, time_details)
            
            import re
            pattern = r'总行程: .*站, \d+次换乘, [\d\.]+分钟'
            replacement = f'总行程: {len(path)}站, {transfers}次换乘, {total_actual_time:.1f}分钟'
            formatted_result = re.sub(pattern, replacement, formatted_result)
            
            json_time_details = {}
            for key, value in time_details.items():
                new_value = dict(value)
                if 'departure_time' in new_value:
                    new_value['departure_time'] = new_value['departure_time'].isoformat()
                if 'arrival_time' in new_value:
                    new_value['arrival_time'] = new_value['arrival_time'].isoformat()
                json_time_details[f"{key[0]},{key[1]}"] = new_value
            
            segments_info = []
            current_line = None
            transfer_points = []
            
            arrival_time = departure_time
            for i in range(len(path) - 1):
                segment = (path[i], path[i+1])
                if segment in time_details:
                    details = time_details[segment]
                    line = details['line']
                    
                    if current_line and current_line != line:
                        transfer_points.append({
                            'station': path[i],
                            'from_line': current_line,
                            'to_line': line
                        })
                    
                    current_line = line
                    
                    if 'arrival_time' in details:
                        arrival_time = details['arrival_time']
                    
                    segments_info.append({
                        'from_station': path[i],
                        'to_station': path[i+1],
                        'line': line,
                        'wait_time': details.get('wait_time', 0),
                        'travel_time': details.get('travel_time', 0),
                        'transfer_time': details.get('transfer_time', 0),
                        'departure_time': details.get('departure_time').isoformat() if 'departure_time' in details else None,
                        'arrival_time': details.get('arrival_time').isoformat() if 'arrival_time' in details else None,
                        'is_transfer': details.get('is_transfer', False)
                    })
            
            return jsonify({
                'path': path,
                'transfers': transfers,
                'total_time': round(total_actual_time, 1),
                'formatted_result': formatted_result,
                'time_details': json_time_details,
                'distance_km': round(total_distance_km, 2),
                'fare': fare,
                'segments': segments_info,
                'transfer_points': transfer_points,
                'departure_time': departure_time.isoformat(),
                'arrival_time': arrival_time.isoformat(),
                'time_summary': {
                    'wait_time': round(sum(details.get('wait_time', 0) for segment, details in time_details.items()), 1),
                    'transfer_time': round(sum(details.get('transfer_time', 0) for segment, details in time_details.items()), 1),
                    'travel_time': round(sum(details.get('travel_time', 0) for segment, details in time_details.items()), 1),
                    'stop_time': round(sum(details.get('stop_time', 0) for segment, details in time_details.items()), 1)
                }
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# 站点GeoJSON数据API
@app.route('/api/stations/points', methods=['GET'])
def get_station_points():
    try:
        point_json_path = os.path.join(Config.GEO_DATA_DIR, 'point.json')
        logging.info(f"访问站点数据文件: {point_json_path}")
        
        if not os.path.exists(point_json_path):
            logging.warning(f"站点数据文件不存在: {point_json_path}")
            return jsonify({
                "type": "FeatureCollection",
                "features": []
            })
            
        with open(point_json_path, 'r', encoding='utf-8') as f:
            geo_data = json.load(f)
            logging.info(f"成功加载站点数据: {len(geo_data.get('features', []))}个站点")
        
        return jsonify(geo_data)
    except Exception as e:
        logging.error(f"站点API错误: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# 线路GeoJSON数据API
@app.route('/api/stations/lines', methods=['GET'])
def get_line_geojson():
    try:
        line_geojson_file = os.path.join(Config.GEO_DATA_DIR, 'line.geojson')
        logging.info(f"访问线路数据文件: {line_geojson_file}")
        
        # 在日志中添加文件是否存在的信息，帮助调试
        if os.path.exists(line_geojson_file):
            logging.info(f"线路数据文件存在，大小: {os.path.getsize(line_geojson_file)} 字节")
        else:
            logging.warning(f"线路数据文件不存在: {line_geojson_file}")
            return jsonify({
                "type": "FeatureCollection",
                "features": []
            })
            
        with open(line_geojson_file, 'r', encoding='utf-8') as f:
            lines_data = json.load(f)
            logging.info(f"成功加载线路数据: {len(lines_data.get('features', []))}条线路")
            
        return jsonify(lines_data)
    except Exception as e:
        logging.error(f"获取线路数据失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# 地图编辑API - 添加站点
@app.route('/api/edit/stations', methods=['POST'])
def add_station():
    data = request.json
    station_name = data.get('name')
    line_name = data.get('line')
    coordinates = data.get('coordinates')

    subway_graph = _load_subway_graph()
    map_editor = MapEditor(subway_graph)
    result = map_editor.add_station(station_name, line_name, coordinates)

    if result["success"] == True:
        data_manager.save_stations(subway_graph.stations)
        data_manager.save_lines(subway_graph.lines)
    return jsonify(result)

# 地图编辑API - 删除站点
@app.route('/api/edit/stations/<station_name>', methods=['DELETE'])
def delete_station(station_name):
    subway_graph = _load_subway_graph()
    map_editor = MapEditor(subway_graph)
    result = map_editor.remove_station(station_name)

    if result["success"] == True:
        data_manager.save_stations(subway_graph.stations)
        data_manager.save_edges(subway_graph.edges)
    return jsonify(result)

# 地图编辑API - 更新站点
@app.route('/api/edit/stations/<station_name>', methods=['PUT'])
def update_station(station_name):
    data = request.json
    new_name = data.get('new_name')
    coordinates = data.get('coordinates')

    subway_graph = _load_subway_graph()
    map_editor = MapEditor(subway_graph)
    result = map_editor.update_station(station_name, new_name, coordinates)

    if result["success"] == True:
        data_manager.save_stations(subway_graph.stations)
    return jsonify(result)

# 地图编辑API - 添加连接
@app.route('/api/edit/connections', methods=['POST'])
def add_connection():
    data = request.json
    station1 = data.get('station1')
    station2 = data.get('station2')
    line_name = data.get('line')
    distance = data.get('distance')
    time = data.get('time')

    subway_graph = _load_subway_graph()
    map_editor = MapEditor(subway_graph)
    result = map_editor.add_connection(station1, station2, line_name, distance, time)

    if result["success"] == True:
        data_manager.save_edges(subway_graph.edges)
    return jsonify(result)

# 地图编辑API - 删除线路
@app.route('/api/edit/lines/<line_name>', methods=['DELETE'])
def delete_edit_line(line_name):
    try:
        subway_graph = _load_subway_graph()
        map_editor = MapEditor(subway_graph)
        result = map_editor.remove_line(line_name)
        
        if result["success"] == True:
            data_manager.save_lines(subway_graph.lines)
            data_manager.save_stations(subway_graph.stations)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"删除线路时出错: {str(e)}"})

# 地图编辑API - 获取线路详情
@app.route('/api/edit/lines/<line_name>', methods=['GET'])
def get_line_details(line_name):
    subway_graph = _load_subway_graph()
    map_editor = MapEditor(subway_graph)
    result = map_editor.get_line_details(line_name)
    return jsonify(result)

# 地图编辑API - 更新线路坐标
@app.route('/api/edit/lines/<line_name>/coordinates', methods=['PUT'])
def update_line_coordinates(line_name):
    data = request.json
    coordinates = data.get('coordinates', [])
    
    subway_graph = _load_subway_graph()
    map_editor = MapEditor(subway_graph)
    result = map_editor.update_line_coordinates(line_name, coordinates)
    
    if result["success"] == True:
        data_manager.save_lines(subway_graph.lines)
    return jsonify(result)

# 地图编辑API - 添加线路
@app.route('/api/edit/lines', methods=['POST'])
def add_line_api():
    try:
        data = request.json
        
        line_name = data.get('line_name')
        color = data.get('color')
        stations = data.get('stations', [])
        station_connections = data.get('station_connections', [])
        start_station = data.get('start_station')
        end_station = data.get('end_station')
        timetable_data = data.get('timetable_data', {})
        avg_speed = data.get('avg_speed')
        
        logging.info(f"添加线路: {line_name}, 站点数: {len(stations)}, 连接数: {len(station_connections)}")
        
        # 加载地铁图
        subway_graph = _load_subway_graph()
        map_editor = MapEditor(subway_graph)
        
        # 添加线路到系统
        result = map_editor.add_line(line_name, color, stations, station_connections)
        if not result["success"]:
            logging.error(f"添加线路失败: {result['message']}")
            return jsonify(result)
        
        # 添加站点连接关系
        for connection in station_connections:
            from_station = connection.get('from')
            to_station = connection.get('to')
            distance = connection.get('distance')
            
            connect_result = map_editor.add_connection(from_station, to_station, line_name, distance)
            if not connect_result["success"]:
                logging.warning(f"添加连接失败: {from_station} -> {to_station}: {connect_result['message']}")
        
        # 更新线路GeoJSON
        geo_result = map_editor.update_line_geojson(line_name, color, stations)
        if not geo_result["success"]:
            logging.warning(f"更新线路GeoJSON失败: {geo_result['message']}")
        
        # 保存时刻表数据
        if timetable_data:
            try:
                timetable_result = map_editor.save_timetable(line_name, start_station, end_station, timetable_data)
                if not timetable_result.get("success", False):
                    logging.warning(f"保存时刻表失败: {timetable_result.get('message', '未知错误')}")
            except AttributeError:
                logging.warning(f"保存时刻表方法不存在，跳过时刻表保存")
            except Exception as e:
                logging.warning(f"保存时刻表时发生错误: {str(e)}")
        
        # 更新线路速度
        if avg_speed and isinstance(avg_speed, (int, float)) and avg_speed > 0:
            try:
                success = update_line_speed(line_name, float(avg_speed))
                if not success:
                    logging.warning(f"更新线路 {line_name} 的平均速度失败")
            except Exception as e:
                logging.error(f"处理线路速度时出错: {str(e)}", exc_info=True)
        
        # 保存修改后的数据
        data_manager.save_stations(subway_graph.stations)
        data_manager.save_lines(subway_graph.lines)
        data_manager.save_edges(subway_graph.edges)
        
        # 确保地图数据保存成功
        logging.info(f"线路 {line_name} 添加成功，已保存所有相关数据")
        
        return jsonify({
            'success': True, 
            'message': f'线路 "{line_name}" 添加成功。',
            'details': {
                'stations_count': len(stations),
                'connections_count': len(station_connections)
            }
        })
        
    except Exception as e:
        logging.error(f"添加线路 API 处理失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'添加线路失败: {str(e)}'})

def update_line_speed(line_name, speed):
    try:
        import re
        from config import Config
        
        base_line_name = line_name
        if '(' in base_line_name:
            base_line_name = base_line_name.split('(')[0].strip()
        
        if "地铁" in base_line_name and "号线" in base_line_name:
            base_line_name = re.sub(r'^地铁', '', base_line_name)
            
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        pattern = r'(LINE_AVG_SPEEDS\s*=\s*{)(.*?)(})'
        match = re.search(pattern, config_content, re.DOTALL)
        
        if not match:
            return False

        dict_start = match.group(1)
        dict_content = match.group(2)
        dict_end = match.group(3)
            
        line_pattern = rf'"{re.escape(base_line_name)}"\s*:\s*\d+\.?\d*'
        if re.search(line_pattern, dict_content):
            dict_content = re.sub(line_pattern, f'"{base_line_name}": {speed}', dict_content)
        else:
            if dict_content.strip() and not dict_content.rstrip().endswith(','):
                dict_content += ','
            dict_content += f'\n        "{base_line_name}": {speed},'
        
        new_config_content = config_content.replace(match.group(0), f"{dict_start}{dict_content}{dict_end}")
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(new_config_content)
            
        Config.LINE_AVG_SPEEDS[base_line_name] = speed
        
        return True
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    app.run(debug=True)




