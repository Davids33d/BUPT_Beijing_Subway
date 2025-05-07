import json
import os
import uuid
import logging  # 添加 logging
from config import Config, get_project_root

class MapEditor:
    """地铁地图编辑器，提供地铁网络编辑功能"""
    
    def __init__(self, subway_graph):
        """初始化地图编辑器"""
        self.subway_graph = subway_graph
        self.project_root = get_project_root()
        self.station_distance_file = Config.STATION_DISTANCE_FILE
        self.time_data_file = Config.TIME_FILE
    
    def add_station(self, station_name, line_name, coordinates_str):
        """添加新站点"""
        try:
            # 检查站点名称
            if not station_name or not line_name or not coordinates_str:
                return {"success": False, "message": "站点名称、线路名称和坐标不能为空"}
            
            # 检查站点是否已存在 - 适用于列表结构
            if isinstance(self.subway_graph.stations, list):
                for station in self.subway_graph.stations:
                    if station.get('name') == station_name:
                        return {"success": False, "message": f"站点 '{station_name}' 已存在"}
            else:  # 兼容字典结构
                for station_id, station in self.subway_graph.stations.items():
                    if station.get('name') == station_name:
                        return {"success": False, "message": f"站点 '{station_name}' 已存在"}
            
            # 解析坐标
            try:
                longitude, latitude = map(float, coordinates_str.split(','))
            except (ValueError, TypeError):
                return {"success": False, "message": "坐标格式错误，应为'经度,纬度'"}
            
            # 创建新站点
            station_id = str(uuid.uuid4())
            new_station = {
                "id": station_id,
                "name": station_name,
                "location": coordinates_str,
                "lines": [line_name],
                "status": "运营中"
            }
            
            # 添加到地铁图 - 根据数据结构选择添加方式
            if isinstance(self.subway_graph.stations, list):
                self.subway_graph.stations.append(new_station)
            else:  # 兼容字典结构
                self.subway_graph.stations[station_id] = new_station
            
            # 更新线路信息
            self.update_line_info(line_name, station_id)
            
            # 同时将站点添加到point.json文件
            result = self.add_station_to_point_json(station_name, line_name, longitude, latitude)
            if not result:
                return {"success": False, "message": "添加站点到point.json文件失败"}
            
            return {"success": True, "message": f"站点 '{station_name}' 添加成功"}
        except Exception as e:
            print(f"添加站点异常: {str(e)}")
            return {"success": False, "message": f"添加站点失败: {str(e)}"}
    
    def update_line_info(self, line_name, station_id):
        """更新线路信息，添加站点到线路中"""
        try:
            # 检查线路是否存在
            if isinstance(self.subway_graph.lines, dict):
                if line_name in self.subway_graph.lines:
                    if 'stations' not in self.subway_graph.lines[line_name]:
                        self.subway_graph.lines[line_name]['stations'] = []
                    
                    if station_id not in self.subway_graph.lines[line_name]['stations']:
                        self.subway_graph.lines[line_name]['stations'].append(station_id)
                else:
                    # 创建新线路
                    self.subway_graph.lines[line_name] = {
                        'name': line_name, 
                        'stations': [station_id]
                    }
            elif isinstance(self.subway_graph.lines, list):
                # 如果lines是列表，查找对应线路
                line_found = False
                for line in self.subway_graph.lines:
                    if line.get('name') == line_name:
                        if 'stations' not in line:
                            line['stations'] = []
                        
                        if station_id not in line['stations']:
                            line['stations'].append(station_id)
                        line_found = True
                        break
                
                if not line_found:
                    # 创建新线路并添加到列表
                    self.subway_graph.lines.append({
                        'name': line_name,
                        'stations': [station_id]
                    })
        except Exception as e:
            print(f"更新线路信息失败: {str(e)}")
    
    def add_station_to_point_json(self, station_name, line_name, longitude, latitude):
        """将站点添加到point.json文件"""
        try:
            # 获取point.json文件路径
            point_json_path = os.path.join(Config.DATA_DIR, 'point.json')
            
            # 读取现有数据
            with open(point_json_path, 'r', encoding='utf-8') as f:
                geo_data = json.load(f)
            
            # 创建新站点Feature
            new_feature = {
                "type": "Feature",
                "properties": {
                    "station_name": station_name,
                    "lines": [line_name],
                    "status": "运营中",
                    "line_siz": 1
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [longitude, latitude]
                }
            }
            
            # 添加到features列表
            geo_data["features"].append(new_feature)
            
            # 保存回文件
            with open(point_json_path, 'w', encoding='utf-8') as f:
                json.dump(geo_data, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"保存站点到point.json失败: {str(e)}")
            return False
    
    def add_connection(self, station1, station2, line_name, distance=None, time=None):
        """添加站点间连接"""
        try:
            self.subway_graph.add_connection(station1, station2, line_name, distance, time)
            
            # 如果提供了距离信息，同时更新站点距离数据
            if distance is not None:
                self.add_station_distance(station1, station2, line_name, distance)
                
            return {"success": True, "message": f"已添加连接: {station1} - {station2}"}
        except Exception as e:
            return {"success": False, "message": f"添加连接失败: {str(e)}"}
    
    def remove_station(self, station_name):
        """从系统和point.json文件中删除站点"""
        try:
            # 从系统数据中删除站点
            station_id_to_remove = None
            station_found = False
            
            # 处理列表格式的站点数据
            if isinstance(self.subway_graph.stations, list):
                for i, station in enumerate(self.subway_graph.stations):
                    if station.get('name') == station_name or station.get('station_name') == station_name:
                        station_id_to_remove = station.get('id')
                        self.subway_graph.stations.pop(i)
                        station_found = True
                        break
            # 处理字典格式的站点数据
            elif isinstance(self.subway_graph.stations, dict):
                for station_id, station in self.subway_graph.stations.items():
                    if station.get('name') == station_name or station.get('station_name') == station_name:
                        station_id_to_remove = station_id
                        station_found = True
                        break
                
                if station_found:
                    del self.subway_graph.stations[station_id_to_remove]
            
            if not station_found:
                return {"success": False, "message": f"站点 '{station_name}' 未找到"}
            
            # 从线路中删除站点引用
            if isinstance(self.subway_graph.lines, list):
                for line in self.subway_graph.lines:
                    if 'stations' in line and station_id_to_remove in line['stations']:
                        line['stations'].remove(station_id_to_remove)
            elif isinstance(self.subway_graph.lines, dict):
                for line_id, line in self.subway_graph.lines.items():
                    if 'stations' in line and station_id_to_remove in line['stations']:
                        line['stations'].remove(station_id_to_remove)
            
            # 删除与该站点相关的连接
            edges_to_remove = []
            if isinstance(self.subway_graph.edges, dict):
                for edge_id, edge in self.subway_graph.edges.items():
                    if edge['source'] == station_id_to_remove or edge['target'] == station_id_to_remove:
                        edges_to_remove.append(edge_id)
                
                for edge_id in edges_to_remove:
                    del self.subway_graph.edges[edge_id]
            elif isinstance(self.subway_graph.edges, list):
                self.subway_graph.edges = [
                    edge for edge in self.subway_graph.edges 
                    if edge.get('source') != station_id_to_remove and edge.get('target') != station_id_to_remove
                ]
            
            # 从point.json文件中删除站点
            self.remove_station_from_point_json(station_name)
            
            return {"success": True, "message": f"站点 '{station_name}' 已成功删除"}
        except Exception as e:
            print(f"删除站点失败: {str(e)}")
            return {"success": False, "message": f"删除站点失败: {str(e)}"}
    
    def remove_station_from_point_json(self, station_name):
        """从point.json文件中删除指定站点"""
        try:
            point_json_path = os.path.join(Config.DATA_DIR, 'point.json')
            
            # 读取现有数据
            with open(point_json_path, 'r', encoding='utf-8') as f:
                geo_data = json.load(f)
            
            # 查找并删除匹配的站点
            original_feature_count = len(geo_data["features"])
            geo_data["features"] = [
                feature for feature in geo_data["features"] 
                if feature.get("properties", {}).get("station_name") != station_name
            ]
            
            # 如果删除了站点，保存回文件
            if len(geo_data["features"]) < original_feature_count:
                with open(point_json_path, 'w', encoding='utf-8') as f:
                    json.dump(geo_data, f, ensure_ascii=False, indent=2)
                return True
            else:
                print(f"在point.json中未找到站点: {station_name}")
                return False
        except Exception as e:
            print(f"从point.json删除站点失败: {str(e)}")
            return False
    
    def update_station(self, station_name, new_name=None, coordinates=None):
        """更新站点信息"""
        try:
            self.subway_graph.update_station(station_name, new_name, coordinates)
            return {"success": True, "message": f"已更新站点: {station_name}"}
        except Exception as e:
            return {"success": False, "message": f"更新站点失败: {str(e)}"}
            
    def add_line(self, line_name, line_color, stations, connections):
        """添加一条新线路，并更新GeoJSON和站点距离数据
        
        Args:
            line_name: 线路名称
            line_color: 线路颜色
            stations: 该线路上的站点列表，按顺序排列
            connections: 站点连接列表，格式为 [{'from': s1, 'to': s2, 'distance': d}, ...]
            
        Returns:
            dict: 操作结果
        """
        try:
            # 1. 更新线路 GeoJSON
            geojson_result = self.update_line_geojson(line_name, line_color, stations)
            if not geojson_result["success"]:
                # 如果GeoJSON更新失败（例如线路已存在），则直接返回错误
                return geojson_result
            
            # 2. 更新 SubwayGraph 中的线路信息 (如果需要)
            #    根据 SubwayGraph 的具体实现来决定如何添加或更新线路
            #    这里的调用假设 add_line 接受颜色、起始站和终点站
            if hasattr(self.subway_graph, 'add_line'):
                 self.subway_graph.add_line(
                     line_name, 
                     color=line_color, 
                     start_station=stations[0] if stations else None, 
                     end_station=stations[-1] if stations else None
                 )
            
            # 3. 更新站点距离数据 (station.json)
            if not connections:
                 logging.warning(f"线路 '{line_name}' 没有提供连接信息，station.json 可能未更新距离。")
                 # 即使没有连接信息，也认为线路添加成功（GeoJSON已更新）
                 return {"success": True, "message": f"成功添加线路 {line_name} 到GeoJSON，但未提供连接信息。"}

            # 加载现有站点距离数据
            stations_data = self.load_station_distance_data()
            
            # 逐个添加或更新连接和距离
            connections_updated_count = 0
            for conn in connections:
                from_station = conn.get('from')
                to_station = conn.get('to')
                distance = conn.get('distance')

                if not from_station or not to_station or distance is None:
                    logging.warning(f"线路 '{line_name}' 的连接信息不完整: {conn}，跳过此连接。")
                    continue

                # 使用内部方法添加或更新双向距离
                self._add_or_update_station_distance(stations_data, from_station, line_name, [(to_station, distance)])
                # _add_or_update_station_distance 内部会调用 _update_connected_station_distance 处理反向
                connections_updated_count += 1

            # 保存更新后的 station.json 数据
            self.save_station_distance_data(stations_data)
            
            logging.info(f"线路 '{line_name}': 成功更新 {connections_updated_count} 个连接的距离信息到 station.json。")
            
            return {"success": True, "message": f"成功添加线路 {line_name} 并更新了 {connections_updated_count} 个连接的距离信息。"}
            
        except Exception as e:
            logging.error(f"添加线路 '{line_name}' 失败: {str(e)}", exc_info=True) # 使用 logging 记录详细错误
            return {"success": False, "message": f"添加线路失败: {str(e)}"}
    
    def update_line_geojson(self, line_name, line_color, stations):
        """更新线路的GeoJSON数据
        
        Args:
            line_name: 线路名称
            line_color: 线路颜色
            stations: 站点序列
            
        Returns:
            dict: 操作结果
        """
        try:
            # 获取文件路径
            point_json_path = os.path.join(Config.DATA_DIR, 'point.json')
            line_geojson_path = os.path.join(Config.DATA_DIR, 'line.geojson')
            
            # 读取站点数据
            with open(point_json_path, 'r', encoding='utf-8') as f:
                point_data = json.load(f)
            
            # 创建站点名称到坐标的映射
            station_coords = {}
            for feature in point_data.get('features', []):
                props = feature.get('properties', {})
                station_name = props.get('station_name')
                if station_name:
                    station_coords[station_name] = feature.get('geometry', {}).get('coordinates', [])
            
            # 检查所有站点是否存在
            missing_stations = []
            for station in stations:
                if station not in station_coords:
                    missing_stations.append(station)
            
            if missing_stations:
                return {"success": False, "message": f"以下站点在系统中不存在: {', '.join(missing_stations)}"}
            
            # 提取站点坐标
            line_coordinates = [station_coords[station] for station in stations]
            
            # 读取线路GeoJSON数据
            try:
                with open(line_geojson_path, 'r', encoding='utf-8') as f:
                    line_geojson = json.load(f)
            except FileNotFoundError:
                # 如果文件不存在，创建基本结构
                line_geojson = {
                    "type": "FeatureCollection",
                    "features": []
                }
            
            # 检查是否已存在同名线路
            for feature in line_geojson.get('features', []):
                props = feature.get('properties', {})
                if props.get('line_name') == line_name:
                    return {"success": False, "message": f"线路 '{line_name}' 已存在于GeoJSON文件中"}
            
            # 生成新的ID
            max_id = 0
            for feature in line_geojson.get('features', []):
                if 'id' in feature and isinstance(feature['id'], int) and feature['id'] > max_id:
                    max_id = feature['id']
            new_id = max_id + 1
            
            # 创建新的线路Feature
            new_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": line_coordinates
                },
                "properties": {
                    "key_name": line_name,
                    "line_name": line_name,
                    "front_name": stations[0],  # 起始站
                    "terminal_name": stations[-1],  # 终点站
                    "status": "运营中",
                    "stroke": line_color,
                    "stroke-width": 5,
                    "stroke-opacity": 1
                },
                "id": new_id
            }
            
            # 添加到features列表
            line_geojson['features'].append(new_feature)
            
            # 保存回文件
            with open(line_geojson_path, 'w', encoding='utf-8') as f:
                json.dump(line_geojson, f, ensure_ascii=False, indent=2)
            
            return {"success": True, "message": f"已将线路 '{line_name}' 添加到GeoJSON文件"}
        except Exception as e:
            print(f"更新线路GeoJSON失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"更新线路GeoJSON失败: {str(e)}"}
    
    def remove_connection(self, station1, station2):
        """删除站点间连接"""
        try:
            self.subway_graph.remove_connection(station1, station2)
            return {"success": True, "message": f"已删除连接: {station1} - {station2}"}
        except Exception as e:
            return {"success": False, "message": f"删除连接失败: {str(e)}"}
    
    def save_map(self, filename):
        """保存地铁地图到文件"""
        try:
            self.subway_graph.save_to_file(filename)
            return {"success": True, "message": f"地铁地图已保存到: {filename}"}
        except Exception as e:
            return {"success": False, "message": f"保存地图失败: {str(e)}"}
    
    def load_map(self, filename):
        """从文件加载地铁地图"""
        try:
            self.subway_graph.load_from_file(filename)
            return {"success": True, "message": f"已从文件加载地铁地图: {filename}"}
        except Exception as e:
            return {"success": False, "message": f"加载地图失败: {str(e)}"}
    
    # 新增：站点距离相关功能
    
    def load_station_distance_data(self):
        """加载站点距离数据文件"""
        if os.path.exists(self.station_distance_file):
            with open(self.station_distance_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_station_distance_data(self, data):
        """保存站点距离数据到文件"""
        with open(self.station_distance_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_station_distance(self, station_name, connected_station, line_name, distance):
        """添加或更新站点之间的距离信息
        
        Args:
            station_name: 起始站点名称
            connected_station: 相邻站点名称
            line_name: 线路名称
            distance: 两站之间的距离(米)
            
        Returns:
            dict: 操作结果
        """
        try:
            # 加载现有站点距离数据
            stations_data = self.load_station_distance_data()
            
            # 添加或更新站点距离信息
            self._add_or_update_station_distance(stations_data, station_name, line_name, [(connected_station, distance)])
            
            # 保存更新后的数据
            self.save_station_distance_data(stations_data)
            
            return {"success": True, "message": f"已添加站点距离信息: {station_name} - {connected_station} ({distance}米)"}
        except Exception as e:
            return {"success": False, "message": f"添加站点距离信息失败: {str(e)}"}
    
    def add_multiple_station_distances(self, station_name, line_name, connected_stations):
        """添加或更新站点与多个相邻站点之间的距离信息
        
        Args:
            station_name: 站点名称
            line_name: 线路名称
            connected_stations: 相邻站点列表，每个元素为(站点名,距离)
            
        Returns:
            dict: 操作结果
        """
        try:
            # 加载现有站点距离数据
            stations_data = self.load_station_distance_data()
            
            # 添加或更新站点距离信息
            self._add_or_update_station_distance(stations_data, station_name, line_name, connected_stations)
            
            # 保存更新后的数据
            self.save_station_distance_data(stations_data)
            
            return {"success": True, "message": f"已添加站点 {station_name} 的多个距离信息"}
        except Exception as e:
            return {"success": False, "message": f"添加多个站点距离信息失败: {str(e)}"}
    
    def _add_or_update_station_distance(self, stations_data, station_name, line_name, connected_stations):
        """添加或更新站点距离信息的内部实现 (确保日志记录)
        
        Args:
            stations_data: 现有站点数据
            station_name: 站点名称
            line_name: 线路名称
            connected_stations: 相邻站点列表，每个元素为(站点名,距离)
        """
        # 检查站点是否已存在
        if station_name in stations_data:
            # 站点已存在，更新信息
            station_info = stations_data[station_name]
            
            # 确保 'lines' 和 'edge' 键存在且是列表
            if "lines" not in station_info or not isinstance(station_info["lines"], list):
                station_info["lines"] = []
            if "edge" not in station_info or not isinstance(station_info["edge"], list):
                 station_info["edge"] = []
            
            # 检查线路是否已在lines列表中
            if line_name not in station_info["lines"]:
                station_info["lines"].append(line_name)
                station_info["line_siz"] = len(station_info["lines"]) # 更新 line_siz
                logging.debug(f"站点 '{station_name}': 添加线路 '{line_name}' 到列表，line_siz 更新为 {station_info['line_siz']}")

            # 更新edge信息
            for connected_station, distance in connected_stations:
                # 检查是否已有此相邻站点的连接
                existing_edge = False
                for edge in station_info["edge"]:
                    if edge.get("station") == connected_station and edge.get("line") == line_name:
                        # 已存在此连接，更新距离
                        if edge.get("distance") != distance:
                             edge["distance"] = distance
                             logging.debug(f"站点 '{station_name}': 更新到 '{connected_station}' ({line_name}) 的距离为 {distance}")
                        existing_edge = True
                        break
                
                # 如果不存在此连接，添加新连接
                if not existing_edge:
                    new_edge = {
                        "station": connected_station,
                        "line": line_name,
                        "distance": distance
                    }
                    station_info["edge"].append(new_edge)
                    logging.debug(f"站点 '{station_name}': 添加新连接到 '{connected_station}' ({line_name}), 距离 {distance}")

                # 同时更新相邻站点的信息（双向连接）
                self._update_connected_station_distance(stations_data, connected_station, station_name, line_name, distance)
        else:
            # 创建新站点
            logging.debug(f"站点 '{station_name}': 在 station.json 中创建新条目")
            new_station = {
                "edge": [],
                "lines": [line_name],
                "line_siz": 1
            }
            
            # 添加相邻站点信息
            for connected_station, distance in connected_stations:
                 new_edge = {
                     "station": connected_station,
                     "line": line_name,
                     "distance": distance
                 }
                 new_station["edge"].append(new_edge)
                 logging.debug(f"站点 '{station_name}': 添加新连接到 '{connected_station}' ({line_name}), 距离 {distance}")

                 # 同时更新相邻站点的信息（双向连接）
                 self._update_connected_station_distance(stations_data, connected_station, station_name, line_name, distance)
            
            stations_data[station_name] = new_station
    
    def _update_connected_station_distance(self, stations_data, station_name, connected_to, line_name, distance):
        """更新相邻站点的距离信息，确保双向连接 (确保日志记录)
        
        Args:
            stations_data: 站点数据
            station_name: 要更新的站点名 (即 connected_station)
            connected_to: 连接到的站点名 (即 station_name)
            line_name: 线路名称
            distance: 两站间距离
        """
        # 如果相邻站点不存在，创建新站点
        if station_name not in stations_data:
            logging.debug(f"站点 '{station_name}' (相邻站): 在 station.json 中创建新条目以建立反向连接")
            stations_data[station_name] = {
                "edge": [{
                    "station": connected_to,
                    "line": line_name,
                    "distance": distance
                }],
                "lines": [line_name],
                "line_siz": 1
            }
            logging.debug(f"站点 '{station_name}': 添加反向连接到 '{connected_to}' ({line_name}), 距离 {distance}")
            return
        
        # 站点已存在
        station_info = stations_data[station_name]

        # 确保 'lines' 和 'edge' 键存在且是列表
        if "lines" not in station_info or not isinstance(station_info["lines"], list):
            station_info["lines"] = []
        if "edge" not in station_info or not isinstance(station_info["edge"], list):
            station_info["edge"] = []

        # 检查线路是否已在lines列表中
        if line_name not in station_info["lines"]:
            station_info["lines"].append(line_name)
            station_info["line_siz"] = len(station_info["lines"]) # 更新 line_siz
            logging.debug(f"站点 '{station_name}' (相邻站): 添加线路 '{line_name}' 到列表，line_siz 更新为 {station_info['line_siz']}")

        # 检查是否已有与connected_to站点的连接
        existing_edge = False
        for edge in station_info["edge"]:
            if edge.get("station") == connected_to and edge.get("line") == line_name:
                # 已存在此连接，更新距离
                if edge.get("distance") != distance:
                    edge["distance"] = distance
                    logging.debug(f"站点 '{station_name}' (相邻站): 更新到 '{connected_to}' ({line_name}) 的反向距离为 {distance}")
                existing_edge = True
                break
        
        # 如果不存在此连接，添加新连接
        if not existing_edge:
            new_edge = {
                "station": connected_to,
                "line": line_name,
                "distance": distance
            }
            station_info["edge"].append(new_edge)
            logging.debug(f"站点 '{station_name}' (相邻站): 添加新反向连接到 '{connected_to}' ({line_name}), 距离 {distance}")

    def interactive_add_station_distances(self):
        """交互式添加站点间距离信息
        
        这是add_station_distances.py中main函数的集成版本，
        允许用户通过交互方式添加站点间的距离信息
        """
        print("=== 地铁线路站点距离信息添加 ===")
        
        # 获取线路名称
        line_name = input("请输入线路名称（例如：地铁1号线八通线(环球度假区--福寿岭)）：")
        
        # 加载现有站点距离数据
        stations_data = self.load_station_distance_data()
        
        # 获取站点信息
        while True:
            station_name = input("\n请输入站点名称（输入'完成'结束）：")
            if station_name == "完成":
                break
            
            connected_stations = []
            print(f"\n正在添加 {station_name} 的相邻站点信息...")
            
            while True:
                connected_station = input("请输入相邻站点名称（输入'完成'结束当前站点的添加）：")
                if connected_station == "完成":
                    break
                
                while True:
                    try:
                        distance = int(input(f"请输入 {station_name} 到 {connected_station} 的距离（米）："))
                        break
                    except ValueError:
                        print("请输入有效的整数距离！")
                
                connected_stations.append((connected_station, distance))
            
            # 添加或更新站点信息
            self._add_or_update_station_distance(stations_data, station_name, line_name, connected_stations)
            print(f"站点 {station_name} 信息已添加/更新")
        
        # 保存更新后的数据
        self.save_station_distance_data(stations_data)
        print("\n所有站点信息已保存到文件。")
        
        return {"success": True, "message": "站点距离信息添加完成"}

    def remove_line_from_geojson(self, line_name):
        """从线路GeoJSON文件中删除指定线路
        
        Args:
            line_name: 要删除的线路名称
            
        Returns:
            dict: 操作结果
        """
        try:
            # 获取文件路径
            line_geojson_path = os.path.join(Config.DATA_DIR, 'line.geojson')
            
            # 检查文件是否存在
            if not os.path.exists(line_geojson_path):
                return {"success": False, "message": f"线路GeoJSON文件不存在: {line_geojson_path}"}
            
            # 读取线路GeoJSON数据
            with open(line_geojson_path, 'r', encoding='utf-8') as f:
                line_geojson = json.load(f)
            
            # 记录原始特征数量
            original_count = len(line_geojson.get('features', []))
            
            # 查找并删除匹配的线路
            new_features = [
                feature for feature in line_geojson.get('features', [])
                if feature.get('properties', {}).get('line_name') != line_name
            ]
            
            # 检查是否找到并删除了线路
            if len(new_features) == original_count:
                return {"success": False, "message": f"未在GeoJSON中找到线路: {line_name}"}
            
            # 更新特征列表
            line_geojson['features'] = new_features
            
            # 保存回文件
            with open(line_geojson_path, 'w', encoding='utf-8') as f:
                json.dump(line_geojson, f, ensure_ascii=False, indent=2)
            
            return {"success": True, "message": f"已从GeoJSON中删除线路: {line_name}"}
        except Exception as e:
            print(f"从GeoJSON删除线路时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"从GeoJSON删除线路失败: {str(e)}"}
    
    def remove_line(self, line_name):
        """删除指定线路信息
        
        从时刻表和站点距离数据中删除指定线路的所有信息
        
        Args:
            line_name: 要删除的线路名称
            
        Returns:
            dict: 操作结果
        """
        try:
            # 加载站点距离数据
            stations_data = self.load_station_distance_data()
            if not stations_data:
                return {"success": False, "message": "加载站点距离数据失败"}
            
            # 加载时刻表数据
            timetable_file = Config.TIME_FILE
            try:
                with open(timetable_file, 'r', encoding='utf-8') as f:
                    timetable_data = json.load(f)
            except Exception as e:
                timetable_data = {}
            
            # 从站点距离数据中删除线路信息
            stations_to_delete = []  # 需要完全删除的站点
            stations_modified = 0    # 修改过的站点计数
            
            for station_name, station_info in list(stations_data.items()):
                if "edge" not in station_info:
                    station_info["edge"] = []
                    
                # 删除与该线路相关的边
                if "edge" in station_info:
                    original_edge_count = len(station_info["edge"])
                    
                    # 执行删除操作
                    station_info["edge"] = [
                        edge for edge in station_info["edge"] 
                        if edge.get("line") != line_name
                    ]
                    
                    if original_edge_count != len(station_info["edge"]):
                        stations_modified += 1
                
                # 从lines列表中删除该线路
                if "lines" in station_info and line_name in station_info["lines"]:
                    station_info["lines"].remove(line_name)
                    
                    # 更新line_siz
                    station_info["line_siz"] = len(station_info["lines"])
                    stations_modified += 1
                
                # 判断站点是否应该被删除
                edges = station_info.get("edge", [])
                lines = station_info.get("lines", [])
                
                # 如果没有任何边和线路时才删除站点
                if not edges and not lines:
                    stations_to_delete.append(station_name)
            
            # 删除没有边关系且没有线路信息的站点
            for station_name in stations_to_delete:
                del stations_data[station_name]
            
            # 从时刻表数据中删除线路信息
            timetable_modified = 0
            
            for station_name, station_timetable in list(timetable_data.items()):
                for line in list(station_timetable.keys()):
                    if line == line_name:
                        del station_timetable[line]
                        timetable_modified += 1
            
            # 保存更新后的数据
            self.save_station_distance_data(stations_data)
            
            # 保存更新后的时刻表数据
            with open(timetable_file, 'w', encoding='utf-8') as f:
                json.dump(timetable_data, f, ensure_ascii=False, indent=2)
            
            # 从线路地理数据中删除线路
            geojson_result = self.remove_line_from_geojson(line_name)
            
            return {
                "success": True, 
                "message": f"已删除线路 '{line_name}'",
                "details": {
                    "stations_modified": stations_modified,
                    "stations_deleted": len(stations_to_delete),
                    "timetable_entries_deleted": timetable_modified,
                    "deleted_stations": stations_to_delete,
                    "geojson_result": geojson_result["success"]
                }
            }
        except Exception as e:
            return {"success": False, "message": f"删除线路失败: {str(e)}"}

    def save_timetable(self, line_name, start_station, end_station, timetable_data):
        """保存线路时刻表数据
        
        Args:
            line_name: 线路名称
            start_station: 起始站名称
            end_station: 终点站名称
            timetable_data: 时刻表数据，包含工作日和非工作日的起始站和终点站时刻
            
        Returns:
            dict: 操作结果
        """
        try:
            # 时刻表文件路径
            timetable_file = Config.TIME_FILE
            
            # 读取现有时刻表数据
            try:
                with open(timetable_file, 'r', encoding='utf-8') as f:
                    timetable = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                # 文件不存在或内容无效时创建新的时刻表数据结构
                timetable = {}
            
            # 确保起始站和终点站在时刻表中有条目
            if start_station not in timetable:
                timetable[start_station] = {}
            if end_station not in timetable:
                timetable[end_station] = {}
                
            # 在起始站和终点站的时刻表中添加或更新当前线路的时刻表
            # 工作日起始站
            if timetable_data.get('workday_start'):
                if line_name not in timetable[start_station]:
                    timetable[start_station][line_name] = {}
                timetable[start_station][line_name]['workday'] = timetable_data['workday_start']
            
            # 工作日终点站
            if timetable_data.get('workday_end'):
                if line_name not in timetable[end_station]:
                    timetable[end_station][line_name] = {}
                timetable[end_station][line_name]['workday'] = timetable_data['workday_end']
            
            # 非工作日起始站
            if timetable_data.get('weekend_start'):
                if line_name not in timetable[start_station]:
                    timetable[start_station][line_name] = {}
                timetable[start_station][line_name]['weekend'] = timetable_data['weekend_start']
            
            # 非工作日终点站
            if timetable_data.get('weekend_end'):
                if line_name not in timetable[end_station]:
                    timetable[end_station][line_name] = {}
                timetable[end_station][line_name]['weekend'] = timetable_data['weekend_end']
                
            # 保存回文件
            with open(timetable_file, 'w', encoding='utf-8') as f:
                json.dump(timetable, f, ensure_ascii=False, indent=2)
                
            return {"success": True, "message": f"已保存线路 '{line_name}' 的时刻表数据"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"保存时刻表失败: {str(e)}"}
