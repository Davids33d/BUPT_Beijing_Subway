"""
Werkzeug兼容性模块，处理不同版本API变化
通过猴子补丁方式直接修补werkzeug.urls模块，确保url_quote可用
"""

import sys
import importlib

# 检查werkzeug版本并应用相应的补丁
def apply_werkzeug_patches():
    """应用Werkzeug补丁来处理版本差异"""
    try:
        # 尝试导入werkzeug.urls模块
        import werkzeug.urls
        
        # 检查是否已存在url_quote
        if not hasattr(werkzeug.urls, 'url_quote') and hasattr(werkzeug.urls, 'quote'):
            # 新版本中重命名为quote，给模块添加url_quote别名
            werkzeug.urls.url_quote = werkzeug.urls.quote
            print("已为werkzeug.urls添加url_quote兼容函数")
            
    except ImportError:
        print("无法导入werkzeug.urls模块")
        
# 立即应用补丁
apply_werkzeug_patches()

# 以下是原始的兼容性导出，保留向后兼容性
try:
    from werkzeug.urls import url_quote
except ImportError:
    try:
        from werkzeug.urls import quote as url_quote
    except ImportError:
        # 最后的防御措施：提供一个最小实现
        def url_quote(string, charset='utf-8', errors='strict', safe='/:', unsafe=''):
            """简单的URL引用实现，仅作为最后的后备"""
            import urllib.parse
            return urllib.parse.quote(str(string), safe=safe)

# 导出url_quote函数供其他模块使用
__all__ = ['url_quote', 'apply_werkzeug_patches']
