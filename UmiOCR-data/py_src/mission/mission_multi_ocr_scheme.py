# ===============================================
# 多引擎OCR方案保存/加载模块
# 支持保存为JSON文件，包含引擎配置和参数
# ===============================================

import json
import os
from typing import Dict, List, Optional

# 方案配置类
class MultiOcrScheme:
    def __init__(self):
        self.name: str = ""  # 方案名称
        self.description: str = ""  # 方案描述
        self.engine_names: List[str] = []  # 引擎名称列表
        self.engine_configs: Dict[str, Dict] = {}  # 引擎配置
        self.common_config: Dict = {}  # 通用配置
        self.create_time: str = ""  # 创建时间
        self.update_time: str = ""  # 更新时间

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "engine_names": self.engine_names,
            "engine_configs": self.engine_configs,
            "common_config": self.common_config,
            "create_time": self.create_time,
            "update_time": self.update_time
        }

    def from_dict(self, data: Dict):
        """从字典加载"""
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.engine_names = data.get("engine_names", [])
        self.engine_configs = data.get("engine_configs", {})
        self.common_config = data.get("common_config", {})
        self.create_time = data.get("create_time", "")
        self.update_time = data.get("update_time", "")

# 方案管理器类
class __MultiOcrSchemeManagerClass:
    def __init__(self):
        self.schemes: Dict[str, MultiOcrScheme] = {}  # 方案字典
        self.scheme_dir: str = ""  # 方案保存目录
        self.current_scheme: Optional[MultiOcrScheme] = None  # 当前方案

    def init(self, scheme_dir: str):
        """初始化方案管理器"""
        self.scheme_dir = scheme_dir
        if not os.path.exists(scheme_dir):
            os.makedirs(scheme_dir)
        self.load_all_schemes()

    def create_scheme(self, name: str, description: str = "") -> MultiOcrScheme:
        """创建新方案"""
        scheme = MultiOcrScheme()
        scheme.name = name
        scheme.description = description
        scheme.create_time = self._get_current_time()
        scheme.update_time = scheme.create_time
        return scheme

    def save_scheme(self, scheme: MultiOcrScheme, filename: Optional[str] = None) -> bool:
        """保存方案到文件"""
        try:
            if not filename:
                filename = self._get_scheme_filename(scheme.name)

            # 更新时间
            scheme.update_time = self._get_current_time()

            # 转换为字典
            data = scheme.to_dict()

            # 保存到文件
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 添加到方案列表
            self.schemes[scheme.name] = scheme
            return True
        except Exception as e:
            print(f"保存方案失败: {e}")
            return False

    def load_scheme(self, filename: str) -> Optional[MultiOcrScheme]:
        """从文件加载方案"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            scheme = MultiOcrScheme()
            scheme.from_dict(data)
            return scheme
        except Exception as e:
            print(f"加载方案失败: {e}")
            return None

    def load_scheme_by_name(self, name: str) -> Optional[MultiOcrScheme]:
        """按名称加载方案"""
        if name in self.schemes:
            return self.schemes[name]

        filename = self._get_scheme_filename(name)
        if os.path.exists(filename):
            scheme = self.load_scheme(filename)
            if scheme:
                self.schemes[name] = scheme
                return scheme

        return None

    def delete_scheme(self, name: str) -> bool:
        """删除方案"""
        try:
            filename = self._get_scheme_filename(name)
            if os.path.exists(filename):
                os.remove(filename)

            if name in self.schemes:
                del self.schemes[name]

            return True
        except Exception as e:
            print(f"删除方案失败: {e}")
            return False

    def get_scheme_list(self) -> List[str]:
        """获取方案名称列表"""
        return list(self.schemes.keys())

    def export_scheme(self, scheme: MultiOcrScheme, filename: str) -> bool:
        """导出方案到指定文件"""
        return self.save_scheme(scheme, filename)

    def import_scheme(self, filename: str) -> Optional[MultiOcrScheme]:
        """从指定文件导入方案"""
        scheme = self.load_scheme(filename)
        if scheme:
            # 保存到方案目录
            save_filename = self._get_scheme_filename(scheme.name)
            self.save_scheme(scheme, save_filename)
            return scheme
        return None

    def load_all_schemes(self):
        """加载所有方案"""
        if not self.scheme_dir or not os.path.exists(self.scheme_dir):
            return

        for filename in os.listdir(self.scheme_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.scheme_dir, filename)
                scheme = self.load_scheme(filepath)
                if scheme:
                    self.schemes[scheme.name] = scheme

    def _get_scheme_filename(self, name: str) -> str:
        """获取方案文件名"""
        # 替换非法字符
        safe_name = name.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
        return os.path.join(self.scheme_dir, f"{safe_name}.json")

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 全局实例
MultiOcrSchemeManager = __MultiOcrSchemeManagerClass()

# QML接口函数
def init_scheme_manager(scheme_dir: str):
    """初始化方案管理器"""
    MultiOcrSchemeManager.init(scheme_dir)

def create_scheme(name: str, description: str = "") -> Dict:
    """创建新方案"""
    scheme = MultiOcrSchemeManager.create_scheme(name, description)
    return scheme.to_dict()

def save_scheme(data: Dict) -> bool:
    """保存方案"""
    scheme = MultiOcrScheme()
    scheme.from_dict(data)
    return MultiOcrSchemeManager.save_scheme(scheme)

def load_scheme(name: str) -> Optional[Dict]:
    """加载方案"""
    scheme = MultiOcrSchemeManager.load_scheme_by_name(name)
    if scheme:
        return scheme.to_dict()
    return None

def delete_scheme(name: str) -> bool:
    """删除方案"""
    return MultiOcrSchemeManager.delete_scheme(name)

def get_scheme_list() -> List[str]:
    """获取方案列表"""
    return MultiOcrSchemeManager.get_scheme_list()

def export_scheme(name: str, filename: str) -> bool:
    """导出方案"""
    scheme = MultiOcrSchemeManager.load_scheme_by_name(name)
    if scheme:
        return MultiOcrSchemeManager.export_scheme(scheme, filename)
    return False

def import_scheme(filename: str) -> Optional[Dict]:
    """导入方案"""
    scheme = MultiOcrSchemeManager.import_scheme(filename)
    if scheme:
        return scheme.to_dict()
    return None