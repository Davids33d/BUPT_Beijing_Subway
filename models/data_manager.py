import json
import os
import logging
from typing import Dict, List, Optional
from pathlib import Path

class DataManager:
    """数据管理类，负责读写站点、线路、连接和时刻表数据"""
    
    def __init__(self, stations_file, lines_file=None, edges_file=None, schedules_file=None):
        """初始化数据管理器"""
        self.stations_file = stations_file
        self.lines_file = lines_file
        self.edges_file = edges_file
        self.schedules_file = schedules_file
        
        # 设置时刻表文件路径
        root_dir = Path(__file__).parent.parent
        self.time_data_file = os.path.join(root_dir, "time_data", "time.json")
        
        # 创建文件如果它们不存在
        self._ensure_files_exist()
        
        # 加载时刻表数据
        self.time_data = self._load_time_data()
    
    def _ensure_files_exist(self):
        """确保所有数据文件存在，如果不存在则创建空文件"""
        files = [self.stations_file]
        
        # 只处理非None的文件路径
        if self.lines_file:
            files.append(self.lines_file)
        if self.edges_file:
            files.append(self.edges_file)
        if self.schedules_file:
            files.append(self.schedules_file)
            
        for file in files:
            if file:  # 确保文件路径不是None
                directory = os.path.dirname(file)
                if not os.path.exists(directory):
                    os.makedirs(directory)
                if not os.path.exists(file):
                    with open(file, 'w', encoding='utf-8') as f:
                        json.dump([], f, ensure_ascii=False)
    
    def _load_time_data(self) -> Dict:
        """加载时刻表数据
        
        Returns:
            Dict: 时刻表数据字典
        """
        try:
            if os.path.exists(self.time_data_file):
                with open(self.time_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"加载时刻表数据出错: {str(e)}")
            return {}
    
    def load_stations(self):
        """加载站点数据"""
        try:
            with open(self.stations_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def load_lines(self):
        """加载线路数据"""
        if not self.lines_file:  # 如果文件路径为None，返回空列表
            return []
        try:
            with open(self.lines_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def load_edges(self):
        """加载边连接数据"""
        if not self.edges_file:  # 如果文件路径为None，返回空列表
            return []
        try:
            with open(self.edges_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def load_schedules(self):
        """加载时刻表数据"""
        if not self.schedules_file:  # 如果文件路径为None，返回空列表
            return []
        try:
            with open(self.schedules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def save_stations(self, stations):
        """保存站点数据到文件"""
        try:
            with open(self.stations_file, 'w', encoding='utf-8') as f:
                json.dump(stations, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存站点数据失败: {str(e)}")
            return False
    
    def save_lines(self, lines):
        """保存线路数据"""
        if not self.lines_file:  # 如果文件路径为None，直接返回False
            return False
        with open(self.lines_file, 'w', encoding='utf-8') as f:
            json.dump(lines, f, ensure_ascii=False, indent=2)
        return True
    
    def save_edges(self, edges):
        """保存边数据到文件"""
        if not self.edges_file:  # 如果文件路径为None，直接返回False
            return False
        try:
            with open(self.edges_file, 'w', encoding='utf-8') as f:
                json.dump(edges, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存边数据失败: {str(e)}")
            return False
    
    def save_schedules(self, schedules):
        """保存时刻表数据"""
        if not self.schedules_file:  # 如果文件路径为None，直接返回False
            return False
        with open(self.schedules_file, 'w', encoding='utf-8') as f:
            json.dump(schedules, f, ensure_ascii=False, indent=2)
        return True
    
    def save_time_data(self, data: Dict) -> bool:
        """保存时刻表数据
        
        Args:
            data: 要保存的时刻表数据
            
        Returns:
            bool: 保存是否成功
        """
        try:
            directory = os.path.dirname(self.time_data_file)
            if not os.path.exists(directory):
                os.makedirs(directory)
                
            with open(self.time_data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"保存时刻表数据出错: {str(e)}")
            return False
    
    def save_station(self, station):
        """保存单个站点信息"""
        stations = self.load_stations()
        
        # 检查是否已存在该站点，如果存在则更新
        found = False
        for i, s in enumerate(stations):
            if s['id'] == station['id']:
                stations[i] = station
                found = True
                break
        
        if not found:
            stations.append(station)
        
        return self.save_stations(stations)
    
    def save_line(self, line):
        """保存单个线路信息"""
        lines = self.load_lines()
        
        # 检查是否已存在该线路，如果存在则更新
        found = False
        for i, l in enumerate(lines):
            if l['id'] == line['id']:
                lines[i] = line
                found = True
                break
        
        if not found:
            lines.append(line)
        
        return self.save_lines(lines)
    
    def delete_line(self, line_id):
        """删除线路"""
        lines = self.load_lines()
        lines = [line for line in lines if line['id'] != line_id]
        return self.save_lines(lines)
    
    def delete_station(self, station_id):
        """删除站点"""
        stations = self.load_stations()
        stations = [station for station in stations if station['id'] != station_id]
        return self.save_stations(stations)
    
    def get_schedule(self, station_name: str) -> Optional[Dict]:
        """获取指定站点的时刻表
        
        Args:
            station_name: 站点名称
            
        Returns:
            Dict: 站点的时刻表数据，如果不存在则返回None
        """
        if not self.time_data:
            return None
            
        return {station_name: self.time_data.get(station_name, {})} if station_name in self.time_data else None
    
    def update_schedule(self, station_name: str, line_name: str, direction: str, 
                       date_type: str, timetable: Dict[str, List[int]]) -> bool:
        """更新站点时刻表
        
        Args:
            station_name: 站点名称
            line_name: 线路名称
            direction: 方向（"1"表示上行，"2"表示下行）
            date_type: 日期类型（"工作日"或"双休日"）
            timetable: 时刻表数据，格式为 {"小时": [分钟列表]}
            
        Returns:
            bool: 更新是否成功
        """
        try:
            if station_name not in self.time_data:
                self.time_data[station_name] = {}
                
            if line_name not in self.time_data[station_name]:
                self.time_data[station_name][line_name] = {}
                
            if direction not in self.time_data[station_name][line_name]:
                self.time_data[station_name][line_name][direction] = {}
                
            self.time_data[station_name][line_name][direction][date_type] = timetable
            
            # 保存到文件
            return self.save_time_data(self.time_data)
        except Exception as e:
            logging.error(f"更新时刻表出错: {str(e)}")
            return False
