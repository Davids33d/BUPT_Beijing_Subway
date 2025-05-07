import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import time
import re

# 修复相对导入问题
try:
    from .station_service import StationService  # 当作为包的一部分导入时
except ImportError:
    # 当直接运行文件时
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from services.station_service import StationService

# 将日志级别设置为WARNING，减少INFO日志输出
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TimeTableService:
    """时刻表服务类，提供获取站点时刻表的功能"""
    
    def __init__(self, time_data_file=None):
        """
        初始化时刻表服务
        
        Args:
            time_data_file: 时刻表数据文件路径
        """
        if time_data_file is None:
            # 默认时刻表数据文件路径
            self.time_data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'time_data', 'time.json')
        else:
            self.time_data_file = time_data_file
        
        self.time_data = self._load_time_data()
    
    def _load_time_data(self):
        """加载时刻表数据"""
        try:
            if os.path.exists(self.time_data_file):
                with open(self.time_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"加载时刻表数据出错: {str(e)}")
            return {}
    
    def get_schedule(self, station_name):
        """
        获取站点的时刻表
        
        Args:
            station_name: 站点名称
            
        Returns:
            dict: 站点时刻表数据
        """
        if not self.time_data:
            return None
        
        return {station_name: self.time_data.get(station_name, {})} if station_name in self.time_data else None

