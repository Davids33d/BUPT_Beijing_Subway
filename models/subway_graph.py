import networkx as nx
import json
from config import Config

class SubwayGraph:
    def __init__(self, stations=None, lines=None, edges=None):
        self.graph = nx.Graph()
        
        # 初始化数据结构
        self.stations = stations if stations is not None else {}
        self.lines = lines if lines is not None else {}
        self.edges = edges if edges is not None else []
        
        # 如果没有提供数据，则从文件加载
        if stations is None and lines is None and edges is None:
            self.load_data()
        # 否则，根据提供的数据构建图
        else:
            self.build_graph_from_data()
    
    def load_data(self):
        """从文件加载地铁数据，包括站点、线路和连接关系"""
        edges_file = f"{Config.DATA_DIR}/edges.json"
        with open(edges_file, 'r', encoding='utf-8') as f:
            edges = json.load(f)

        for edge in edges:
            from_station = edge['from']
            to_station = edge['to']
            line = edge['line']
            distance = edge['distance']
            time = edge['time']

            # 添加站点（如果不存在）
            if from_station not in self.stations:
                self.stations[from_station] = {'name': from_station, 'lines': [line]}
            else:
                if line not in self.stations[from_station]['lines']:
                    self.stations[from_station]['lines'].append(line)

            if to_station not in self.stations:
                self.stations[to_station] = {'name': to_station, 'lines': [line]}
            else:
                if line not in self.stations[to_station]['lines']:
                    self.stations[to_station]['lines'].append(line)

            # 添加线路（如果不存在）
            if line not in self.lines:
                self.lines[line] = {'name': line, 'stations': [from_station, to_station]}
            else:
                if to_station not in self.lines[line]['stations']:
                    self.lines[line]['stations'].append(to_station)
                if from_station not in self.lines[line]['stations']:
                    self.lines[line]['stations'].append(from_station)

            # 添加边
            self.graph.add_edge(from_station, to_station, line=line, distance=distance, time=time)

    def build_graph_from_data(self):
        """根据提供的站点、线路和边数据构建图"""
        # 根据self.edges构建图
        for edge in self.edges:
            from_station = edge['from']
            to_station = edge['to']
            line = edge['line']
            distance = edge.get('distance', 0)
            time = edge.get('time', 0)
            
            # 添加边
            self.graph.add_edge(from_station, to_station, line=line, distance=distance, time=time)

    def get_shortest_path(self, start_station, end_station, weight='time'):
        """使用Dijkstra算法计算最短路径"""
        try:
            path = nx.shortest_path(self.graph, source=start_station, target=end_station, weight=weight)
            return path
        except nx.NetworkXNoPath:
            return None

    def get_least_transfers_path(self, start_station, end_station):
        """
        使用自定义权重查找最少换乘路径
        为图中的边分配权重，使得换乘边的权重远大于非换乘边
        """
        # 创建临时图以分配自定义权重
        temp_graph = nx.Graph()
        
        # 复制原图的节点和边
        for edge in self.graph.edges(data=True):
            from_station, to_station, attr = edge
            line = attr['line']
            
            # 确定起点站和终点站的线路集合
            from_lines = set(self.stations[from_station]['lines'])
            to_lines = set(self.stations[to_station]['lines'])
            
            # 计算权重：如果两站点共享线路则权重为1，否则为100（表示换乘）
            weight = 1 if line in from_lines and line in to_lines else 100
            
            # 添加边到临时图
            temp_graph.add_edge(from_station, to_station, weight=weight, line=line)
        
        # 使用Dijkstra算法找最少换乘路径
        try:
            path = nx.shortest_path(temp_graph, source=start_station, target=end_station, weight='weight')
            return path
        except nx.NetworkXNoPath:
            return None

    def get_multiple_paths(self, start_station, end_station, max_paths=3):
        """
        查找多条可能的路径
        返回最多max_paths条不同的路径，按总时间排序
        """
        paths = []
        
        # 首先获取最短时间路径
        time_path = self.get_shortest_path(start_station, end_station)
        if time_path:
            time_details = self.get_path_details(time_path)
            paths.append({
                "type": "shortest_time",
                "path": time_path,
                "details": time_details
            })
        
        # 获取最少换乘路径
        transfers_path = self.get_least_transfers_path(start_station, end_station)
        # 检查是否与最短时间路径相同
        if transfers_path and transfers_path != time_path:
            transfers_details = self.get_path_details(transfers_path)
            paths.append({
                "type": "least_transfers",
                "path": transfers_path,
                "details": transfers_details
            })
        
        # 尝试找到更多可能的路径（使用k-最短路径算法）
        try:
            import itertools
            # 限制寻找的额外路径数量
            k_paths = list(itertools.islice(
                nx.shortest_simple_paths(self.graph, start_station, end_station, weight='time'), 
                max_paths + 1  # +1是为了排除已经找到的最短路径
            ))
            
            # 过滤掉已经包含的路径
            for i, path in enumerate(k_paths):
                if i == 0 or path == time_path or path == transfers_path:
                    continue  # 跳过已包含的路径
                
                path_details = self.get_path_details(path)
                paths.append({
                    "type": f"alternative_{i}",
                    "path": path,
                    "details": path_details
                })
                
                if len(paths) >= max_paths:
                    break
        except:
            # 如果k最短路径算法失败，忽略额外路径
            pass
        
        return paths

    def sort_paths(self, paths, sort_by='time'):
        """
        对多条路径进行排序
        sort_by: 'time'(按时间排序), 'transfers'(按换乘次数排序), 'distance'(按距离排序)
        """
        if sort_by == 'time':
            return sorted(paths, key=lambda x: x['details']['time'])
        elif sort_by == 'transfers':
            return sorted(paths, key=lambda x: x['details']['transfers'])
        elif sort_by == 'distance':
            return sorted(paths, key=lambda x: x['details']['distance'])
        else:
            return paths  # 默认不排序

    def get_station_info(self, station_id):
        """获取站点信息"""
        return self.stations.get(station_id)

    def get_line_info(self, line_id):
        """获取线路信息"""
        return self.lines.get(line_id)

    def get_path_details(self, path):
        """
        计算路径详情，包括总距离、总时间、换乘次数和分段信息
        添加换乘时间(Config.TRANSFER_TIME)和停站时间(Config.STOP_TIME)
        """
        from config import Config
        total_distance = 0
        total_time = 0
        transfers = 0
        segments = []
        previous_line = None
        for i in range(len(path) - 1):
            edge_data = self.graph.get_edge_data(path[i], path[i+1])
            # 假设返回单个边数据
            line_used = edge_data['line']
            distance = edge_data.get('distance', 0)
            segment_time = edge_data.get('time', 0)
            # 如果当前边与前一边线路不同，则计为换乘并增加换乘时间
            if previous_line is not None and line_used != previous_line:
                transfers += 1
                segment_time += Config.TRANSFER_TIME
            segments.append({
                "from": path[i],
                "to": path[i+1],
                "line": line_used,
                "distance": distance,
                "time": segment_time
            })
            total_distance += distance
            total_time += segment_time
            previous_line = line_used
        # 对每个中间站点添加停站时间
        stops = len(path) - 1
        total_time += stops * Config.STOP_TIME
        return {
            "stations": path,
            "distance": total_distance,
            "time": total_time,
            "transfers": transfers,
            "segments": segments
        }

    def add_line(self, line_name, color=None, start_station=None, end_station=None):
        """添加新线路
        
        Args:
            line_name: 线路名称
            color: 线路颜色，默认为None
            start_station: 起始站点，默认为None
            end_station: 终点站，默认为None
        """
        try:
            # 检查线路名称是否为空
            if not line_name:
                raise ValueError("线路名称不能为空")
                
            # 根据self.lines的类型选择不同的处理方式
            if isinstance(self.lines, dict):
                # 如果是字典，检查线路是否已存在
                if line_name in self.lines:
                    # 更新现有线路信息
                    if color:
                        self.lines[line_name]['color'] = color
                    if start_station:
                        self.lines[line_name]['start_station'] = start_station
                    if end_station:
                        self.lines[line_name]['end_station'] = end_station
                else:
                    # 创建新线路
                    self.lines[line_name] = {
                        'name': line_name,
                        'stations': [],
                        'color': color or '#FF0000'  # 默认红色
                    }
                    
                    # 添加起始站和终点站信息（如果提供）
                    if start_station:
                        self.lines[line_name]['start_station'] = start_station
                    if end_station:
                        self.lines[line_name]['end_station'] = end_station
                        
            elif isinstance(self.lines, list):
                # 如果是列表，查找是否已存在该线路
                line_found = False
                for line in self.lines:
                    if line.get('name') == line_name:
                        # 更新现有线路信息
                        if color:
                            line['color'] = color
                        if start_station:
                            line['start_station'] = start_station
                        if end_station:
                            line['end_station'] = end_station
                        line_found = True
                        break
                        
                if not line_found:
                    # 创建新线路并添加到列表
                    new_line = {
                        'name': line_name,
                        'stations': [],
                        'color': color or '#FF0000'  # 默认红色
                    }
                    
                    # 添加起始站和终点站信息（如果提供）
                    if start_station:
                        new_line['start_station'] = start_station
                    if end_station:
                        new_line['end_station'] = end_station
                        
                    self.lines.append(new_line)
                    
            return True
        except Exception as e:
            print(f"添加线路失败: {str(e)}")
            raise e

    def add_connection(self, station1, station2, line_name, distance=None, time=None):
        """添加站点间连接
        
        Args:
            station1: 起始站点名称
            station2: 终点站点名称
            line_name: 线路名称
            distance: 距离（米）
            time: 运行时间（秒）
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 获取站点ID
            station1_id = None
            station2_id = None
            
            # 处理列表格式的站点数据
            if isinstance(self.stations, list):
                for station in self.stations:
                    if station.get('name') == station1 or station.get('station_name') == station1:
                        station1_id = station.get('id')
                    if station.get('name') == station2 or station.get('station_name') == station2:
                        station2_id = station.get('id')
            # 处理字典格式的站点数据
            elif isinstance(self.stations, dict):
                for sid, station in self.stations.items():
                    if station.get('name') == station1 or station.get('station_name') == station1:
                        station1_id = sid
                    if station.get('name') == station2 or station.get('station_name') == station2:
                        station2_id = sid
            
            if not station1_id or not station2_id:
                return False
            
            # 创建连接
            edge_id = f"{station1_id}_{station2_id}"
            edge_data = {
                'source': station1_id,
                'target': station2_id,
                'line': line_name
            }
            
            if distance is not None:
                edge_data['distance'] = distance
            
            if time is not None:
                edge_data['time'] = time
            
            # 添加边信息
            if isinstance(self.edges, dict):
                self.edges[edge_id] = edge_data
            elif isinstance(self.edges, list):
                self.edges.append(edge_data)
            
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    subway_graph = SubwayGraph()

    # 示例用法：获取最短路径并打印路径详情
    shortest_path = subway_graph.get_shortest_path('s001', 's004')
    print(f"最短时间路径: {shortest_path}")

    if shortest_path:
        details = subway_graph.get_path_details(shortest_path)
        print("路径详情:")
        print(f"  总时间: {details['time']}分钟")
        print(f"  总距离: {details['distance']}公里")
        print(f"  换乘次数: {details['transfers']}次")
    
    # 测试最少换乘路径
    least_transfers = subway_graph.get_least_transfers_path('s001', 's004')
    print(f"\n最少换乘路径: {least_transfers}")
    
    if least_transfers:
        details = subway_graph.get_path_details(least_transfers)
        print("路径详情:")
        print(f"  总时间: {details['time']}分钟")
        print(f"  总距离: {details['distance']}公里")
        print(f"  换乘次数: {details['transfers']}次")
    
    # 测试多条路径查询和排序
    print("\n多条路径查询结果:")
    multiple_paths = subway_graph.get_multiple_paths('s001', 's004')
    
    for i, path_info in enumerate(multiple_paths):
        print(f"\n路径 {i+1} ({path_info['type']}):")
        path_details = path_info['details']
        print(f"  站点序列: {path_details['stations']}")
        print(f"  总时间: {path_details['time']}分钟")
        print(f"  换乘次数: {path_details['transfers']}次")
        print(f"  总距离: {path_details['distance']}公里")
