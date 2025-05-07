"""
应用程序启动脚本 - 用于PyInstaller打包
"""
# 首先导入所需模块
import os
import sys
import shutil
import logging
from pathlib import Path
import json

# 配置基本日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('BeijingSubway')

# 设置正确的应用程序路径和工作目录
def setup_app_environment():
    # 获取应用程序路径
    if getattr(sys, 'frozen', False):
        # 如果应用程序被冻结（PyInstaller打包）
        app_path = os.path.dirname(sys.executable)
        logger.info(f"在打包环境中运行，应用路径: {app_path}")
        # 设置工作目录为可执行文件所在目录
        os.chdir(app_path)
        
        # 修正所有的路径引用，使用相对路径而非硬编码路径
        patch_absolute_paths()
    else:
        # 开发环境
        app_path = os.path.dirname(os.path.abspath(__file__))
        logger.info(f"在开发环境中运行，应用路径: {app_path}")

    # 确保必要的数据目录存在
    ensure_data_directories()
    
    return app_path

# 修正代码中的硬编码绝对路径
def patch_absolute_paths():
    try:
        # 修补app.py中的路径引用
        import app
        
        # 重写硬编码的路径访问函数
        original_get_station_points = app.get_station_points
        def patched_get_station_points():
            try:
                # 使用相对路径替换硬编码路径
                point_json_path = os.path.join('geo_data', 'point.json')
                logger.info(f"访问站点数据文件: {point_json_path}")
                
                if not os.path.exists(point_json_path):
                    return app.jsonify({
                        "type": "FeatureCollection",
                        "features": []
                    })
                    
                with open(point_json_path, 'r', encoding='utf-8') as f:
                    geo_data = json.load(f)
                    logger.info(f"成功加载站点数据: {len(geo_data.get('features', []))}个站点")
                
                return app.jsonify(geo_data)
            except Exception as e:
                logger.error(f"获取站点数据时出错: {str(e)}", exc_info=True)
                return app.jsonify({'error': str(e)}), 500
        
        # 替换原始函数
        app.get_station_points = patched_get_station_points
        
        # 同样修补获取线路数据的函数
        original_get_line_geojson = app.get_line_geojson
        def patched_get_line_geojson():
            try:
                # 使用相对路径替换硬编码路径
                line_geojson_file = os.path.join('geo_data', 'line.geojson')
                logger.info(f"访问线路数据文件: {line_geojson_file}")
                
                # 在日志中添加文件是否存在的信息，帮助调试
                if os.path.exists(line_geojson_file):
                    logger.info(f"线路数据文件存在，大小: {os.path.getsize(line_geojson_file)} 字节")
                else:
                    logger.warning(f"线路数据文件不存在: {line_geojson_file}")
                
                if not os.path.exists(line_geojson_file):
                    return app.jsonify({
                        "type": "FeatureCollection",
                        "features": []
                    })
                
                with open(line_geojson_file, 'r', encoding='utf-8') as f:
                    lines_data = json.load(f)
                
                return app.jsonify(lines_data)
            except Exception as e:
                logger.error(f"获取线路数据失败: {str(e)}", exc_info=True)
                return app.jsonify({'error': str(e)}), 500
        
        # 替换原始函数
        app.get_line_geojson = patched_get_line_geojson
        
        logger.info("已修补硬编码路径引用")
        
        # 同时修补配置模块中的路径
        import config
        config.Config.GEO_DATA_DIR = os.path.abspath('geo_data')
        config.Config.DISTANCE_DATA_DIR = os.path.abspath('distance_data')
        config.Config.TIME_DATA_DIR = os.path.abspath('time_data')
        config.Config.STATION_DISTANCE_FILE = os.path.abspath(os.path.join('distance_data', 'station.json'))
        config.Config.TIME_FILE = os.path.abspath(os.path.join('time_data', 'time.json'))
        
        logger.info(f"已修正配置路径: GEO_DATA_DIR = {config.Config.GEO_DATA_DIR}")
        logger.info(f"已修正配置路径: STATION_DISTANCE_FILE = {config.Config.STATION_DISTANCE_FILE}")
        logger.info(f"已修正配置路径: TIME_FILE = {config.Config.TIME_FILE}")
        
    except Exception as e:
        logger.error(f"修补路径时出错: {str(e)}", exc_info=True)

# 确保所有必要的数据目录存在
def ensure_data_directories():
    directories = ['time_data', 'distance_data', 'geo_data']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"确保目录存在: {directory}")
    
    # 检查并创建必要的基本数据文件
    ensure_base_data_files()

# 创建基本数据文件
def ensure_base_data_files():
    # 站点距离数据文件
    station_file = os.path.join('distance_data', 'station.json')
    if not os.path.exists(station_file):
        with open(station_file, 'w', encoding='utf-8') as f:
            json.dump({"stations": []}, f, ensure_ascii=False, indent=2)
        logger.info(f"创建空站点距离文件: {station_file}")
    
    # 时刻表数据文件
    time_file = os.path.join('time_data', 'time.json')
    if not os.path.exists(time_file):
        with open(time_file, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        logger.info(f"创建空时刻表文件: {time_file}")
    
    # 地理数据文件
    geo_point_file = os.path.join('geo_data', 'point.json')
    if not os.path.exists(geo_point_file):
        with open(geo_point_file, 'w', encoding='utf-8') as f:
            json.dump({"type": "FeatureCollection", "features": []}, f, ensure_ascii=False, indent=2)
        logger.info(f"创建空地理点数据文件: {geo_point_file}")
    
    geo_line_file = os.path.join('geo_data', 'line.geojson')
    if not os.path.exists(geo_line_file):
        with open(geo_line_file, 'w', encoding='utf-8') as f:
            json.dump({"type": "FeatureCollection", "features": []}, f, ensure_ascii=False, indent=2)
        logger.info(f"创建空地理线数据文件: {geo_line_file}")

# 导入兼容性模块并应用补丁
import compat
# 应用猴子补丁解决werkzeug.urls问题
compat.apply_werkzeug_patches()

# 设置环境
app_path = setup_app_environment()
logger.info(f"应用程序路径: {app_path}")

# 导入并启动Flask应用
from app import app

if __name__ == "__main__":
    try:
        logger.info("正在启动北京地铁应用...")
        # 启动Flask应用
        app.run(host='127.0.0.1', port=5000)
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}", exc_info=True)
        input("按任意键退出...")
