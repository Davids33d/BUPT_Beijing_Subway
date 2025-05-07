import os
import json
import logging
from config import Config
from typing import Dict, List, Optional
from pathlib import Path

class TimetableManager:
    """时刻表管理器，提供地铁时刻表的增删改查功能"""
    
    def __init__(self):
        """初始化时刻表管理器"""
        # 修改文件路径，使用time_data目录下的time.json文件
        self.timetable_file = "d:/pythonProject/subway/time_data/time.json"
        
    def _ensure_timetable_file(self):
        """确保时刻表文件存在"""
        if not os.path.exists(self.timetable_file):
            os.makedirs(os.path.dirname(self.timetable_file), exist_ok=True)
            with open(self.timetable_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    def load_timetable_data(self):
        """加载时刻表数据"""
        try:
            if os.path.exists(self.timetable_file):
                with open(self.timetable_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"加载时刻表数据失败: {str(e)}")
            return {}
    
    def save_timetable_data(self, timetable_data):
        """保存时刻表数据"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.timetable_file), exist_ok=True)
            
            with open(self.timetable_file, 'w', encoding='utf-8') as f:
                json.dump(timetable_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存时刻表数据失败: {str(e)}")
            return False
    
    def update_timetable_for_line(self, line_name, start_station, end_station, timetable_data):
        """更新指定线路的时刻表数据"""
        try:
            # 加载当前时刻表数据
            current_timetable = self.load_timetable_data()
            
            # 完整的线路名称
            full_line_name = f"{line_name}({start_station}--{end_station})"
            
            # 从timetable_data中提取各部分时刻表
            workday_start = timetable_data.get("workday_start", {})
            workday_end = timetable_data.get("workday_end", {})
            weekend_start = timetable_data.get("weekend_start", {})
            weekend_end = timetable_data.get("weekend_end", {})
            
            # 更新始发站的时刻表数据 - 上行方向(1)
            if start_station not in current_timetable:
                current_timetable[start_station] = {}
                
            if full_line_name not in current_timetable[start_station]:
                current_timetable[start_station][full_line_name] = {}
                
            if "1" not in current_timetable[start_station][full_line_name]:
                current_timetable[start_station][full_line_name]["1"] = {}
                
            # 使用中文键名存储始发站工作日和双休日数据
            current_timetable[start_station][full_line_name]["1"]["工作日"] = workday_start
            current_timetable[start_station][full_line_name]["1"]["双休日"] = weekend_start
            
            # 更新终点站的时刻表数据 - 下行方向(2)
            if end_station not in current_timetable:
                current_timetable[end_station] = {}
                
            if full_line_name not in current_timetable[end_station]:
                current_timetable[end_station][full_line_name] = {}
                
            if "2" not in current_timetable[end_station][full_line_name]:
                current_timetable[end_station][full_line_name]["2"] = {}
                
            # 使用中文键名存储终点站工作日和双休日数据
            current_timetable[end_station][full_line_name]["2"]["工作日"] = workday_end
            current_timetable[end_station][full_line_name]["2"]["双休日"] = weekend_end
            
            # 保存更新后的时刻表
            self.save_timetable_data(current_timetable)
            
            return {
                "success": True, 
                "message": f"已成功更新线路 '{full_line_name}' 的时刻表"
            }
        except Exception as e:
            return {
                "success": False, 
                "message": f"更新时刻表失败: {str(e)}"
            }
    
    def update_timetable_data(self, timetable_data):
        """更新整个时刻表数据（保留旧实现以兼容）"""
        try:
            current_timetable = self.load_timetable_data()
            
            # 合并新旧时刻表数据
            for station, station_data in timetable_data.items():
                if station not in current_timetable:
                    current_timetable[station] = {}
                
                for line, line_data in station_data.items():
                    if line in current_timetable[station]:
                        # 检查是否需要添加前缀编号
                        existing_data = current_timetable[station][line]
                        if isinstance(existing_data, dict) and any(k.isdigit() for k in existing_data.keys()):
                            # 已有编号的情况，找到最大编号并加1
                            current_count = max(int(k) for k in existing_data.keys() if k.isdigit()) + 1
                            current_timetable[station][line][str(current_count)] = line_data
                        else:
                            # 没有编号的情况，将原数据移至"1"，新数据放在"2"
                            new_data = {
                                "1": existing_data,
                                "2": line_data
                            }
                            current_timetable[station][line] = new_data
                    else:
                        # 第一次添加
                        current_timetable[station][line] = line_data
            
            # 保存更新后的时刻表
            self.save_timetable_data(current_timetable)
            return True
        except Exception as e:
            logging.error(f"更新时刻表数据失败: {str(e)}")
            return False
    
    def _clean_empty_structures(self, timetable, station_name, line_name=None, direction=None):
        """清理空的结构
        
        Args:
            timetable: 时刻表数据
            station_name: 站点名称
            line_name: 线路名称，如不指定则只检查站点
            direction: 方向，如不指定则只检查线路
        """
        # 如果站点不存在，直接返回
        if station_name not in timetable:
            return
        
        # 如果站点的所有线路都为空，删除站点
        if not timetable[station_name]:
            del timetable[station_name]
            return
        
        # 如果未指定线路名称，直接返回
        if line_name is None:
            return
        
        # 如果线路不存在，直接返回
        if line_name not in timetable[station_name]:
            return
        
        # 如果线路的所有方向都为空，删除线路
        if not timetable[station_name][line_name]:
            del timetable[station_name][line_name]
            # 如果站点的所有线路都为空，删除站点
            if not timetable[station_name]:
                del timetable[station_name]
            return

    def get_line_terminal_stations(self, line_name: str):
        """从线路名中提取始发站和终点站
        
        Args:
            line_name: 完整线路名称，如 "地铁15号线(俸伯--清华东路西口)"
            
        Returns:
            tuple: (始发站，终点站)
        """
        try:
            # 提取括号中的内容
            stations_part = line_name.split('(')[1].split(')')[0]
            # 分割始发站和终点站
            start_station, end_station = stations_part.split('--')
            return start_station, end_station
        except Exception:
            return None, None
    
    def update_timetable_for_station(self, station_name, line_name, direction, date_type, timetable_data):
        """更新特定站点、线路、方向和日期类型的时刻表数据
        
        Args:
            station_name: 站点名称
            line_name: 线路名称
            direction: 方向 (1: 上行, 2: 下行)
            date_type: 日期类型 (工作日, 双休日)
            timetable_data: 时刻表数据
            
        Returns:
            dict: 操作结果
        """
        try:
            # 加载当前时刻表数据
            current_timetable = self.load_timetable_data()
            
            # 检查站点是否存在
            if station_name not in current_timetable:
                current_timetable[station_name] = {}
            
            # 检查线路是否存在
            if line_name not in current_timetable[station_name]:
                current_timetable[station_name][line_name] = {}
            
            # 检查方向是否存在
            if direction not in current_timetable[station_name][line_name]:
                current_timetable[station_name][line_name][direction] = {}
            
            # 更新指定日期类型的时刻表
            if timetable_data:
                current_timetable[station_name][line_name][direction][date_type] = timetable_data
            else:
                # 如果时刻表数据为空，删除该日期类型的时刻表
                if date_type in current_timetable[station_name][line_name][direction]:
                    del current_timetable[station_name][line_name][direction][date_type]
            
            # 清理空结构
            self._clean_empty_structures(current_timetable, station_name, line_name, direction)
            
            # 保存更新后的时刻表
            self.save_timetable_data(current_timetable)
            
            return {
                "success": True,
                "message": f"已成功更新 '{station_name}' 站 '{line_name}' 线路的 {date_type} 时刻表"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"更新时刻表失败: {str(e)}"
            }
    
    def delete_timetable_entry(self, station_name, line_name=None, direction=None, date_type=None):
        """删除时刻表条目
        
        Args:
            station_name: 站点名称
            line_name: 线路名称，如不指定则删除整个站点的时刻表
            direction: 方向，如不指定则删除整个线路的时刻表
            date_type: 日期类型，如不指定则删除整个方向的时刻表
            
        Returns:
            dict: 操作结果
        """
        try:
            # 加载当前时刻表数据
            current_timetable = self.load_timetable_data()
            
            # 如果站点不存在，直接返回成功
            if station_name not in current_timetable:
                return {
                    "success": True,
                    "message": f"站点 '{station_name}' 不存在，无需删除"
                }
            
            # 如果未指定线路名称，删除整个站点
            if line_name is None:
                del current_timetable[station_name]
                self.save_timetable_data(current_timetable)
                return {
                    "success": True,
                    "message": f"已删除站点 '{station_name}' 的所有时刻表"
                }
            
            # 如果线路不存在，直接返回成功
            if line_name not in current_timetable[station_name]:
                return {
                    "success": True,
                    "message": f"线路 '{line_name}' 不存在，无需删除"
                }
            
            # 如果未指定方向，删除整个线路
            if direction is None:
                # 提取始发站和终点站
                start_station, end_station = self.get_line_terminal_stations(line_name)
                
                # 删除线路相关的所有站点的时刻表数据
                if start_station and start_station in current_timetable and line_name in current_timetable[start_station]:
                    del current_timetable[start_station][line_name]
                    # 清理空站点
                    self._clean_empty_structures(current_timetable, start_station)
                
                if end_station and end_station in current_timetable and line_name in current_timetable[end_station]:
                    del current_timetable[end_station][line_name]
                    # 清理空站点
                    self._clean_empty_structures(current_timetable, end_station)
                
                del current_timetable[station_name][line_name]
                # 清理空站点
                self._clean_empty_structures(current_timetable, station_name)
                self.save_timetable_data(current_timetable)
                return {
                    "success": True,
                    "message": f"已删除线路 '{line_name}' 的所有时刻表"
                }
            
            # 如果方向不存在，直接返回成功
            if direction not in current_timetable[station_name][line_name]:
                return {
                    "success": True,
                    "message": f"方向 '{direction}' 不存在，无需删除"
                }
            
            # 如果未指定日期类型，删除整个方向
            if date_type is None:
                del current_timetable[station_name][line_name][direction]
                # 清理空结构
                self._clean_empty_structures(current_timetable, station_name, line_name)
                self.save_timetable_data(current_timetable)
                return {
                    "success": True,
                    "message": f"已删除站点 '{station_name}' 的线路 '{line_name}' 的方向 '{direction}' 的所有时刻表"
                }
            
            # 如果日期类型不存在，直接返回成功
            if date_type not in current_timetable[station_name][line_name][direction]:
                return {
                    "success": True,
                    "message": f"日期类型 '{date_type}' 不存在，无需删除"
                }
            
            # 删除指定日期类型的时刻表
            del current_timetable[station_name][line_name][direction][date_type]
            
            # 清理空结构
            self._clean_empty_structures(current_timetable, station_name, line_name, direction)
            
            # 保存更新后的时刻表
            self.save_timetable_data(current_timetable)
            
            return {
                "success": True,
                "message": f"已删除站点 '{station_name}' 的线路 '{line_name}' 的方向 '{direction}' 的日期类型 '{date_type}' 的时刻表"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"删除时刻表失败: {str(e)}"
            }

