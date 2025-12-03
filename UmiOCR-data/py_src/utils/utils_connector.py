# 通用工具连接器

from typing import List
from PySide6.QtCore import QObject, Slot

from . import utils
from . import file_finder  # 文件搜索器
from . import mission_multi_ocr_scheme  # 多引擎方案管理
from ..platform import Platform  # 跨平台
from .thread_pool import threadRun  # 异步执行函数


class UtilsConnector(QObject):
    def __init__(self):
        super().__init__()

    # 将文本写入剪贴板
    @Slot(str)
    def copyText(self, text):
        utils.copyText(text)

    # 用系统应用打开文件或目录
    @Slot(str)
    def startfile(self, path):
        Platform.startfile(path)

    # 硬件控制
    @Slot(str)
    def hardwareCtrl(self, key):
        if key == "shutdown":  # 关机
            Platform.HardwareCtrl.shutdown()
        elif key == "hibernate":  # 休眠
            Platform.HardwareCtrl.hibernate()

    # 同步搜索文件，返回合法的文件路径列表
    @Slot("QVariant", bool, str, result="QVariant")
    def findFiles(self, paths, sufType, isRecurrence):
        return file_finder.findFiles(paths, sufType, isRecurrence)

    # 异步搜索文件
    @Slot("QVariant", str, bool, str, str, float)
    def asynFindFiles(
        self,
        paths: List,  # 初始路径列表
        sufType: str,  # 后缀类型，FileSuf的key
        isRecurrence: bool,  # 若为True，则递归搜索
        completeKey: str,  # 全部完成后的事件key。向事件传入合法路径列表。
        updateKey: str,  # 加载中刷新进度的key，不填则无。向事件传入 (已完成的路径数量, 最近一条路径)
        updateTime: float,  # 刷新进度的间距
    ):
        threadRun(
            file_finder.asynFindFiles,
            paths,
            sufType,
            isRecurrence,
            completeKey,
            updateKey,
            updateTime,
        )

    # QUrl列表 转 String列表
    @Slot("QVariant", result="QVariant")
    def QUrl2String(self, fileUrls):
        return utils.QUrl2String(fileUrls)

    # 多引擎方案管理接口
    @Slot()
    def init_scheme_manager(self):
        mission_multi_ocr_scheme.init_scheme_manager()

    @Slot(str, str, str, str, result=str)
    def create_scheme(self, name, engine1, engine2, strategy):
        return mission_multi_ocr_scheme.create_scheme(name, engine1, engine2, strategy)

    @Slot(str, str, str, str, str)
    def save_scheme(self, scheme_id, name, engine1, engine2, strategy):
        mission_multi_ocr_scheme.save_scheme(scheme_id, name, engine1, engine2, strategy)

    @Slot(str, result="QVariant")
    def load_scheme(self, scheme_id):
        return mission_multi_ocr_scheme.load_scheme(scheme_id)

    @Slot(str)
    def delete_scheme(self, scheme_id):
        mission_multi_ocr_scheme.delete_scheme(scheme_id)

    @Slot(result="QVariant")
    def list_schemes(self):
        return mission_multi_ocr_scheme.list_schemes()

    @Slot(str, str)
    def export_scheme(self, scheme_id, file_path):
        mission_multi_ocr_scheme.export_scheme(scheme_id, file_path)

    @Slot(str, result=str)
    def import_scheme(self, file_path):
        return mission_multi_ocr_scheme.import_scheme(file_path)
