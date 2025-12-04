from PySide2.QtCore import QObject, Slot, Property, Signal
from ..directory_monitor import DirectoryMonitorInstance
import logging

logger = logging.getLogger(__name__)

class DirectoryMonitorController(QObject):
    """目录监控页面控制器"""
    
    # 信号
    monitorItemsChanged = Signal()
    fileTasksChanged = Signal()
    taskStatsChanged = Signal()
    alertTriggered = Signal(str, str)
    
    def __init__(self):
        super().__init__()
        self._directory_monitor = DirectoryMonitorInstance
        
        # 连接信号
        self._directory_monitor.monitorItemAdded.connect(self._on_monitor_item_changed)
        self._directory_monitor.monitorItemUpdated.connect(self._on_monitor_item_changed)
        self._directory_monitor.monitorItemDeleted.connect(self._on_monitor_item_changed)
        self._directory_monitor.fileTaskAdded.connect(self._on_file_task_changed)
        self._directory_monitor.fileTaskUpdated.connect(self._on_file_task_changed)
        self._directory_monitor.fileTaskDeleted.connect(self._on_file_task_changed)
        self._directory_monitor.alertTriggered.connect(self.alertTriggered.emit)
        
        # 初始化统计信息
        self._task_stats = self._directory_monitor.get_task_stats()

    @Property(bool, notify=monitorItemsChanged)
    def is_running(self) -> bool:
        """监控器是否正在运行"""
        return self._directory_monitor._running

    @Property('QVariant', notify=taskStatsChanged)
    def task_stats(self) -> dict:
        """任务统计信息"""
        return self._task_stats

    @Slot()
    def start_monitor(self):
        """启动目录监控"""
        self._directory_monitor.start()
        self.monitorItemsChanged.emit()

    @Slot()
    def stop_monitor(self):
        """停止目录监控"""
        self._directory_monitor.stop()
        self.monitorItemsChanged.emit()

    # ========================= 【监控项管理接口】 =========================

    @Slot(result='QVariantList')
    def get_monitor_items(self) -> list:
        """获取所有监控项"""
        return self._directory_monitor.get_monitor_items()

    @Slot(str, result='QVariant')
    def get_monitor_item(self, item_id: str) -> dict:
        """获取单个监控项"""
        return self._directory_monitor.get_monitor_item(item_id)

    @Slot('QVariant', result=str)
    def add_monitor_item(self, item_data: dict) -> str:
        """添加监控项"""
        return self._directory_monitor.add_monitor_item(item_data)

    @Slot(str, 'QVariant', result=bool)
    def update_monitor_item(self, item_id: str, item_data: dict) -> bool:
        """更新监控项"""
        return self._directory_monitor.update_monitor_item(item_id, item_data)

    @Slot(str, result=bool)
    def delete_monitor_item(self, item_id: str) -> bool:
        """删除监控项"""
        return self._directory_monitor.delete_monitor_item(item_id)

    @Slot(str, result=bool)
    def toggle_monitor_item(self, item_id: str) -> bool:
        """切换监控项启用状态"""
        return self._directory_monitor.toggle_monitor_item(item_id)

    # ========================= 【任务管理接口】 =========================

    @Slot(result='QVariantList')
    def get_file_tasks(self) -> list:
        """获取所有文件任务"""
        return self._directory_monitor.get_file_tasks()

    @Slot(str, result='QVariant')
    def get_file_task(self, task_id: str) -> dict:
        """获取单个文件任务"""
        return self._directory_monitor.get_file_task(task_id)

    @Slot(str, result=bool)
    def retry_file_task(self, task_id: str) -> bool:
        """重试文件任务"""
        return self._directory_monitor.retry_file_task(task_id)

    @Slot(str, result=bool)
    def skip_file_task(self, task_id: str) -> bool:
        """跳过文件任务"""
        return self._directory_monitor.skip_file_task(task_id)

    @Slot(str, result=bool)
    def delete_file_task(self, task_id: str) -> bool:
        """删除文件任务"""
        return self._directory_monitor.delete_file_task(task_id)

    @Slot(result='QVariant')
    def refresh_task_stats(self) -> dict:
        """刷新任务统计信息"""
        self._task_stats = self._directory_monitor.get_task_stats()
        self.taskStatsChanged.emit()
        return self._task_stats

    # ========================= 【私有方法】 =========================

    def _on_monitor_item_changed(self, *args):
        """监控项变化时触发"""
        self.monitorItemsChanged.emit()

    def _on_file_task_changed(self, *args):
        """文件任务变化时触发"""
        self.fileTasksChanged.emit()
        self.refresh_task_stats()

# 控制器工厂函数
def create_controller() -> DirectoryMonitorController:
    """创建目录监控页面控制器"""
    return DirectoryMonitorController()