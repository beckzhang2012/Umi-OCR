# ==============================================
# =============== 任务上下文快照 ===============
# ==============================================

"""
任务上下文快照模块，用于保存和恢复任务的关键信息，防止线程共享状态被意外清除导致的崩溃。
"""

import os
import time
import json
from umi_log import logger

class MissionSnapshot:
    """任务上下文快照类"""
    
    def __init__(self, msnID, msnInfo, msnList, apiKey=None, apiInfo=None):
        """
        初始化任务快照
        
        Args:
            msnID (str): 任务ID
            msnInfo (dict): 任务信息字典
            msnList (list): 任务队列列表
            apiKey (str, optional): API类型
            apiInfo (object, optional): API对象
        """
        self.msnID = msnID
        self.msnInfo = msnInfo.copy()  # 深拷贝防止外部修改
        self.msnList = [task.copy() for task in msnList]  # 深拷贝任务队列
        self.apiKey = apiKey
        self.apiInfo = apiInfo
        self.createdTime = time.time()
        self.lastUpdatedTime = time.time()
        self.completedTasks = []  # 已完成的任务列表
        self.failedTasks = []  # 失败的任务列表
        self.currentTaskIndex = 0  # 当前执行的任务索引
        self.isRecovered = False  # 是否是恢复的任务
        self.state = "created"  # 任务状态: created, running, completed, failed, recovered
        
        logger.info(f"任务快照已创建: {msnID}, 任务总数: {len(msnList)}")
        
    def update_progress(self, taskIndex, task, result):
        """
        更新任务执行进度
        
        Args:
            taskIndex (int): 任务索引
            task (dict): 任务信息
            result (dict): 任务执行结果
        """
        self.currentTaskIndex = taskIndex
        if result.get("code") == 100:
            self.completedTasks.append({
                'task': task.copy(),
                'result': result.copy(),
                'timestamp': time.time()
            })
        else:
            self.failedTasks.append({
                'task': task.copy(),
                'result': result.copy(),
                'timestamp': time.time()
            })
        self.lastUpdatedTime = time.time()
        
        if (taskIndex + 1) % 100 == 0:  # 每完成100个任务记录一次
            logger.info(f"任务 {self.msnID} 进度更新: {taskIndex + 1}/{len(self.msnList)} 个任务已完成")
        
    def get_remaining_tasks(self):
        """
        获取剩余未完成的任务
        
        Returns:
            list: 剩余任务列表
        """
        if self.currentTaskIndex >= len(self.msnList):
            return []
        return self.msnList[self.currentTaskIndex:]
        
    def get_total_count(self):
        """
        获取总任务数量
        
        Returns:
            int: 总任务数
        """
        return len(self.msnList)
        
    def get_completed_count(self):
        """
        获取已完成的任务数量
        
        Returns:
            int: 已完成任务数
        """
        return len(self.completedTasks)
        
    def get_failed_count(self):
        """
        获取失败的任务数量
        
        Returns:
            int: 失败任务数
        """
        return len(self.failedTasks)
        
    def get_progress(self):
        """
        获取任务进度
        
        Returns:
            float: 进度百分比 (0-100)
        """
        total = self.get_total_count()
        if total == 0:
            return 0.0
        return (self.get_completed_count() / total) * 100
        
    def to_dict(self):
        """
        转换为字典格式
        
        Returns:
            dict: 快照的字典表示
        """
        return {
            'msnID': self.msnID,
            'msnInfo': self.msnInfo,
            'msnList': self.msnList,
            'apiKey': self.apiKey,
            'completedTasks': self.completedTasks,
            'failedTasks': self.failedTasks,
            'currentTaskIndex': self.currentTaskIndex,
            'createdTime': self.createdTime,
            'lastUpdatedTime': self.lastUpdatedTime,
            'isRecovered': self.isRecovered,
            'state': self.state
        }
        
    @classmethod
    def from_dict(cls, data):
        """
        从字典创建快照对象
        
        Args:
            data (dict): 快照数据
            
        Returns:
            MissionSnapshot: 快照对象
        """
        snapshot = cls(
            data['msnID'],
            data['msnInfo'],
            data['msnList'],
            data.get('apiKey'),
            None  # API对象无法序列化，需要重新初始化
        )
        snapshot.completedTasks = data.get('completedTasks', [])
        snapshot.failedTasks = data.get('failedTasks', [])
        snapshot.currentTaskIndex = data.get('currentTaskIndex', 0)
        snapshot.createdTime = data.get('createdTime', time.time())
        snapshot.lastUpdatedTime = data.get('lastUpdatedTime', time.time())
        snapshot.isRecovered = data.get('isRecovered', False)
        snapshot.state = data.get('state', 'created')
        
        return snapshot
        
    def mark_recovered(self):
        """标记任务为已恢复"""
        self.isRecovered = True
        self.state = "recovered"
        logger.info(f"任务 {self.msnID} 已标记为恢复状态")
    
    def save_to_file(self, directory=None):
        """保存快照到文件"""
        if directory is None:
            directory = os.path.join(os.getcwd(), "snapshots")
            
        os.makedirs(directory, exist_ok=True)
        
        filename = f"snapshot_{self.msnID}_{int(self.createdTime)}.json"
        filepath = os.path.join(directory, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"任务快照已保存到文件: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"保存任务快照到文件失败: {e}", exc_info=True)
            return None
    
    @classmethod
    def load_from_file(cls, filepath):
        """从文件加载快照"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            snapshot = cls.from_dict(data)
            logger.info(f"任务快照已从文件加载: {filepath}")
            return snapshot
        except Exception as e:
            logger.error(f"从文件加载任务快照失败: {e}", exc_info=True)
            return None
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"任务快照已保存到: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"保存任务快照失败: {e}")
            return None
        
    @classmethod
    def load_from_file(cls, filepath):
        """从文件加载快照"""
        import json
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"任务快照已从: {filepath} 加载")
            return cls.from_dict(data)
        except Exception as e:
            logger.error(f"加载任务快照失败: {e}")
            return None
        
    def __str__(self):
        return f"MissionSnapshot(msnID={self.msnID}, progress={self.get_progress():.1f}%, completed={self.get_completed_count()}, failed={self.get_failed_count()}, state={self.state})"

class SnapshotManager:
    """任务快照管理器"""
    
    def __init__(self):
        self.snapshots = {}  # msnID: MissionSnapshot
        self.snapshot_dir = os.path.join(os.getcwd(), "snapshots")
        os.makedirs(self.snapshot_dir, exist_ok=True)
        
    def create_snapshot(self, msnID, msnInfo, msnList, apiKey, apiInfo):
        """创建任务快照"""
        snapshot = MissionSnapshot(msnID, msnInfo, msnList, apiKey, apiInfo)
        self.snapshots[msnID] = snapshot
        logger.info(f"已创建任务快照: {snapshot}")
        return snapshot
        
    def get_snapshot(self, msnID):
        """获取任务快照"""
        return self.snapshots.get(msnID)
        
    def update_snapshot(self, msnID, index, task, result=None):
        """更新任务快照"""
        snapshot = self.snapshots.get(msnID)
        if snapshot:
            snapshot.update_progress(index, task, result)
            # 定期保存到文件
            if index % 10 == 0:  # 每处理10个任务保存一次
                snapshot.save_to_file(self.snapshot_dir)
            return True
        return False
        
    def remove_snapshot(self, msnID):
        """移除任务快照"""
        if msnID in self.snapshots:
            del self.snapshots[msnID]
            logger.info(f"已移除任务快照: {msnID}")
            return True
        return False
        
    def save_all_snapshots(self):
        """保存所有快照到文件"""
        for snapshot in self.snapshots.values():
            snapshot.save_to_file(self.snapshot_dir)
        
    def load_snapshots_from_files(self):
        """从文件加载所有快照"""
        import glob
        
        snapshot_files = glob.glob(os.path.join(self.snapshot_dir, "snapshot_*.json"))
        
        for filepath in snapshot_files:
            snapshot = MissionSnapshot.load_from_file(filepath)
            if snapshot:
                self.snapshots[snapshot.msnID] = snapshot
        
        logger.info(f"已从文件加载 {len(self.snapshots)} 个任务快照")
        
    def get_all_snapshots(self):
        """获取所有快照"""
        return list(self.snapshots.values())
        
    def cleanup_old_snapshots(self, days=7):
        """清理旧的快照文件"""
        import glob
        import shutil
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        snapshot_files = glob.glob(os.path.join(self.snapshot_dir, "snapshot_*.json"))
        
        for filepath in snapshot_files:
            try:
                # 从文件名提取时间戳
                filename = os.path.basename(filepath)
                parts = filename.split("_")
                if len(parts) >= 3:
                    timestamp = int(parts[2].split(".")[0])
                    if timestamp < cutoff_time:
                        os.remove(filepath)
                        logger.info(f"已清理旧快照文件: {filepath}")
            except Exception as e:
                logger.error(f"清理旧快照文件失败: {e}")

# 全局快照管理器实例
SnapshotManagerInstance = SnapshotManager()