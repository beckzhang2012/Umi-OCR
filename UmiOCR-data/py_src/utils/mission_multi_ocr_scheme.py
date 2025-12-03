# 多引擎方案管理

import os
import json
import uuid
from datetime import datetime
from PySide6.QtCore import QObject, Slot
from umi_log import logger


class MultiOcrScheme:
    """多引擎OCR方案"""
    def __init__(self, scheme_id, name, engine1, engine2, strategy):
        self.id = scheme_id
        self.name = name
        self.engine1 = engine1
        self.engine2 = engine2
        self.strategy = strategy
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'engine1': self.engine1,
            'engine2': self.engine2,
            'strategy': self.strategy,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(data):
        """从字典创建"""
        scheme = MultiOcrScheme(
            data['id'],
            data['name'],
            data['engine1'],
            data['engine2'],
            data['strategy']
        )
        scheme.created_at = data.get('created_at', datetime.now().isoformat())
        scheme.updated_at = data.get('updated_at', datetime.now().isoformat())
        return scheme


class __MultiOcrSchemeManagerClass:
    """多引擎OCR方案管理器"""
    def __init__(self):
        self.schemes_dir = os.path.join(os.path.dirname(__file__), 'schemes')
        os.makedirs(self.schemes_dir, exist_ok=True)
        self.schemes = self._load_all_schemes()

    def _load_all_schemes(self):
        """加载所有方案"""
        schemes = {}
        for filename in os.listdir(self.schemes_dir):
            if filename.endswith('.json'):
                scheme_id = filename[:-5]
                scheme_path = os.path.join(self.schemes_dir, filename)
                try:
                    with open(scheme_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    schemes[scheme_id] = MultiOcrScheme.from_dict(data)
                except Exception as e:
                    logger.error(f"加载方案失败: {scheme_id} - {e}")
        return schemes

    def create_scheme(self, name, engine1, engine2, strategy):
        """创建新方案"""
        scheme_id = str(uuid.uuid4())
        scheme = MultiOcrScheme(scheme_id, name, engine1, engine2, strategy)
        self.schemes[scheme_id] = scheme
        self._save_scheme(scheme)
        return scheme_id

    def save_scheme(self, scheme_id, name, engine1, engine2, strategy):
        """保存方案"""
        if scheme_id in self.schemes:
            scheme = self.schemes[scheme_id]
            scheme.name = name
            scheme.engine1 = engine1
            scheme.engine2 = engine2
            scheme.strategy = strategy
            scheme.updated_at = datetime.now().isoformat()
            self._save_scheme(scheme)
        else:
            logger.error(f"方案不存在: {scheme_id}")

    def _save_scheme(self, scheme):
        """保存方案到文件"""
        scheme_path = os.path.join(self.schemes_dir, f'{scheme.id}.json')
        try:
            with open(scheme_path, 'w', encoding='utf-8') as f:
                json.dump(scheme.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存方案失败: {scheme.id} - {e}")

    def load_scheme(self, scheme_id):
        """加载方案"""
        if scheme_id in self.schemes:
            return self.schemes[scheme_id].to_dict()
        else:
            logger.error(f"方案不存在: {scheme_id}")
            return None

    def delete_scheme(self, scheme_id):
        """删除方案"""
        if scheme_id in self.schemes:
            del self.schemes[scheme_id]
            scheme_path = os.path.join(self.schemes_dir, f'{scheme_id}.json')
            if os.path.exists(scheme_path):
                os.remove(scheme_path)
        else:
            logger.error(f"方案不存在: {scheme_id}")

    def list_schemes(self):
        """列出所有方案"""
        return [scheme.to_dict() for scheme in self.schemes.values()]

    def export_scheme(self, scheme_id, file_path):
        """导出方案"""
        if scheme_id in self.schemes:
            scheme = self.schemes[scheme_id]
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(scheme.to_dict(), f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"导出方案失败: {scheme_id} - {e}")
        else:
            logger.error(f"方案不存在: {scheme_id}")

    def import_scheme(self, file_path):
        """导入方案"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                scheme_data = json.load(f)
            scheme_id = str(uuid.uuid4())
            scheme_data['id'] = scheme_id
            scheme_data['created_at'] = datetime.now().isoformat()
            scheme_data['updated_at'] = datetime.now().isoformat()
            scheme = MultiOcrScheme.from_dict(scheme_data)
            self.schemes[scheme_id] = scheme
            self._save_scheme(scheme)
            return scheme_id
        except Exception as e:
            logger.error(f"导入方案失败: {e}")
            return None


# 全局方案管理器实例
_scheme_manager = None


def init_scheme_manager():
    """初始化方案管理器"""
    global _scheme_manager
    if _scheme_manager is None:
        _scheme_manager = __MultiOcrSchemeManagerClass()


def create_scheme(name, engine1, engine2, strategy):
    """创建新方案"""
    if _scheme_manager is None:
        init_scheme_manager()
    return _scheme_manager.create_scheme(name, engine1, engine2, strategy)


def save_scheme(scheme_id, name, engine1, engine2, strategy):
    """保存方案"""
    if _scheme_manager is None:
        init_scheme_manager()
    _scheme_manager.save_scheme(scheme_id, name, engine1, engine2, strategy)


def load_scheme(scheme_id):
    """加载方案"""
    if _scheme_manager is None:
        init_scheme_manager()
    return _scheme_manager.load_scheme(scheme_id)


def delete_scheme(scheme_id):
    """删除方案"""
    if _scheme_manager is None:
        init_scheme_manager()
    _scheme_manager.delete_scheme(scheme_id)


def list_schemes():
    """列出所有方案"""
    if _scheme_manager is None:
        init_scheme_manager()
    return _scheme_manager.list_schemes()


def export_scheme(scheme_id, file_path):
    """导出方案"""
    if _scheme_manager is None:
        init_scheme_manager()
    _scheme_manager.export_scheme(scheme_id, file_path)


def import_scheme(file_path):
    """导入方案"""
    if _scheme_manager is None:
        init_scheme_manager()
    return _scheme_manager.import_scheme(file_path)


class SchemeManagerConnector(QObject):
    """多引擎方案管理连接器，用于QML调用"""
    def __init__(self):
        super().__init__()
        init_scheme_manager()

    @Slot()
    def init(self):
        """初始化方案管理器"""
        init_scheme_manager()

    @Slot(str, str, str, str, result=str)
    def createScheme(self, name, engine1, engine2, strategy):
        """创建新方案"""
        return create_scheme(name, engine1, engine2, strategy)

    @Slot(str, str, str, str, str)
    def saveScheme(self, scheme_id, name, engine1, engine2, strategy):
        """保存方案"""
        save_scheme(scheme_id, name, engine1, engine2, strategy)

    @Slot(str, result="QVariant")
    def loadScheme(self, scheme_id):
        """加载方案"""
        return load_scheme(scheme_id)

    @Slot(str)
    def deleteScheme(self, scheme_id):
        """删除方案"""
        delete_scheme(scheme_id)

    @Slot(result="QVariant")
    def listSchemes(self):
        """列出所有方案"""
        return list_schemes()

    @Slot(str, str)
    def exportScheme(self, scheme_id, file_path):
        """导出方案"""
        export_scheme(scheme_id, file_path)

    @Slot(str, result=str)
    def importScheme(self, file_path):
        """导入方案"""
        return import_scheme(file_path)