class TimeService:
    """地铁时刻表服务类"""
    
    def __init__(self, timetable_file=None, station_service=None):
        """初始化时刻表服务
        
        Args:
            timetable_file: 时刻表数据文件路径
            station_service: 站点服务
        """
        self.station_service = station_service
        
        # 设置默认时刻表文件路径
        if timetable_file is None:
            self.timetable_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'time_data', 'time.json')
        else:
            self.timetable_file = timetable_file
            
        # 用于存储线路首发站点的映射
        self.line_terminal_stations = {}
        # 用于存储每条线路上站点的顺序
        self.line_stations_order = {}
        # 用于存储每个站点相对于首发站的时间偏移（分钟）
        self.line_station_offsets = {}
        # 用于存储所有线路信息
        self.all_lines = set()
        # 用于存储线路名称映射（短名称->完整名称）
        self.line_name_mapping = {}
        # 存储规范化后的线路名称映射
        self.normalized_line_cache = {}
        
        # 加载时刻表数据
        self._load_timetable_data()
        
        # 预计算线路信息和站点偏移
        self._precompute_line_station_data()
        
        logger.warning(f"TimeService初始化完成，预计算了{len(self.line_station_offsets)}条线路的站点时间偏移")
    
    def _load_timetable_data(self):
        """加载时刻表数据"""
        start_time = time.time()
        try:
            with open(self.timetable_file, 'r', encoding='utf-8') as f:
                self.timetable_data = json.load(f)
        except Exception as e:
            logger.error(f"加载时刻表数据失败: {e}")
            self.timetable_data = {}
    
    def _precompute_line_station_data(self):
        """预计算线路站点数据和时间偏移"""
        if not self.timetable_data or not self.station_service:
            return
            
        start_time = time.time()
        
        # 第一步：收集所有线路信息并提取首发站
        self._extract_line_info()
        
        # 创建线路名称映射
        self._create_line_name_mapping()
        
        # 第二步：为每条线路构建站点顺序
        self._build_line_station_order()
        
        # 第三步：计算每个站点相对于首发站的时间偏移
        self._calculate_station_time_offsets()
        
        # 第四步：确保所有线路的双向数据都已计算
        self._ensure_bidirectional_offsets()
        
        logger.warning(f"预计算完成，共处理{len(self.line_terminal_stations)}条线路")
        
        # 输出预计算结果摘要
        self._log_precompute_summary()

    def _ensure_bidirectional_offsets(self):
        """确保所有线路都有双向的偏移数据"""
        for line_name, directions in list(self.line_station_offsets.items()):
            # 检查是否只有一个方向有数据
            if "1" in directions and "2" not in directions:
                self._create_reverse_direction_offsets(line_name, "1", "2")
            elif "2" in directions and "1" not in directions:
                self._create_reverse_direction_offsets(line_name, "2", "1")
        
        # 特别为1号线系列处理
        self._ensure_line_one_bidirectional()

    def _create_reverse_direction_offsets(self, line_name, src_dir, target_dir):
        """从一个方向创建反向的偏移数据
        
        Args:
            line_name: 线路名称
            src_dir: 源方向
            target_dir: 目标方向
        """
        if line_name not in self.line_station_offsets or src_dir not in self.line_station_offsets[line_name]:
            return
            
        if line_name not in self.line_stations_order or src_dir not in self.line_stations_order[line_name]:
            return
            
        # 获取正向站点列表并反转
        stations = self.line_stations_order[line_name][src_dir]
        if not stations:
            return
            
        reversed_stations = list(reversed(stations))
        
        # 确保目标方向数据结构存在
        if target_dir not in self.line_station_offsets[line_name]:
            self.line_station_offsets[line_name][target_dir] = {}
            
        # 为目标方向创建站点顺序
        if target_dir not in self.line_stations_order[line_name]:
            self.line_stations_order[line_name][target_dir] = reversed_stations
        
        # 第一个站点偏移为0
        first_station = reversed_stations[0]
        self.line_station_offsets[line_name][target_dir][first_station] = 0
        
        # 计算每个站点的偏移
        cumulative_offset = 0
        for i in range(1, len(reversed_stations)):
            prev_station = reversed_stations[i-1]
            curr_station = reversed_stations[i]
            travel_time = self._calculate_travel_time(prev_station, curr_station, line_name)
            stop_time = 0.5 if i > 1 else 0
            cumulative_offset += travel_time + stop_time
            self.line_station_offsets[line_name][target_dir][curr_station] = cumulative_offset
            
        logger.info(f"为线路 {line_name} 方向 {target_dir} 创建了反向偏移数据，共 {len(reversed_stations)} 个站点")

    def _ensure_line_one_bidirectional(self):
        """特别确保1号线相关线路都有双向数据"""
        one_line_variants = [line for line in self.all_lines if "1号线" in line or "一号线" in line]
        
        # 先找到数据最完整的1号线变体
        best_variant = None
        max_stations_count = 0
        
        for variant in one_line_variants:
            if variant in self.line_station_offsets:
                for direction, stations in self.line_station_offsets[variant].items():
                    if len(stations) > max_stations_count:
                        max_stations_count = len(stations)
                        best_variant = variant
        
        if best_variant:
            # 确保这个变体有双向数据
            if "1" in self.line_station_offsets[best_variant] and "2" not in self.line_station_offsets[best_variant]:
                self._create_reverse_direction_offsets(best_variant, "1", "2")
            elif "2" in self.line_station_offsets[best_variant] and "1" not in self.line_station_offsets[best_variant]:
                self._create_reverse_direction_offsets(best_variant, "2", "1")
            
            # 将完整的双向数据复制到所有1号线变体
            if "1" in self.line_station_offsets[best_variant] and "2" in self.line_station_offsets[best_variant]:
                for variant in one_line_variants:
                    if variant != best_variant:
                        self.line_station_offsets[variant] = {}
                        self.line_station_offsets[variant]["1"] = self.line_station_offsets[best_variant]["1"]
                        self.line_station_offsets[variant]["2"] = self.line_station_offsets[best_variant]["2"]
                        
                        if variant not in self.line_stations_order:
                            self.line_stations_order[variant] = {}
                        
                        self.line_stations_order[variant]["1"] = self.line_stations_order[best_variant]["1"]
                        self.line_stations_order[variant]["2"] = self.line_stations_order[best_variant]["2"]
                
                # 确保简化名称也有同样的数据
                for simple_name in ["1号线", "地铁1号线", "一号线", "地铁一号线"]:
                    if simple_name not in self.line_station_offsets:
                        self.line_station_offsets[simple_name] = {}
                        self.line_station_offsets[simple_name]["1"] = self.line_station_offsets[best_variant]["1"]
                        self.line_station_offsets[simple_name]["2"] = self.line_station_offsets[best_variant]["2"]
                        
                        if simple_name not in self.line_stations_order:
                            self.line_stations_order[simple_name] = {}
                        
                        self.line_stations_order[simple_name]["1"] = self.line_stations_order[best_variant]["1"]
                        self.line_stations_order[simple_name]["2"] = self.line_stations_order[best_variant]["2"]
            
            logger.info(f"已为所有1号线变体创建双向偏移数据，基于 {best_variant}")

    def _log_precompute_summary(self):
        """输出预计算结果摘要日志"""
        try:
            lines_with_offsets = 0
            total_directions = 0
            total_stations = 0
            
            for line_name, directions in self.line_station_offsets.items():
                lines_with_offsets += 1
                for direction, stations in directions.items():
                    total_directions += 1
                    total_stations += len(stations)
                    
            logger.warning(f"预计算完成: {lines_with_offsets}条线路, {total_directions}个方向, {total_stations}个站点偏移")
                
        except Exception as e:
            logger.error(f"生成预计算摘要时出错: {e}")

    def _create_line_name_mapping(self):
        """创建线路名称映射，用于匹配简称和全称"""
        self.line_name_mapping = {}
        
        # 特殊处理1号线的各种名称变体
        one_line_variants = []
        
        for full_name in self.all_lines:
            short_name = None
            
            # 专门处理1号线及其变体
            if "1号线" in full_name or "一号线" in full_name:
                if "1号线" not in self.line_name_mapping:
                    self.line_name_mapping["1号线"] = []
                self.line_name_mapping["1号线"].append(full_name)
                
                if "地铁1号线" not in self.line_name_mapping:
                    self.line_name_mapping["地铁1号线"] = []
                self.line_name_mapping["地铁1号线"].append(full_name)
                
                one_line_variants.append(full_name)
                continue
                
            if "号线" in full_name:
                match = re.search(r'(\d+)号线', full_name)
                if match:
                    short_name = match.group(1) + "号线"
                    alt_short_name = "地铁" + short_name
                    
                    if short_name not in self.line_name_mapping:
                        self.line_name_mapping[short_name] = []
                    self.line_name_mapping[short_name].append(full_name)
                    
                    if alt_short_name not in self.line_name_mapping:
                        self.line_name_mapping[alt_short_name] = []
                    self.line_name_mapping[alt_short_name].append(full_name)
            
            elif "昌平线" in full_name:
                short_name = "昌平线"
            elif "房山线" in full_name:
                short_name = "房山线"
            elif "亦庄线" in full_name:
                short_name = "亦庄线"
            elif "燕房线" in full_name:
                short_name = "燕房线"
            elif "首都机场线" in full_name or ("机场线" in full_name and "首都" in full_name):
                short_name = "首都机场线"
            elif "大兴机场线" in full_name or ("机场线" in full_name and "大兴" in full_name):
                short_name = "大兴机场线"
            elif "S1" in full_name:
                short_name = "S1线"
            elif "西郊线" in full_name:
                short_name = "西郊线"
            
            if short_name:
                if short_name not in self.line_name_mapping:
                    self.line_name_mapping[short_name] = []
                self.line_name_mapping[short_name].append(full_name)
        
        # 确保所有线路至少映射到自己
        for full_name in self.all_lines:
            if full_name not in self.line_name_mapping:
                self.line_name_mapping[full_name] = [full_name]
                
        # 将所有特殊处理的1号线变体存入line_name_mapping
        for variant in ["1号线", "地铁1号线", "一号线", "地铁一号线"]:
            if variant in self.line_name_mapping:
                self.line_name_mapping[variant].extend(one_line_variants)
            else:
                self.line_name_mapping[variant] = one_line_variants

    def _extract_line_info(self):
        """从时刻表数据中提取所有线路信息和首发站"""
        for station_name, station_data in self.timetable_data.items():
            for line_name, line_data in station_data.items():
                self.all_lines.add(line_name)
                
                terminal_stations = self._extract_terminal_stations(line_name)
                if terminal_stations:
                    self.line_terminal_stations[line_name] = terminal_stations
                    start_station, end_station = terminal_stations
                    
                    if "1" in line_data and "2" in line_data:
                        if line_name not in self.line_terminal_stations:
                            self.line_terminal_stations[line_name] = {}
                        if isinstance(self.line_terminal_stations[line_name], tuple):
                            self.line_terminal_stations[line_name] = {
                                "1": start_station,
                                "2": end_station
                            }
                        else:
                            self.line_terminal_stations[line_name]["1"] = start_station
                            self.line_terminal_stations[line_name]["2"] = end_station

    def _extract_terminal_stations(self, line_name: str) -> Tuple[Optional[str], Optional[str]]:
        """从线路名中提取始发站和终点站
        
        Args:
            line_name: 完整线路名称，如 "地铁15号线(俸伯--清华东路西口)"
            
        Returns:
            tuple: (始发站，终点站)，如果提取失败则返回(None, None)
        """
        try:
            stations_part = line_name.split('(')[1].split(')')[0]
            start_station, end_station = stations_part.split('--')
            return start_station, end_station
        except Exception:
            return None, None

    def _build_line_station_order(self):
        """为每条线路构建站点顺序"""
        for line_name in self.all_lines:
            if line_name not in self.line_terminal_stations:
                continue
                
            terminal_info = self.line_terminal_stations[line_name]
            if isinstance(terminal_info, tuple):
                start_station, end_station = terminal_info
                terminals = {
                    "1": start_station,
                    "2": end_station
                }
            else:
                terminals = terminal_info
            
            self.line_stations_order[line_name] = {}
            
            for direction, start_terminal in terminals.items():
                other_direction = "2" if direction == "1" else "1"
                end_terminal = terminals.get(other_direction)
                if not end_terminal:
                    continue
                
                path = self._get_line_path(start_terminal, end_terminal, line_name)
                
                if path:
                    self.line_stations_order[line_name][direction] = path
                    logger.info(f"成功为线路 {line_name} 方向 {direction} 构建站点顺序，共 {len(path)} 个站点")
                else:
                    if hasattr(self.station_service, 'get_line_stations'):
                        stations = self.station_service.get_line_stations(line_name)
                        if stations:
                            if direction == "2":
                                stations = list(reversed(stations))
                            self.line_stations_order[line_name][direction] = stations
                            logger.info(f"使用备选方法为线路 {line_name} 方向 {direction} 构建站点顺序，共 {len(stations)} 个站点")
                        else:
                            # 如果无法获取线路站点，记录错误
                            logger.warning(f"无法获取线路 {line_name} 的站点列表")
        
        # 特殊处理1号线
        self._special_handle_line_one()

    def _special_handle_line_one(self):
        """特殊处理1号线的站点顺序"""
        one_line_variants = [line for line in self.all_lines if "1号线" in line or "一号线" in line]
        
        if one_line_variants:
            # 找到包含站点最多的一号线变体
            best_variant = None
            max_stations = 0
            
            for variant in one_line_variants:
                if variant in self.line_stations_order:
                    for direction, stations in self.line_stations_order[variant].items():
                        if len(stations) > max_stations:
                            max_stations = len(stations)
                            best_variant = variant
            
            # 如果找到最佳变体，为其他变体使用相同的站点顺序
            if best_variant:
                for variant in one_line_variants:
                    if variant != best_variant:
                        self.line_stations_order[variant] = self.line_stations_order[best_variant]
                
                # 确保简化版名称也有对应的站点顺序
                simple_names = ["1号线", "地铁1号线", "一号线", "地铁一号线"]
                for simple_name in simple_names:
                    if simple_name not in self.line_stations_order:
                        self.line_stations_order[simple_name] = self.line_stations_order[best_variant]

    def _get_line_path(self, start_station, end_station, line_name):
        """获取线路上从起始站到终点站的站点路径"""
        try:
            if hasattr(self.station_service, 'get_path'):
                path = self.station_service.get_path(start_station, end_station, line_name)
                if path:
                    return path
            
            path = self._build_path_with_bfs(start_station, end_station, line_name)
            if path:
                return path
            else:
                return None
        except Exception:
            return None
    
    def _build_path_with_bfs(self, start_station, end_station, line_name):
        """使用BFS算法构建从起始站到终点站的路径
        
        Args:
            start_station: 起始站点
            end_station: 终点站点
            line_name: 线路名称
            
        Returns:
            list: 站点路径列表，如果无法构建则返回None
        """
        if not self.station_service:
            return None
            
        from collections import deque
        
        queue = deque([(start_station, [start_station])])
        visited = set([start_station])
        
        while queue:
            current, path = queue.popleft()
            
            if current == end_station:
                return path
            
            try:
                adjacent_stations = self.station_service.get_adjacent_stations(current)
                
                for next_station in adjacent_stations:
                    if next_station not in visited:
                        is_on_same_line = False
                        
                        current_lines = self.station_service.get_all_lines(current)
                        next_lines = self.station_service.get_all_lines(next_station)
                        
                        for line in current_lines:
                            if (line == line_name or self._lines_are_similar(line, line_name)) and \
                               any(line == l or self._lines_are_similar(line, l) for l in next_lines):
                                is_on_same_line = True
                                break
                        
                        if is_on_same_line:
                            visited.add(next_station)
                            new_path = path + [next_station]
                            queue.append((next_station, new_path))
            except Exception:
                continue
        
        return None

    def get_station_path(self, start_station, end_station, line_name):
        """获取指定线路上两站之间的路径
        
        Args:
            start_station: 起始站点名称
            end_station: 终点站点名称
            line_name: 线路名称
            
        Returns:
            list: 站点路径列表，如果无法找到路径则返回None
        """
        if not self.station_service:
            return None
            
        normalized_line = self._normalize_line_name(line_name)
        
        try:
            if hasattr(self.station_service, 'get_path_between_stations'):
                path = self.station_service.get_path_between_stations(start_station, end_station, normalized_line)
                if path:
                    return path
        except Exception:
            pass
        
        if normalized_line in self.line_stations_order:
            for direction, stations in self.line_stations_order[normalized_line].items():
                try:
                    if start_station in stations and end_station in stations:
                        start_idx = stations.index(start_station)
                        end_idx = stations.index(end_station)
                        
                        if start_idx < end_idx:
                            path = stations[start_idx:end_idx+1]
                            return path
                        else:
                            path = stations[end_idx:start_idx+1]
                            path.reverse()
                            return path
                except Exception:
                    pass
        
        return self._build_path_with_bfs(start_station, end_station, normalized_line)

    def _calculate_station_time_offsets(self):
        """计算每个站点相对于首发站的时间偏移"""
        for line_name, directions in self.line_stations_order.items():
            self.line_station_offsets[line_name] = {}
            
            for direction, stations in directions.items():
                if not stations:
                    continue
                    
                self.line_station_offsets[line_name][direction] = {}
                first_station = stations[0]
                
                self.line_station_offsets[line_name][direction][first_station] = 0
                
                cumulative_offset = 0
                
                for i in range(1, len(stations)):
                    prev_station = stations[i-1]
                    curr_station = stations[i]
                    
                    travel_time = self._calculate_travel_time(prev_station, curr_station, line_name)
                    
                    stop_time = 0.5 if i > 1 else 0
                    
                    cumulative_offset += travel_time + stop_time
                    
                    self.line_station_offsets[line_name][direction][curr_station] = cumulative_offset

    def _calculate_travel_time(self, from_station, to_station, line_name):
        """计算两个站点之间的行驶时间（分钟）
        
        Args:
            from_station: 起始站点
            to_station: 目标站点
            line_name: 线路名称
            
        Returns:
            float: 行驶时间（分钟）
        """
        try:
            if self.station_service and hasattr(self.station_service, 'get_distance'):
                distance = self.station_service.get_distance(from_station, to_station, line_name)
                if distance > 0:
                    avg_speed = 40
                    
                    try:
                        import sys
                        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        from config import Config
                        
                        base_line_name = None
                        if "号线" in line_name:
                            match = re.search(r'(\d+)号线', line_name)
                            if match:
                                base_line_name = match.group(1) + "号线"
                        elif "机场线" in line_name:
                            base_line_name = "机场线"
                        elif "昌平线" in line_name:
                            base_line_name = "昌平线"
                        elif "房山线" in line_name:
                            base_line_name = "房山线"
                        elif "亦庄线" in line_name:
                            base_line_name = "亦庄线"
                        
                        if hasattr(Config, 'LINE_AVG_SPEEDS') and base_line_name and base_line_name in Config.LINE_AVG_SPEEDS:
                            avg_speed = Config.LINE_AVG_SPEEDS[base_line_name]
                    except Exception:
                        pass
                    
                    travel_time = (distance / 1000) / avg_speed * 60
                    return travel_time
            
            return 2.0
        except Exception:
            return 2.0

    def _normalize_line_name(self, line_name):
        """标准化线路名称，查找最匹配的完整线路名称"""
        # 先检查缓存
        if line_name in self.normalized_line_cache:
            return self.normalized_line_cache[line_name]
            
        if line_name in self.all_lines:
            self.normalized_line_cache[line_name] = line_name
            return line_name
            
        # 特殊处理1号线的情况
        if "1号线" in line_name or "一号线" in line_name or line_name == "1号线" or line_name == "地铁1号线":
            one_line_variants = [l for l in self.all_lines if "1号线" in l or "一号线" in l]
            if one_line_variants:
                # 按照长度排序，优先选择最长的名称（通常包含更多信息）
                sorted_variants = sorted(one_line_variants, key=len, reverse=True)
                result = sorted_variants[0]
                self.normalized_line_cache[line_name] = result
                return result
            
        if line_name in self.line_name_mapping:
            matches = self.line_name_mapping[line_name]
            if matches:
                # 按照长度排序，优先选择最长的名称
                result = sorted(matches, key=len, reverse=True)[0]
                self.normalized_line_cache[line_name] = result
                return result
        
        # 尝试基于包含关系查找
        for full_name in self.all_lines:
            if line_name in full_name or full_name in line_name or self._lines_are_similar(line_name, full_name):
                self.normalized_line_cache[line_name] = full_name
                return full_name
                
        # 模糊匹配：检查是否包含相同的数字
        line_numbers = re.findall(r'\d+', line_name)
        if line_numbers:
            for full_name in self.all_lines:
                full_name_numbers = re.findall(r'\d+', full_name)
                if line_numbers == full_name_numbers:
                    self.normalized_line_cache[line_name] = full_name
                    return full_name
        
        # 如果还是找不到，就返回原始名称
        self.normalized_line_cache[line_name] = line_name
        return line_name

    def _lines_are_similar(self, line1, line2):
        """判断两个线路名称是否相似"""
        # 如果都包含1号线，则视为相似
        if ("1号线" in line1 or "一号线" in line1) and ("1号线" in line2 or "一号线" in line2):
            return True
            
        def clean_name(name):
            return re.sub(r'\([^)]*\)', '', name).strip()
            
        clean1 = clean_name(line1)
        clean2 = clean_name(line2)
        
        if clean1 in clean2 or clean2 in clean1:
            return True
            
        num1 = re.search(r'(\d+)', clean1)
        num2 = re.search(r'(\d+)', clean2)
        
        if num1 and num2 and num1.group(1) == num2.group(1):
            return True
            
        special_lines = [
            ["昌平线", "地铁昌平线"], 
            ["房山线", "地铁房山线"],
            ["亦庄线", "地铁亦庄线"],
            ["燕房线", "地铁燕房线"],
            ["机场线", "首都机场线", "北京首都机场线"],
            ["S1", "S1线"],
            ["1号线", "地铁1号线", "一号线", "地铁一号线", "地铁1号线八通线"]
        ]
        
        for line_group in special_lines:
            if any(term in clean1 for term in line_group) and any(term in clean2 for term in line_group):
                return True
                
        return False

    def get_station_schedule(self, station_name: str, line_name: str, direction: str, date_type: str = "工作日") -> Dict[str, List[int]]:
        """获取指定站点的时刻表
        
        Args:
            station_name: 站点名称
            line_name: 线路名称
            direction: 方向, "1"表示上行(第一个站到最后一个站), "2"表示下行(最后一个站到第一个站)
            date_type: 日期类型，"工作日"或"双休日"
            
        Returns:
            dict: 站点时刻表，格式为 {小时: [分钟列表]}
        """
        try:
            normalized_line_name = self._normalize_line_name(line_name)
            
            if station_name in self.timetable_data:
                if normalized_line_name in self.timetable_data[station_name]:
                    line_data = self.timetable_data[station_name][normalized_line_name]
                    if direction in line_data and date_type in line_data[direction]:
                        return line_data[direction][date_type]
                
                for actual_line_name in self.timetable_data[station_name]:
                    if line_name in actual_line_name or self._lines_are_similar(line_name, actual_line_name):
                        line_data = self.timetable_data[station_name][actual_line_name]
                        if direction in line_data and date_type in line_data[direction]:
                            return line_data[direction][date_type]
            
            result = self._calculate_station_timetable_using_offset(station_name, normalized_line_name, direction, date_type)
            if result:
                return result
                
            for potential_line_name in self.line_station_offsets:
                if line_name in potential_line_name or self._lines_are_similar(line_name, potential_line_name):
                    result = self._calculate_station_timetable_using_offset(station_name, potential_line_name, direction, date_type)
                    if result:
                        return result
            
            return {}
            
        except Exception as e:
            logger.error(f"获取站点 {station_name} 时刻表时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    def get_station_timetable(self, station_name: str, line_name: str, direction: str, date_type: str = "工作日") -> Dict[str, List[int]]:
        """获取指定站点的时刻表（别名方法，功能与get_station_schedule相同）
        
        Args:
            station_name: 站点名称
            line_name: 线路名称
            direction: 方向, "1"表示上行(第一个站到最后一个站), "2"表示下行(最后一个站到第一个站)
            date_type: 日期类型，"工作日"或"双休日"
            
        Returns:
            dict: 站点时刻表，格式为 {小时: [分钟列表]}
        """
        return self.get_station_schedule(station_name, line_name, direction, date_type)
    
    def _calculate_station_timetable_using_offset(self, station_name, line_name, direction, date_type):
        """使用预计算的时间偏移计算站点时刻表"""
        try:
            normalized_line = self._normalize_line_name(line_name)
            
            if normalized_line not in self.line_station_offsets:
                return {}
                
            if direction not in self.line_station_offsets[normalized_line]:
                # 尝试查找其他方向
                if self.line_station_offsets[normalized_line]:
                    alt_direction = list(self.line_station_offsets[normalized_line].keys())[0]
                    logger.info(f"使用方向 {alt_direction} 作为 {direction} 的替代")
                    direction = alt_direction
                else:
                    return {}
            
            # 尝试精确匹配站点名称
            if station_name not in self.line_station_offsets[normalized_line][direction]:
                # 尝试容错匹配 - 检查空格、大小写和相似站点名称
                closest_match = self._find_closest_station_match(station_name, self.line_station_offsets[normalized_line][direction])
                
                if closest_match:
                    logger.info(f"找到站点 '{station_name}' 的最佳匹配: '{closest_match}'")
                    station_name = closest_match
                else:
                    # 检查该站是否在线路的任何方向上
                    for dir_key, stations in self.line_station_offsets[normalized_line].items():
                        closest_match = self._find_closest_station_match(station_name, stations)
                        if closest_match:
                            logger.info(f"站点 '{station_name}' 在线路 {normalized_line} 方向 {dir_key} 中找到匹配: '{closest_match}'")
                            direction = dir_key
                            station_name = closest_match
                            break
                    else:
                        return {}
            
            time_offset = self.line_station_offsets[normalized_line][direction][station_name]
            
            first_station = None
            for station, offset in self.line_station_offsets[normalized_line][direction].items():
                if offset == 0:
                    first_station = station
                    break
            
            if not first_station:
                return {}
            
            if first_station not in self.timetable_data:
                return {}
                
            matching_line = normalized_line
            if normalized_line not in self.timetable_data[first_station]:
                matching_line = None
                for line in self.timetable_data[first_station]:
                    if normalized_line in line or self._lines_are_similar(normalized_line, line):
                        matching_line = line
                        break
                        
                if not matching_line:
                    return {}
            
            first_station_data = self.timetable_data[first_station][matching_line]
            if direction not in first_station_data:
                # 尝试其他方向
                alt_directions = list(first_station_data.keys())
                if alt_directions:
                    direction = alt_directions[0]
                    logger.info(f"使用首发站 '{first_station}' 的方向 {direction} 作为替代")
                else:
                    return {}
                
            if date_type not in first_station_data[direction]:
                # 尝试其他日期类型
                alt_date_types = list(first_station_data[direction].keys())
                if alt_date_types:
                    date_type = alt_date_types[0]
                    logger.info(f"使用日期类型 {date_type} 作为替代")
                else:
                    return {}
            
            origin_schedule = first_station_data[direction][date_type]
            if not origin_schedule:
                return {}
                
            target_schedule = {}
            
            for hour_str, minutes in origin_schedule.items():
                if not minutes:  # 跳过空列表
                    continue
                    
                for minute in minutes:
                    base_time = datetime(2000, 1, 1, int(hour_str), minute)
                    arrival_time = base_time + timedelta(minutes=time_offset)
                    
                    arrival_hour = str(arrival_time.hour)
                    arrival_minute = arrival_time.minute
                    
                    if arrival_hour not in target_schedule:
                        target_schedule[arrival_hour] = []
                    
                    if arrival_minute not in target_schedule[arrival_hour]:
                        target_schedule[arrival_hour].append(arrival_minute)
            
            for hour in target_schedule:
                target_schedule[hour].sort()
            
            return target_schedule
        
        except Exception as e:
            logger.error(f"使用偏移量计算站点 '{station_name}' 的时刻表时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    def _find_closest_station_match(self, station_name, stations_dict):
        """查找最接近的站点名称匹配
        
        Args:
            station_name: 要查找的站点名称
            stations_dict: 站点字典 (站点名 -> 偏移值)
            
        Returns:
            str: 找到的最匹配站点名称，如果没有找到则返回None
        """
        if not station_name or not stations_dict:
            return None
            
        # 精确匹配
        if station_name in stations_dict:
            return station_name
            
        # 忽略空格匹配
        station_no_space = station_name.replace(' ', '')
        for name in stations_dict:
            if name.replace(' ', '') == station_no_space:
                return name
        
        # 忽略大小写匹配
        station_lower = station_name.lower()
        for name in stations_dict:
            if name.lower() == station_lower:
                return name
                
        # 包含匹配
        for name in stations_dict:
            if station_name in name or name in station_name:
                return name
        
        # 首字母缩写匹配（适用于拼音首字母）
        if all(ord('A') <= ord(c) <= ord('Z') for c in station_name):
            for name in stations_dict:
                initials = ''.join(word[0].upper() for word in name.split() if word)
                if initials == station_name:
                    return name
                    
        # 没有找到匹配
        return None

    def _find_next_train_in_timetable(self, timetable, current_time):
        """从时刻表中查找下一班车的发车时间
        
        Args:
            timetable: 时刻表数据，格式为 {小时: [分钟列表]}
            current_time: 当前时间
            
        Returns:
            datetime: 下一班车的发车时间，如果没有更多班次则返回None
        """
        if not timetable:
            return None
        
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        # 检查当前小时是否有还未发车的班次
        if str(current_hour) in timetable:
            for minute in sorted(timetable[str(current_hour)]):
                if minute > current_minute:
                    next_departure = datetime(
                        current_time.year, current_time.month, current_time.day,
                        current_hour, minute)
                    return next_departure
        
        # 检查之后的小时
        for hour in range(current_hour + 1, 24):
            if str(hour) in timetable and timetable[str(hour)]:
                minute = min(timetable[str(hour)])
                next_departure = datetime(
                    current_time.year, current_time.month, current_time.day,
                    hour, minute)
                return next_departure
        
        # 如果当前一天都没有找到，检查第二天的首班车
        for hour in range(0, current_hour + 1):
            if str(hour) in timetable and timetable[str(hour)]:
                minute = min(timetable[str(hour)])
                next_day = current_time + timedelta(days=1)
                next_departure = datetime(
                    next_day.year, next_day.month, next_day.day,
                    hour, minute)
                return next_departure
        
        return None

    def get_next_departure_safe(self, station_name, line_name, direction, current_time, date_type="工作日"):
        """安全地获取下一班车的发车时间
        
        Args:
            station_name: 站点名称
            line_name: 线路名称
            direction: 方向
            current_time: 当前时间
            date_type: 日期类型，默认为"工作日"
            
        Returns:
            datetime: 下一班车的发车时间，如果没有更多班次则返回None
        """
        try:
            # 获取站点时刻表
            timetable = self.get_station_schedule(station_name, line_name, direction, date_type)
            if not timetable:
                return None
                
            # 使用内部方法查找下一班车
            return self._find_next_train_in_timetable(timetable, current_time)
        except Exception as e:
            logger.error(f"查找下一班车时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

