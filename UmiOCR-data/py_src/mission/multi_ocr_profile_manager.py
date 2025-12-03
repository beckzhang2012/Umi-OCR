# ===============================================
# =============== 多引擎方案管理器 ===============
# ===============================================

"""
多引擎方案管理器，用于保存和加载多引擎配置方案。
"""

import os
import json
import shutil
from datetime import datetime
from umi_log import logger


class MultiOCRProfile:
    """多引擎方案数据结构"""
    def __init__(self, name, description=""):
        self.name = name
        self.description = description
        self.engines = []  # [{"key": engine_key, "name": engine_name, "config": config_dict}, ...]
        self.strategy = "confidence"  # 结果合并策略
        self.created_time = datetime.now().isoformat()
        self.updated_time = datetime.now().isoformat()
        self.version = "1.0"

    def add_engine(self, engine_key, engine_name, config=None):
        """添加引擎配置"""
        self.engines.append({
            "key": engine_key,
            "name": engine_name,
            "config": config or {}
        })
        self.updated_time = datetime.now().isoformat()

    def remove_engine(self, engine_key):
        """移除引擎配置"""
        self.engines = [e for e in self.engines if e["key"] != engine_key]
        self.updated_time = datetime.now().isoformat()

    def update_engine_config(self, engine_key, config):
        """更新引擎配置"""
        for engine in self.engines:
            if engine["key"] == engine_key:
                engine["config"] = config
                self.updated_time = datetime.now().isoformat()
                break

    def set_strategy(self, strategy):
        """设置结果合并策略"""
        valid_strategies = ["vote", "confidence", "merge"]
        if strategy in valid_strategies:
            self.strategy = strategy
            self.updated_time = datetime.now().isoformat()
            return True
        return False

    def to_dict(self):
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "engines": self.engines.copy(),
            "strategy": self.strategy,
            "created_time": self.created_time,
            "updated_time": self.updated_time,
            "version": self.version
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建方案对象"""
        profile = cls(data.get("name", ""), data.get("description", ""))
        profile.engines = data.get("engines", [])
        profile.strategy = data.get("strategy", "confidence")
        profile.created_time = data.get("created_time", datetime.now().isoformat())
        profile.updated_time = data.get("updated_time", datetime.now().isoformat())
        profile.version = data.get("version", "1.0")
        return profile


class MultiOCRProfileManager:
    """多引擎方案管理器"""
    def __init__(self, profiles_dir=None):
        if profiles_dir is None:
            from ..utils.path_manager import PathManager
            self.profiles_dir = os.path.join(PathManager.get_config_dir(), "multi_ocr_profiles")
        else:
            self.profiles_dir = profiles_dir
        
        self._ensure_dir_exists()
        self._profiles = {}  # {profile_name: MultiOCRProfile}
        self._load_profiles()

    def _ensure_dir_exists(self):
        """确保方案目录存在"""
        try:
            os.makedirs(self.profiles_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建多引擎方案目录失败: {e}", exc_info=True)
            raise

    def _load_profiles(self):
        """加载所有方案"""
        try:
            if not os.path.exists(self.profiles_dir):
                return
            
            for filename in os.listdir(self.profiles_dir):
                if filename.endswith(".json"):
                    profile_path = os.path.join(self.profiles_dir, filename)
                    try:
                        with open(profile_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            profile = MultiOCRProfile.from_dict(data)
                            self._profiles[profile.name] = profile
                    except Exception as e:
                        logger.error(f"加载多引擎方案失败 {filename}: {e}", exc_info=True)
        
        except Exception as e:
            logger.error("加载多引擎方案失败", exc_info=True)

    def save_profile(self, profile):
        """保存方案到文件"""
        if not isinstance(profile, MultiOCRProfile):
            raise TypeError("profile 必须是 MultiOCRProfile 类型")
        
        try:
            filename = f"{profile.name.replace(' ', '_')}.json"
            profile_path = os.path.join(self.profiles_dir, filename)
            
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
            
            self._profiles[profile.name] = profile
            logger.info(f"多引擎方案已保存: {profile.name}")
            return True
        
        except Exception as e:
            logger.error(f"保存多引擎方案失败 {profile.name}: {e}", exc_info=True)
            return False

    def load_profile(self, profile_name):
        """加载方案"""
        return self._profiles.get(profile_name)

    def delete_profile(self, profile_name):
        """删除方案"""
        if profile_name not in self._profiles:
            return False
        
        try:
            filename = f"{profile_name.replace(' ', '_')}.json"
            profile_path = os.path.join(self.profiles_dir, filename)
            
            if os.path.exists(profile_path):
                os.remove(profile_path)
            
            del self._profiles[profile_name]
            logger.info(f"多引擎方案已删除: {profile_name}")
            return True
        
        except Exception as e:
            logger.error(f"删除多引擎方案失败 {profile_name}: {e}", exc_info=True)
            return False

    def get_all_profiles(self):
        """获取所有方案列表"""
        return list(self._profiles.values())

    def get_profile_names(self):
        """获取所有方案名称"""
        return sorted(self._profiles.keys())

    def duplicate_profile(self, original_name, new_name, new_description=""):
        """复制方案"""
        original_profile = self._profiles.get(original_name)
        if not original_profile:
            return False
        
        try:
            new_profile = MultiOCRProfile(new_name, new_description or original_profile.description)
            new_profile.engines = original_profile.engines.copy()
            new_profile.strategy = original_profile.strategy
            
            return self.save_profile(new_profile)
        
        except Exception as e:
            logger.error(f"复制多引擎方案失败 {original_name} -> {new_name}: {e}", exc_info=True)
            return False

    def export_profile(self, profile_name, export_path):
        """导出方案"""
        profile = self._profiles.get(profile_name)
        if not profile:
            return False
        
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"多引擎方案已导出: {profile_name} -> {export_path}")
            return True
        
        except Exception as e:
            logger.error(f"导出多引擎方案失败 {profile_name}: {e}", exc_info=True)
            return False

    def import_profile(self, import_path):
        """导入方案"""
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            profile = MultiOCRProfile.from_dict(data)
            
            # 检查方案名称是否已存在
            if profile.name in self._profiles:
                # 生成新名称
                base_name = profile.name
                counter = 1
                while f"{base_name}_{counter}" in self._profiles:
                    counter += 1
                profile.name = f"{base_name}_{counter}"
            
            return self.save_profile(profile)
        
        except Exception as e:
            logger.error(f"导入多引擎方案失败 {import_path}: {e}", exc_info=True)
            return False

    def create_default_profiles(self):
        """创建默认方案"""
        # 创建一个包含常用引擎的默认方案
        default_profile = MultiOCRProfile(
            name="默认三引擎方案",
            description="包含常用OCR引擎的默认方案，用于快速对比识别效果"
        )
        
        # 添加默认引擎配置（这些是示例，实际需要根据可用引擎调整）
        default_profile.add_engine(
            engine_key="PaddleOCR",
            engine_name="PaddleOCR",
            config={
                "lang": "ch",
                "det": True,
                "rec": True,
                "cls": True
            }
        )
        
        default_profile.add_engine(
            engine_key="Tesseract",
            engine_name="Tesseract OCR",
            config={
                "lang": "chi_sim",
                "psm": 6
            }
        )
        
        default_profile.add_engine(
            engine_key="BaiduOCR",
            engine_name="百度OCR",
            config={
                "api_key": "",
                "secret_key": "",
                "lang": "CHN_ENG"
            }
        )
        
        default_profile.set_strategy("confidence")
        
        if self.save_profile(default_profile):
            logger.info("默认多引擎方案已创建")
            return True
        
        return False

    def get_profiles_info(self):
        """获取方案信息列表"""
        profiles_info = []
        for profile in self._profiles.values():
            profiles_info.append({
                "name": profile.name,
                "description": profile.description,
                "engine_count": len(profile.engines),
                "strategy": profile.strategy,
                "created_time": profile.created_time,
                "updated_time": profile.updated_time,
                "version": profile.version
            })
        
        # 按更新时间排序
        return sorted(profiles_info, key=lambda x: x["updated_time"], reverse=True)


# 全局多引擎方案管理器
MultiOCRProfileManagerInstance = MultiOCRProfileManager()
