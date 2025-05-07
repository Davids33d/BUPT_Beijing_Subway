"""
打包脚本 - 将应用程序打包为可执行文件
使用方法: python build.py [--no-console]
"""
import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

def main():
    """主打包函数"""
    parser = argparse.ArgumentParser(description='打包北京地铁站点管理系统')
    parser.add_argument('--no-console', action='store_true', help='创建无控制台窗口的应用程序')
    args = parser.parse_args()
    
    print("开始打包北京地铁站点管理系统...")
    
    # 获取项目根目录
    project_root = Path(__file__).parent.absolute()
    print(f"项目根目录: {project_root}")
    
    # 确保目录路径正确
    os.chdir(project_root)
    
    # 清理旧的构建文件
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    
    if dist_dir.exists():
        print("清理旧的dist目录...")
        shutil.rmtree(dist_dir)
    
    if build_dir.exists():
        print("清理旧的build目录...")
        shutil.rmtree(build_dir)
        
    # 定义PyInstaller参数
    entry_script = "run_app.py"
    icon_path = os.path.join(project_root, "static", "favicon.ico")
    app_name = "BeijingSubway"
    
    # 准备数据文件
    data_files = [
        ("static", "static"),
        ("templates", "templates"),
        ("geo_data", "geo_data"),
        ("distance_data", "distance_data"),
        ("time_data", "time_data"),
        ("config.py", "."),
        (".env", ".")
    ]
    
    data_args = []
    for src, dest in data_files:
        data_args.extend(["--add-data", f"{src}{os.pathsep}{dest}"])
    
    # 构建PyInstaller命令
    cmd = [
        "pyinstaller",
        "--name", app_name,
        "--onefile",  # 打包成单个文件
        "--icon", icon_path,
        "--clean",    # 清理PyInstaller缓存
        "--distpath", ".",  # 将EXE输出到当前目录而非dist子目录
    ]
    
    # 添加控制台窗口选项
    if args.no_console:
        cmd.append("--noconsole")  # 不显示控制台窗口
    else:
        cmd.append("--console")    # 显示控制台窗口
    
    # 添加数据文件
    cmd.extend(data_args)
    
    # 精确指定必要的隐藏导入库，避免自动分析引入过多依赖
    essential_packages = [
        "flask", 
        "werkzeug.middleware.proxy_fix",
        "networkx",
        "geojson",
        "python_dotenv",
    ]
    
    for pkg in essential_packages:
        cmd.extend(["--hidden-import", pkg])
    
    # 排除不需要的大型库，减小打包体积
    exclude_modules = [
        "matplotlib", "scipy", "PyQt5", "tkinter", 
        "PIL", "opencv", "sphinx", "alabaster"
    ]
    
    for mod in exclude_modules:
        cmd.extend(["--exclude-module", mod])
    
    # 确保Flask相关模块完整包含
    cmd.extend(["--collect-submodules", "flask"])
    
    # 添加入口脚本
    cmd.append(entry_script)
    
    # 执行打包命令
    print("执行PyInstaller打包命令...")
    print(f"命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("\n打包成功！")
        # 修改EXE路径，现在EXE直接在项目根目录下
        exe_path = os.path.join(project_root, f"{app_name}.exe")
        print(f"可执行文件位置: {exe_path}")
        
        if os.path.exists(exe_path):
            print(f"文件大小: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")
        else:
            print(f"警告: 可执行文件 {exe_path} 未找到。请检查输出路径。")
    except subprocess.CalledProcessError as e:
        print(f"打包失败，错误码: {e.returncode}")
        print(f"错误输出: {e.stderr}")
        return 1
    
    # 检测并使用当前活跃的Python环境
    try:
        # 获取当前Python解释器路径
        current_python = sys.executable
        print(f"\n使用当前Python环境: {current_python}")
        
        # 获取环境中的site-packages路径
        import site
        env_paths = site.getsitepackages()
        if env_paths:
            print(f"环境库路径: {env_paths[0]}")
            
            # 检查是否存在兼容性文件
            compat_file = os.path.join(project_root, "compat.py")
            if not os.path.exists(compat_file):
                print("\n创建Werkzeug兼容性模块...")
                with open(compat_file, "w", encoding="utf-8") as f:
                    f.write('"""Werkzeug兼容性模块，处理不同版本API变化"""\n\n')
                    f.write('# 处理url_quote在不同Werkzeug版本中的名称变化\n')
                    f.write('try:\n')
                    f.write('    from werkzeug.urls import url_quote\n')
                    f.write('except ImportError:\n')
                    f.write('    # 在新版本中，url_quote被重命名为quote\n')
                    f.write('    from werkzeug.urls import quote as url_quote\n\n')
                    f.write("# 导出url_quote函数供其他模块使用\n")
                    f.write("__all__ = ['url_quote']\n")
                print("已创建compat.py兼容性模块，用于解决Werkzeug版本差异问题")
                
                # 将compat.py添加到数据文件
                data_files.append(("compat.py", "."))
                data_args.extend(["--add-data", f"compat.py{os.pathsep}."])
                
            # 添加环境提示
            if "envs" in current_python.lower() or "venv" in current_python.lower():
                print("\n使用虚拟环境打包，有助于减小最终文件大小")
            
            # 添加werkzeug兼容性警告
            print("\n警告: 检测到可能的werkzeug版本兼容性问题")
            print("建议使用以下方法解决:")
            print("1. 确保安装werkzeug 2.0.0以下版本: pip install werkzeug==1.0.1")
            print("2. 或者使用新版本并更新依赖代码中的url_quote引用")
            
            # 添加环境提示
            if "envs" in current_python.lower() or "venv" in current_python.lower():
                print("\n使用虚拟环境打包，有助于减小最终文件大小")
                
                # 提取虚拟环境名称
                env_name = os.path.basename(os.path.dirname(current_python))
                if "Scripts" in current_python:
                    env_name = os.path.basename(os.path.dirname(os.path.dirname(current_python)))
                
                print(f"当前虚拟环境: {env_name}")
                print(f"Python路径: {current_python}")
            else:
                print("\n警告: 似乎没有使用虚拟环境，可能会包含不必要的库")
                print("建议创建并激活专用虚拟环境后再打包:")
                print("1. conda create -n subway_env python=3.9")
                print("2. conda activate subway_env")
                print("3. pip install flask werkzeug networkx geojson python-dotenv pyinstaller")
                print("4. python build.py")
    except Exception as e:
        print(f"获取环境信息失败: {e}")
    
    print("\n使用说明:")
    print(f"1. 直接双击 {app_name}.exe 运行应用")
    print("2. 应用将在 http://127.0.0.1:5000 启动")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
