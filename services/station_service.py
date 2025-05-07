import json
import os
from pathlib import Path
from typing import List

class StationService:
    """地铁站点数据服务类"""
    
    def __init__(self, data_file=None):
        """初始化站点服务
        
        Args:
            data_file: 站点数据文件路径，默认为None，将使用默认路径
        """
        if data_file is None:
            # 获取项目根目录
            root_dir = Path(__file__).parent.parent
            data_file = os.path.join(root_dir, "distance_data", "station.json")  # 从data改为distance_data
        
        self.data_file = data_file
        self.stations = self.load_stations()
        self.station_count = len(self.stations) if self.stations else 0
        print(f"已加载{self.station_count}个站点数据")
    
    def load_stations(self):
        """加载站点数据"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                station_data = json.load(f)
            return station_data
        except Exception as e:
            print(f"加载站点数据失败: {e}")
            return {}
    
    def get_station_info(self, station_name):
        """获取指定站点的信息
        
        Args:
            station_name: 站点名称
            
        Returns:
            dict: 站点信息字典，如果站点不存在则返回None
        """
        return self.stations.get(station_name, None)
    
    def get_adjacent_stations(self, station_name):
        """获取指定站点的邻接站点列表
        
        Args:
            station_name: 站点名称
            
        Returns:
            list: 邻接站点名称列表
        """
        station_info = self.get_station_info(station_name)
        if not station_info:
            return []
        
        return [edge["station"] for edge in station_info.get("edge", [])]
    
    def get_distance(self, station1, station2, line=None):
        """获取两个站点之间的距离
        
        Args:
            station1: 起始站点名称
            station2: 目标站点名称
            line: 指定线路名称，默认为None表示不指定线路
            
        Returns:
            int: 站点间距离(米)，如果站点不相邻或不存在则返回-1
        """
        station1_info = self.get_station_info(station1)
        if not station1_info:
            return -1
        
        for edge in station1_info.get("edge", []):
            if edge["station"] == station2:
                if line and edge["line"] != line:
                    continue
                return edge["distance"]
        
        return -1
    
    def get_all_lines(self, station_name):
        """获取指定站点的所有线路
        
        Args:
            station_name: 站点名称
            
        Returns:
            list: 线路名称列表
        """
        station_info = self.get_station_info(station_name)
        if not station_info:
            return []
        
        return station_info.get("lines", [])
    
    def is_transfer_station(self, station_name):
        """判断是否为换乘站
        
        Args:
            station_name: 站点名称
            
        Returns:
            bool: 是否为换乘站
        """
        station_info = self.get_station_info(station_name)
        if not station_info:
            return False
        
        return station_info.get("line_siz", 0) > 1
    
    def get_all_stations(self):
        """获取所有站点名称
        
        Returns:
            list: 站点名称列表
        """
        return list(self.stations.keys())
    
    def get_station_path(self, start_station, end_station, line):
        """获取指定线路上两站之间的路径
        
        Args:
            start_station: 起始站点名称
            end_station: 终点站点名称
            line: 线路名称
            
        Returns:
            list: 站点路径列表，如果无法找到路径则返回None
        """
        print(f"\n【调试】尝试查找路径: 从 {start_station} 到 {end_station} 沿线路 {line}")
        
        # 检查站点是否存在
        start_exists = self.get_station_info(start_station) is not None
        end_exists = self.get_station_info(end_station) is not None
        print(f"【调试】起始站点存在: {start_exists}, 终点站点存在: {end_exists}")
        
        if not start_exists or not end_exists:
            print(f"【调试】站点不存在，无法找到路径")
            return None
        
        # 检查站点是否在指定线路上
        start_lines = self.get_all_lines(start_station)
        end_lines = self.get_all_lines(end_station)
        print(f"【调试】起始站点线路: {start_lines}")
        print(f"【调试】终点站点线路: {end_lines}")
        
        if line not in start_lines or line not in end_lines:
            print(f"【调试】站点不在指定线路 {line} 上，无法找到路径")
            return None
            
        # 使用BFS寻找路径
        visited = set()
        queue = [[start_station]]
        print(f"【调试】开始BFS搜索，初始队列: {queue}")
        
        while queue:
            path = queue.pop(0)
            current = path[-1]
            
            print(f"【调试】当前处理路径: {path}, 当前站点: {current}")
            
            if current == end_station:
                print(f"【调试】找到路径: {path}")
                return path
                
            if current in visited:
                print(f"【调试】站点 {current} 已访问过，跳过")
                continue
                
            visited.add(current)
            
            # 检查从当前站点出发的所有边
            station_info = self.get_station_info(current)
            if station_info:
                print(f"【调试】检查站点 {current} 的相邻站点:")
                for edge in station_info.get("edge", []):
                    next_station = edge["station"]
                    edge_line = edge["line"]
                    print(f"【调试】  相邻站点: {next_station}, 线路: {edge_line}")
                    
                    if edge["line"] == line and next_station not in visited:
                        new_path = list(path)
                        new_path.append(next_station)
                        queue.append(new_path)
                        print(f"【调试】  添加新路径: {new_path}")
                    else:
                        if edge["line"] != line:
                            print(f"【调试】  线路不匹配: {edge_line} != {line}")
                        if next_station in visited:
                            print(f"【调试】  站点 {next_station} 已访问过")
    
        print(f"【调试】BFS搜索完成，未找到从 {start_station} 到 {end_station} 的路径")
        return None

    def is_station_on_line(self, station_name, line_name):
        """Check if a station is on a specific line"""
        if station_name not in self.stations:
            return False
        
        # 检查完整线路名或部分线路名匹配
        for station_line in self.stations[station_name].get("lines", []):
            if line_name == station_line or line_name in station_line:
                return True
        return False

    def get_stations_on_line(self, line_name: str) -> List[str]:
        """获取指定线路上的所有站点列表
        
        Args:
            line_name: 线路名称
            
        Returns:
            List[str]: 线路上的站点列表，按顺序排列
        """
        try:
            # 遍历所有站点数据，查找属于指定线路的站点
            stations_on_line = []
            station_positions = {}  # 用于存储站点在线路上的位置
            
            for station_name, station_data in self.stations.items():
                for line_info in station_data.get("lines", []):
                    line_info_name = line_info.get("name", "")
                    # 精确匹配或子串匹配
                    if line_info_name == line_name or self._is_matching_line(line_name, line_info_name):
                        position = line_info.get("position", -1)
                        if position >= 0:
                            station_positions[station_name] = position
                            
            # 根据位置排序站点
            sorted_stations = sorted(station_positions.items(), key=lambda x: x[1])
            stations_on_line = [station for station, _ in sorted_stations]
            
            return stations_on_line
        except Exception as e:
            print(f"获取线路 {line_name} 站点列表时出错: {str(e)}")
            return []
            
    def _is_matching_line(self, line1: str, line2: str) -> bool:
        """判断两个线路名称是否匹配
        
        匹配规则:
        1. 去除括号内容后完全相同
        2. 主干名称相同（如"地铁1号线"）
        
        Args:
            line1: 第一个线路名称
            line2: 第二个线路名称
            
        Returns:
            bool: 是否匹配
        """
        # 移除括号内容
        import re
        line1_core = re.sub(r'\([^)]*\)', '', line1).strip()
        line2_core = re.sub(r'\([^)]*\)', '', line2).strip()
        
        # 完全匹配
        if line1_core == line2_core:
            return True
            
        # 提取主干名称（如"地铁1号线"）
        line1_main = re.match(r'(地铁\d+号线|[a-zA-Z0-9]+线)', line1)
        line2_main = re.match(r'(地铁\d+号线|[a-zA-Z0-9]+线)', line2)
        
        if line1_main and line2_main and line1_main.group(1) == line2_main.group(1):
            return True
            
        # 特殊情况：八通线和地铁1号线八通线
        if ("八通线" in line1 and "地铁1号线" in line2) or ("八通线" in line2 and "地铁1号线" in line1):
            return True
            
        return False

    def get_path_between_stations(self, start_station, end_station, line_name):
        """获取两个站点之间在同一条线路上的路径"""
        # 使用BFS查找路径
        if start_station not in self.stations or end_station not in self.stations:
            return None
            
        visited = set()
        queue = [[start_station]]
        
        while queue:
            path = queue.pop(0)
            current = path[-1]
            
            if current == end_station:
                return path
                
            if current in visited:
                continue
                
            visited.add(current)
            
            # 获取当前站点的所有邻接站点（同一线路上的）
            neighbors = []
            for edge in self.stations[current].get("edge", []):
                if edge["line"] == line_name or line_name in edge["line"]:
                    neighbors.append(edge["station"])
                    
            for neighbor in neighbors:
                if neighbor not in visited:
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append(new_path)
                    
        return None  # 没有找到路径

    def get_distance_between_stations(self, station1, station2, line_name):
        """获取两个相邻站点之间的距离（米）"""
        if station1 not in self.stations or station2 not in self.stations:
            return None
            
        # 查找直接连接
        for edge in self.stations[station1].get("edge", []):
            if edge["station"] == station2 and (edge["line"] == line_name or line_name in edge["line"]):
                return edge["distance"]
                
        # 查找反向连接
        for edge in self.stations[station2].get("edge", []):
            if edge["station"] == station1 and (edge["line"] == line_name or line_name in edge["line"]):
                return edge["distance"]
                
        return None

    def is_connected_by_line(self, station1, station2, line_name):
        """检查两个站点是否通过指定线路直接连接
        
        Args:
            station1: 起始站点名称
            station2: 目标站点名称
            line_name: 线路名称
            
        Returns:
            bool: 是否直接连接
        """
        # 首先检查两个站点是否都在指定线路上
        if not self.is_station_on_line(station1, line_name) or not self.is_station_on_line(station2, line_name):
            return False
        
        # 检查是否直接相邻
        station1_info = self.get_station_info(station1)
        if not station1_info:
            return False
        
        for edge in station1_info.get("edge", []):
            if edge["station"] == station2:
                if isinstance(edge["line"], str):
                    if edge["line"] == line_name or line_name in edge["line"]:
                        return True
                elif isinstance(edge["line"], list):
                    if line_name in edge["line"]:
                        return True
        
        return False

if __name__ == "__main__":
    # 简单测试
    service = StationService()
    print(f"站点总数: {service.station_count}")
    
    # 测试获取距离
    test_stations = ["西直门", "大钟寺"]
    distance = service.get_distance(test_stations[0], test_stations[1])
    print(f"{test_stations[0]}到{test_stations[1]}的距离: {distance}米")
