import logging
from .time_path_service import TimePathService
from datetime import timedelta

logger = logging.getLogger(__name__)

class TransferPathService(TimePathService):
    """最少换乘路径服务类，通过给换乘增加巨大权重来优先寻找换乘次数最少的路径"""
    
    def __init__(self, station_service, time_service):
        """初始化最少换乘路径服务"""
        super().__init__(station_service, time_service)
        # 设置换乘惩罚（分钟），这个值需要足够大以确保算法优先考虑换乘次数
        self.TRANSFER_PENALTY = 10000
    
    def find_least_transfers_path(self, start_station, end_station, departure_time=None, date_type="工作日"):
        """
        查找从起始站到终点站的最少换乘路径
        
        参数:
            start_station: 起始站点名称
            end_station: 目标站点名称
            departure_time: 出发时间，默认为当前时间
            date_type: 日期类型，"工作日"或"双休日"
            
        返回:
            (path, total_time, time_details)
        """
        # 调用基类的通用方法，设置大的换乘惩罚值
        return self.find_path(start_station, end_station, departure_time, date_type, transfer_penalty=self.TRANSFER_PENALTY)
    
    def get_actual_travel_time(self, time_details):
        """
        计算实际行程时间（不包括换乘惩罚）
        
        Args:
            time_details: 路径详细信息字典
            
        Returns:
            float: 实际行程时间（分钟）
        """
        if not time_details:
            return 0
            
        # 使用回溯算法重新计算精确时间
        if len(time_details) > 0:
            # 获取路径
            segments = list(time_details.keys())
            
            # 提取完整路径
            if segments:
                path = [segments[0][0]]  # 添加起点
                for segment in segments:
                    path.append(segment[1])  # 添加每个终点
                
                # 获取出发时间
                first_segment = segments[0]
                departure_time = time_details[first_segment].get('departure_time')
                
                if departure_time and path:
                    # 使用父类的回溯算法重新计算时间
                    return super().recalculate_time_with_backtracking(path, departure_time, time_details)
        
        # 如果无法使用回溯算法，使用原始方法计算
        total_time = 0
        for segment, details in time_details.items():
            transfer_time = details.get('transfer_time', 0)
            wait_time = details.get('wait_time', 0)
            travel_time = details.get('travel_time', 0)
            stop_time = details.get('stop_time', 0)
            
            # 确保不包含任何惩罚值
            segment_time = transfer_time + wait_time + travel_time + stop_time
            total_time += segment_time
            
        return total_time
