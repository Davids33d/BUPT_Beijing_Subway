import os
import sys

def get_project_root():
    """获取项目根目录，兼容开发环境和PyInstaller打包环境"""
    # 判断是否运行于打包环境中
    if getattr(sys, 'frozen', False):
        # 如果是PyInstaller打包后的程序，使用可执行文件所在目录作为根目录
        application_path = os.path.dirname(sys.executable)
        return application_path
    else:
        # 开发环境下使用文件所在目录
        return os.path.dirname(os.path.abspath(__file__))

def ensure_directory_exists(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"创建目录: {directory}")

class Config:
    """配置类，包含系统中使用的各种配置参数"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-subway-app'
    
    # 项目根目录
    PROJECT_ROOT = get_project_root()
    
    # 数据文件路径
    DATA_DIR = os.path.join(PROJECT_ROOT, "geo_data")
    STATIONS_FILE = os.path.join(PROJECT_ROOT, "distance_data", "station.json")  # 添加站点文件引用，指向已存在的文件
    
    # 地理数据目录
    GEO_DATA_DIR = os.path.join(PROJECT_ROOT, "geo_data")
    
    # 距离数据目录
    DISTANCE_DATA_DIR = os.path.join(PROJECT_ROOT, "distance_data")
    STATION_DISTANCE_FILE = os.path.join(DISTANCE_DATA_DIR, "station.json")
    
    # 时刻表数据目录
    TIME_DATA_DIR = os.path.join(PROJECT_ROOT, "time_data")
    TIME_FILE = os.path.join(TIME_DATA_DIR, "time.json")
    
    # 静态文件和模板目录
    STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
    TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates") 
    
    # 确保输出目录存在
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
    
    # Mapbox配置
    MAPBOX_TOKEN = os.environ.get('MAPBOX_TOKEN') or 'pk.eyJ1IjoiN2JiM28zNXIiLCJhIjoiY205M3VjOW4yMG5vbTJtczVucXkxOHVkYSJ9.B0fzE18djLYhlNicek69Gg'
    
    # 地铁系统配置
    TRANSFER_TIME = 5  # 换乘耗时(分钟)
    STOP_TIME = 1      # 每站停留时间(分钟)
    AVG_WAIT_TIME = 3  # 平均等待时间(分钟)，当时刻表不可用时使用
    
    # 默认票价
    BASE_FARE = 3      # 基本票价(元)
    FARE_PER_KM = 0.1  # 每公里增加票价(元)
    
    # 票价计算规则
    FARE_RULES = [
        (6, 3),    # 6公里(含)内3元
        (12, 4),   # 6公里至12公里(含)4元
        (22, 5),   # 12公里至22公里(含)5元
        (32, 6),   # 22公里至32公里(含)6元
    ]
    FARE_ADDITIONAL_RATE = 20  # 32公里以上，每20公里增加1元
    
    # 默认速度 (km/h)，当没有为线路特别指定速度时使用
    DEFAULT_SPEED = 35.0
    
    # 各线路的平均速度 (km/h)
    LINE_AVG_SPEEDS = {
        "1号线": 37.5,
        "2号线": 40.0,
        "4号线": 45.0,
        "5号线": 40.0,
        "6号线": 50.0,
        "7号线": 40.0,
        "8号线": 40.0,
        "9号线": 40.0,
        "10号线": 40.0,
        "11号线": 50.0,
        "13号线": 37.5,
        "14号线": 37.5,
        "15号线": 40.0,
        "16号线": 40.0,
        "17号线": 50.0,
        "19号线": 60.0,
        "昌平线": 50.0,
        "房山线": 50.0,
        "亦庄线": 40.0,
        "首都机场线": 55.0,
        "燕房线": 40.0,
        "S1线": 50.0,
        "西郊线": 35.0,
        "大兴机场线": 80.0,
        "亦庄线T1线": 40.0,
    }
    
    @classmethod
    def init_app_directories(cls):
        """初始化应用程序所需的所有目录"""
        directories = [
            cls.DATA_DIR,
            cls.DISTANCE_DATA_DIR, 
            cls.TIME_DATA_DIR,
            cls.STATIC_DIR,
            cls.TEMPLATES_DIR,
            cls.OUTPUT_DIR
        ]
        
        for directory in directories:
            ensure_directory_exists(directory)
        
        print("已初始化所有必要目录")