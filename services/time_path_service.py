import heapq
import sys
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# 添加项目根目录到系统路径，以便导入config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

class TimePathService:
    """基于时间的最短路径查找服务"""
    
    def __init__(self, station_service, time_service):
        """
        初始化路径服务
        
        参数:
            station_service: StationService实例，用于获取站点和线路信息
            time_service: TimeService实例，用于获取时刻表信息
        """
        self.station_service = station_service
        self.time_service = time_service
        self.config = Config()
        # 设置当前日期
        self.current_date = datetime.now().date()
    
    def _calculate_wait_time(self, station, line, current_time, date_type):
        """计算在指定站点和线路上的等待时间"""
        try:
            logger.debug(f"尝试获取站点 {station} 的时刻表 (线路:{line}, 时间:{current_time.strftime('%H:%M')}, 日期类型:{date_type})")
            
            # 如果提供的线路为空或"未知"，尝试找出该站点的可能线路
            if not line or line == "未知":
                possible_lines = self.station_service.get_all_lines(station)
                if possible_lines:
                    line = possible_lines[0]  # 使用第一个可用线路
                    logger.debug(f"未指定线路，使用站点 {station} 的第一个可用线路: {line}")
                else:
                    logger.warning(f"站点 {station} 没有可用线路，使用默认等待时间")
                    return self.config.AVG_WAIT_TIME
            
            # 清理线路名称，删除可能导致查找失败的空格
            line = line.replace(" ", "")
            logger.debug(f"处理后的线路名称: '{line}'")
            
            # 同时尝试两个方向，选择最早到达的车次
            min_wait_time = float('inf')
            
            # 记录可用线路和方向信息，帮助调试
            logger.debug(f"站点 {station} 的所有线路: {self.station_service.get_all_lines(station)}")
            
            # 1. 首先，检查是否为环线
            is_loop_line = "内环" in line or "外环" in line
            simplified_line = line
            
            if is_loop_line:
                # 对环线提取基本线路名称
                if "号线" in line:
                    match = re.search(r'(\d+)号线', line)
                    if match:
                        simplified_line = match.group(1) + "号线"
                    
            # 2. 尝试不同的线路名称格式
            line_variations = [line, simplified_line]
            if "号线" in line:
                match = re.search(r'(\d+)号线', line)
                if match:
                    line_variations.append(f"地铁{match.group(1)}号线")
                    line_variations.append(match.group(1) + "号线")
            
            # 3. 尝试所有可能的线路名称和方向组合
            for line_var in line_variations:
                for direction in ["1", "2"]:
                    try:
                        logger.debug(f"尝试查询站点 {station} 线路 {line_var} 方向 {direction} 日期类型 {date_type} 的下一班车")
                        
                        # 使用time_service的get_next_departure_safe方法
                        next_train = self.time_service.get_next_departure_safe(
                            station, line_var, direction, current_time, date_type
                        )
                        
                        if next_train:
                            # 计算等待时间（分钟）
                            wait_minutes = (next_train - current_time).total_seconds() / 60
                            logger.debug(f"站点 {station} 在线路 {line_var} 方向 {direction} 的等待时间: {wait_minutes:.1f}分钟")
                            min_wait_time = min(min_wait_time, max(0, wait_minutes))  # 确保等待时间不为负
                        else:
                            logger.debug(f"站点 {station} 线路 {line_var} 方向 {direction} 没有找到下一班车，可能已末班车或无此线路方向组合")
                    except Exception as e:
                        logger.debug(f"获取站点 {station} 线路 {line_var} 方向 {direction} 时刻表出错: {str(e)}")
                        continue
            
            # 如果找到了有效的等待时间，返回最小等待时间
            if min_wait_time != float('inf'):
                return min_wait_time
                
            # 4. 如果所有尝试都失败，根据线路类型和时间估算等待时间
            hour = current_time.hour
            
            # 主要线路的高峰期和非高峰期等待时间估算
            if any(line_id in line for line_id in ["1号线", "2号线", "4号线", "5号线", "10号线"]):
                # 主干线路
                if 7 <= hour < 9 or 17 <= hour < 19:  # 高峰期
                    return 2.5  # 平均2.5分钟一班
                elif 6 <= hour < 23:  # 白天非高峰
                    return 4.0  # 平均4分钟一班
                else:  # 夜间
                    return 6.0  # 平均6分钟一班
            else:
                # 其他线路
                if 7 <= hour < 9 or 17 <= hour < 19:  # 高峰期
                    return 4.0  # 平均4分钟一班
                elif 6 <= hour < 23:  # 白天非高峰
                    return 5.5  # 平均5.5分钟一班
                else:  # 夜间
                    return 8.0  # 平均8分钟一班
                
        except Exception as e:
            logger.warning(f"计算站点 {station} 在线路 {line} 的等待时间出错: {str(e)}")
            return self.config.AVG_WAIT_TIME

    def _calculate_loop_line_wait_time(self, station, line, current_time, date_type):
        """为环线计算等待时间的专门方法"""
        # 环线使用简单的默认等待时间，不再考虑时刻表
        return 2.0

    def _calculate_travel_time(self, from_station, to_station, line):
        """计算两个站点之间的行驶时间（分钟）
        
        Args:
            from_station: 起始站点
            to_station: 目标站点
            line: 线路名称
            
        Returns:
            float: 行驶时间（分钟）
        """
        try:
            # 直接调用time_service的同名方法
            if hasattr(self.time_service, '_calculate_travel_time'):
                return self.time_service._calculate_travel_time(from_station, to_station, line)
            
            # 备用方案：基于距离计算行驶时间
            distance = self.station_service.get_distance(from_station, to_station, line)
            if distance > 0:
                # 设置默认平均速度为 40 km/h
                avg_speed = 40  # km/h
                
                # 计算行驶时间（分钟）= 距离(km) / 速度(km/h) * 60
                travel_time = (distance / 1000) / avg_speed * 60
                logger.debug(f"计算 {from_station} 到 {to_station} 在线路 {line} 上的行驶时间: {travel_time:.1f}分钟")
                return travel_time
            
            # 如果无法获取距离，使用默认值
            logger.warning(f"无法获取 {from_station} 到 {to_station} 在线路 {line} 上的距离，使用默认值3.0分钟")
            return 3.0
        except Exception as e:
            logger.warning(f"计算 {from_station} 到 {to_station} 在线路 {line} 的行驶时间出错: {str(e)}")
            # 出错时返回默认估算值
            return 3.0

    def find_path(self, start_station, end_station, departure_time=None, date_type="工作日", transfer_penalty=0):
        """
        通用路径查找方法，可根据transfer_penalty参数决定是最短时间还是最少换乘
        
        参数:
            start_station: 起始站点名称
            end_station: 目标站点名称
            departure_time: 出发时间，格式为"HH:MM"或datetime对象，默认为当前时间
            date_type: 日期类型，"工作日"或"双休日"
            transfer_penalty: 换乘惩罚系数，0表示不惩罚，用于最短时间；大值用于最少换乘
            
        返回:
            (path, total_time, time_details)
            - path: 站点路径列表
            - total_time: 总行程时间（分钟）
            - time_details: 详细时间信息字典
        """
        # 一、初始化阶段
        
        # 验证站点是否存在
        if not self.station_service.get_station_info(start_station):
            raise ValueError(f"起始站 '{start_station}' 不存在")
        
        if not self.station_service.get_station_info(end_station):
            raise ValueError(f"目标站 '{end_station}' 不存在")
        
        # 如果起点和终点是同一个站，直接返回
        if start_station == end_station:
            logger.info(f"起点和终点相同: {start_station}")
            return [start_station], 0, {}
            
        # 处理出发时间
        if departure_time is None:
            departure_time = datetime.now()
        elif isinstance(departure_time, str):
            # 将字符串时间转换为当前日期对应的datetime对象
            hour, minute = map(int, departure_time.split(':'))
            departure_time = datetime.combine(self.current_date, datetime.min.time()).replace(hour=hour, minute=minute)
        
        # 初始化数据结构
        # 优先队列元素: (累计时间, 唯一ID, 站点, 到达时间, 当前线路, 换乘次数, 路径, 详细信息字典)
        queue = [(0, 0, start_station, departure_time, None, 0, [start_station], {})]
        # 使用字典记录站点已知的最短时间，键为(站点,线路)，值为总时间
        best_times = defaultdict(lambda: float('inf'))
        best_times[(start_station, None)] = 0
        
        # 已处理的站点集合
        processed = set()
        
        # 唯一ID计数器，确保相同时间的站点在队列中的排序稳定
        counter = 1
        
        # 添加迭代计数和最大迭代限制，防止无限循环
        iterations = 0
        max_iterations = 100000
        
        # 二、主循环阶段 - Dijkstra算法
        while queue and iterations < max_iterations:
            iterations += 1
            
            # 从优先队列中取出时间最短的站点
            time_so_far, _, current, current_time, current_line, transfers, path, details = heapq.heappop(queue)
            
            # 1. 判断是否到达终点
            if current == end_station:
                # 找到终点，计算实际行程时间（不含惩罚）
                actual_travel_time = self.recalculate_time_with_backtracking(path, departure_time, details)
                return path, actual_travel_time, details
            
            # 2. 检查是否已有更优解
            if (current, current_line) in processed or time_so_far > best_times[(current, current_line)]:
                continue
                
            # 3. 标记当前站点为已处理
            processed.add((current, current_line))
            
            # 4. 探索所有未处理的邻接站点
            neighbors = self.station_service.get_adjacent_stations(current)
            if not neighbors:
                continue
                
            for neighbor in neighbors:
                # 获取可用线路
                current_lines = set(self.station_service.get_all_lines(current))
                neighbor_lines = set(self.station_service.get_all_lines(neighbor))
                common_lines = current_lines.intersection(neighbor_lines)
                
                if not common_lines:
                    continue  # 无公共线路，跳过
                
                # 5. 优先考虑当前线路，避免不必要的换乘
                if current_line in common_lines:
                    # 将当前线路放在列表前面
                    common_lines_ordered = [current_line] + [l for l in common_lines if l != current_line]
                else:
                    common_lines_ordered = list(common_lines)
                
                # 6. 对每条可能的线路进行评估
                for line in common_lines_ordered:
                    # 7. 判断是否需要换乘
                    is_transfer = current_line is not None and current_line != line
                    transfer_time = self.config.TRANSFER_TIME if is_transfer else 0
                    
                    # 根据参数计算换乘惩罚，只影响搜索优先级，不影响实际时间
                    transfer_penalty_value = transfer_penalty if is_transfer else 0
                    
                    new_transfers = transfers + (1 if is_transfer else 0)
                    
                    # 8. 计算等待时间
                    wait_time = 0
                    if current_line is None or is_transfer:  # 起始站或换乘站需要等待
                        # 考虑换乘后的时间点
                        transfer_complete_time = current_time + timedelta(minutes=transfer_time)
                        
                        # 检查是否是环线
                        is_loop_line = "内环" in line or "外环" in line
                        if not is_loop_line:
                            try:
                                terminal_stations = self.time_service._extract_terminal_stations(line)
                                if terminal_stations and terminal_stations[0] == terminal_stations[1]:
                                    is_loop_line = True
                            except:
                                pass
                        
                        # 计算等待时间
                        wait_time = 2.0 if is_loop_line else self._calculate_wait_time(current, line, transfer_complete_time, date_type)
                    
                    # 9. 计算行驶时间
                    travel_time = self._calculate_travel_time(current, neighbor, line)
                    if travel_time == float('inf'):  # 处理无效距离
                        continue  # 尝试下一条线路
                    
                    # 10. 考虑停站时间
                    stop_time = self.config.STOP_TIME if len(path) > 1 else 0
                    
                    # 11. 计算新的累计时间和到达时间
                    # 分开计算实际时间和搜索时间（包含惩罚）
                    actual_segment_time = transfer_time + wait_time + travel_time + stop_time
                    algorithm_time = actual_segment_time + transfer_penalty_value
                    
                    new_time = time_so_far + algorithm_time
                    arrival_time = current_time + timedelta(minutes=actual_segment_time)
                    
                    # 12. 只有找到更好的路径时才更新
                    if new_time < best_times[(neighbor, line)]:
                        best_times[(neighbor, line)] = new_time
                        
                        # 13. 更新路径和详细信息
                        new_path = path + [neighbor]
                        new_details = details.copy()
                        segment = (current, neighbor)
                        new_details[segment] = {
                            'line': line,
                            'transfer_time': transfer_time,
                            'wait_time': wait_time,
                            'travel_time': travel_time,
                            'stop_time': stop_time,
                            'transfer_penalty': transfer_penalty_value, # 记录惩罚值，但不计入实际时间
                            'departure_time': current_time + timedelta(minutes=transfer_time + wait_time),
                            'arrival_time': arrival_time,
                            'is_transfer': is_transfer,
                            'estimated': travel_time == 3.0  # 标记是否为估算值
                        }
                        
                        # 14. 将新状态加入优先队列
                        heapq.heappush(queue, 
                            (new_time, counter, neighbor, arrival_time, line, new_transfers, new_path, new_details))
                        counter += 1
        
        # 三、结果处理阶段
        # 如果无法到达终点站或超过最大迭代次数，返回空结果
        if iterations >= max_iterations:
            logger.warning(f"搜索超过最大迭代次数 {max_iterations}，搜索终止")
        else:
            logger.warning(f"无法找到从 {start_station} 到 {end_station} 的路径")
        
        return [], 0, {}

    def find_optimized_shortest_time_path(self, start_station, end_station, departure_time=None, date_type="工作日"):
        """
        使用优化的Dijkstra算法查找最短时间路径
        
        参数:
            start_station: 起始站点名称
            end_station: 目标站点名称
            departure_time: 出发时间，格式为"HH:MM"或datetime对象，默认为当前时间
            date_type: 日期类型，"工作日"或"双休日"
            
        返回:
            (path, total_time, time_details)
        """
        # 调用通用方法，不设置换乘惩罚
        return self.find_path(start_station, end_station, departure_time, date_type, transfer_penalty=0)

    def recalculate_time_with_backtracking(self, path, start_time, time_details=None):
        """
        使用回溯算法重新计算路径的实际行程时间
        
        Args:
            path: 路径站点列表
            start_time: 出发时间
            time_details: 已有的时间详情（可选）
            
        Returns:
            float: 实际行程时间（分钟）
        """
        if not path or len(path) < 2:
            return 0
            
        current_time = start_time
        total_time = 0
        current_line = None
        
        # 按站点顺序重新计算
        for i in range(len(path) - 1):
            from_station = path[i]
            to_station = path[i+1]
            segment = (from_station, to_station)
            
            # 确定当前线路
            line = None
            if time_details and segment in time_details:
                line = time_details[segment]['line']
            else:
                # 尝试找到连接两站的线路
                from_lines = set(self.station_service.get_all_lines(from_station))
                to_lines = set(self.station_service.get_all_lines(to_station))
                common_lines = from_lines.intersection(to_lines)
                if common_lines:
                    # 优先使用当前线路
                    if current_line in common_lines:
                        line = current_line
                    else:
                        line = next(iter(common_lines))
                        
            if not line:
                logger.warning(f"无法确定 {from_station} 到 {to_station} 之间的线路")
                continue
                
            # 判断是否换乘
            is_transfer = current_line is not None and current_line != line
            transfer_time = self.config.TRANSFER_TIME if is_transfer else 0
            
            # 计算等待时间
            wait_time = 0
            if i == 0 or is_transfer:  # 起始站或换乘站需要等待
                # 考虑换乘后的时间
                transfer_complete_time = current_time + timedelta(minutes=transfer_time)
                date_type = "工作日" if transfer_complete_time.weekday() < 5 else "双休日"
                
                # 环线处理
                is_loop_line = "内环" in line or "外环" in line
                if not is_loop_line:
                    try:
                        terminal_stations = self.time_service._extract_terminal_stations(line)
                        if terminal_stations and terminal_stations[0] == terminal_stations[1]:
                            is_loop_line = True
                    except:
                        pass
                
                wait_time = 2.0 if is_loop_line else self._calculate_wait_time(from_station, line, transfer_complete_time, date_type)
            
            # 计算行驶时间
            travel_time = self._calculate_travel_time(from_station, to_station, line)
            
            # 考虑停站时间（非起始站）
            stop_time = self.config.STOP_TIME if i > 0 else 0
            
            # 更新当前时间
            segment_time = transfer_time + wait_time + travel_time + stop_time
            current_time += timedelta(minutes=segment_time)
            
            # 累计总时间
            total_time += segment_time
            
            # 更新当前线路
            current_line = line
            
        return total_time
        
    def count_transfers_correctly(self, path, time_details):
        """计算路径中的正确换乘次数
        
        Args:
            path: 站点路径列表
            time_details: 路径详细信息字典
            
        Returns:
            int: 换乘次数
        """
        transfers = 0
        current_line = None
        
        # 遍历所有路段，按顺序
        segments = []
        for i in range(len(path) - 1):
            segment = (path[i], path[i+1])
            if segment in time_details:
                segments.append(segment)
        
        for segment in segments:
            details = time_details[segment]
            line = details['line']
            
            # 第一个线路不计算换乘
            if current_line is None:
                current_line = line
            # 只有当线路变化时才计算换乘
            elif current_line != line and line != '未知':
                transfers += 1
                current_line = line
        
        return transfers
        
    def format_path_details(self, path, time_details):
        """格式化路径详细信息，生成易读的路径描述
        
        Args:
            path: 站点路径列表
            time_details: 路径详细信息字典
            
        Returns:
            str: 格式化后的路径描述
        """
        if not path or len(path) < 2:
            return "无有效路径"
            
        result = []
        current_line = None
        total_time = 0
        
        for i in range(len(path) - 1):
            segment = (path[i], path[i+1])
            if segment not in time_details:
                continue
                
            details = time_details[segment]
            line = details.get('line', '未知')
            
            # 处理换乘信息
            if current_line is None:
                result.append(f"从 {path[0]} 站乘坐 {line}")
                current_line = line
            elif current_line != line and line != '未知':
                result.append(f"在 {path[i]} 站换乘 {line}")
                current_line = line
                
            # 添加行程详情
            transfer_time = details.get('transfer_time', 0)
            wait_time = details.get('wait_time', 0)
            travel_time = details.get('travel_time', 0)
            
            departure_time = details.get('departure_time')
            arrival_time = details.get('arrival_time')
            
            if departure_time and arrival_time:
                result.append(f"  {path[i]} → {path[i+1]} ({line}): {departure_time.strftime('%H:%M')} 出发 - {arrival_time.strftime('%H:%M')} 到达")
            else:
                result.append(f"  {path[i]} → {path[i+1]} ({line}): 行程 {travel_time:.1f} 分钟")
                
            total_time += transfer_time + wait_time + travel_time
            
        result.append(f"\n总行程: {len(path)}站, {self.count_transfers_correctly(path, time_details)}次换乘, {total_time:.1f}分钟")
        
        return "\n".join(result)
        
    def _calculate_fare(self, distance_km):
        """计算票价 (人民币元)
        
        Args:
            distance_km: 距离(公里)
            
        Returns:
            float: 票价(元)
        """
        if distance_km <= 6:
            return 3.0
        elif distance_km <= 12:
            return 4.0
        elif distance_km <= 22:
            return 5.0
        elif distance_km <= 32:
            return 6.0
        else:
            # 32公里以上，每20公里增加1元
            extra_km = distance_km - 32
            extra_fee = (extra_km // 20) + (1 if extra_km % 20 > 0 else 0)
            return 6.0 + extra_fee

