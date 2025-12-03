# =======================================
# =============== 路径管理 ===============
# =======================================

import os


class PathManager:
    """路径管理器"""
    @staticmethod
    def get_config_dir():
        """获取配置目录路径"""
        # 配置目录位于UmiOCR-data目录下的config文件夹
        return os.path.abspath("./config")
