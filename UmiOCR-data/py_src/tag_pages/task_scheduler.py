# ===============================================
# =============== 任务排程页面控制器 ===============
# ===============================================

from PySide6.QtCore import Slot, QObject, Property
from typing import List, Dict, Optional

from ..scheduler.scheduler import Scheduler
from umi_log import logger


class TaskSchedulerController(QObject):
    """任务排程页面控制器"""
    def __init__(self):
        super().__init__()
        self._qml_obj = None
        self._scheduler = Scheduler

    def setQmlObj(self, qml_obj):
        """设置QML对象"""
        self._qml_obj = qml_obj

    # ========================= 【QML调用接口】 =========================

    @Slot(result='QVariantList')
    def getTasks(self) -> List[Dict]:
        """获取所有任务"""
        try:
            return self._scheduler.get_tasks()
        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            return []

    @Slot(str, result='QVariant')
    def getTask(self, task_id: str) -> Optional[Dict]:
        """获取单个任务"""
        try:
            return self._scheduler.get_task(task_id)
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    @Slot('QVariant', result=str)
    def addTask(self, task_data: Dict) -> str:
        """添加任务"""
        try:
            return self._scheduler.add_task(task_data)
        except Exception as e:
            logger.error(f"Failed to add task: {e}")
            return ""

    @Slot(str, 'QVariant', result=bool)
    def updateTask(self, task_id: str, task_data: Dict) -> bool:
        """更新任务"""
        try:
            return self._scheduler.update_task(task_id, task_data)
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return False

    @Slot(str, result=bool)
    def deleteTask(self, task_id: str) -> bool:
        """删除任务"""
        try:
            return self._scheduler.delete_task(task_id)
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            return False

    @Slot(str, result=bool)
    def toggleTask(self, task_id: str) -> bool:
        """切换任务启用状态"""
        try:
            return self._scheduler.toggle_task(task_id)
        except Exception as e:
            logger.error(f"Failed to toggle task {task_id}: {e}")
            return False

    @Slot(str, result='QVariantList')
    def getExecutionLogs(self, task_id: str = None) -> List[Dict]:
        """获取执行日志"""
        try:
            return self._scheduler.get_execution_logs(task_id)
        except Exception as e:
            logger.error(f"Failed to get execution logs: {e}")
            return []

    @Slot(str, result=bool)
    def exportLogs(self, file_path: str) -> bool:
        """导出日志到JSON文件"""
        try:
            return self._scheduler.export_logs(file_path)
        except Exception as e:
            logger.error(f"Failed to export logs: {e}")
            return False

    @Slot(str, result=bool)
    def executeTaskNow(self, task_id: str) -> bool:
        """立即执行任务"""
        try:
            # 这里需要实现立即执行任务的逻辑
            # 暂时返回True，实际需要调用调度器的执行方法
            logger.info(f"Executing task now: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to execute task now {task_id}: {e}")
            return False

    # ========================= 【属性】 =========================

    @Property(bool, notify=False)
    def schedulerRunning(self) -> bool:
        """调度器是否运行"""
        return self._scheduler._running

    @Property(int, notify=False)
    def taskCount(self) -> int:
        """任务数量"""
        return len(self._scheduler.get_tasks())

    @Property(int, notify=False)
    def logCount(self) -> int:
        """日志数量"""
        return len(self._scheduler.get_execution_logs())


# 控制器工厂函数
def create_controller() -> TaskSchedulerController:
    """创建任务排程页面控制器"""
    return TaskSchedulerController()