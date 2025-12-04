# ===============================================
# =============== 任务排程管理器 ===============
# ===============================================

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from uuid import uuid4
from croniter import croniter

from umi_log import logger
from ..mission.mission_ocr import MissionOCR


class ScheduledTask:
    """计划任务模型"""
    def __init__(self, task_data: Dict):
        self.id = task_data.get('id', str(uuid4()))
        self.name = task_data.get('name', '')
        self.task_type = task_data.get('task_type', 'batch_ocr')  # batch_ocr 或 screenshot_ocr
        self.schedule_type = task_data.get('schedule_type', 'once')  # once, daily, weekly, cron
        self.schedule_config = task_data.get('schedule_config', {})
        self.ocr_template = task_data.get('ocr_template', '')
        self.folders = task_data.get('folders', [])
        self.retry_policy = task_data.get('retry_policy', {'max_retries': 0, 'retry_interval': 60})
        self.concurrency_limit = task_data.get('concurrency_limit', 1)
        self.enabled = task_data.get('enabled', True)
        self.last_execution = task_data.get('last_execution', None)
        self.next_execution = task_data.get('next_execution', None)
        self.created_at = task_data.get('created_at', datetime.now().isoformat())
        self.updated_at = task_data.get('updated_at', datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'task_type': self.task_type,
            'schedule_type': self.schedule_type,
            'schedule_config': self.schedule_config,
            'ocr_template': self.ocr_template,
            'folders': self.folders,
            'retry_policy': self.retry_policy,
            'concurrency_limit': self.concurrency_limit,
            'enabled': self.enabled,
            'last_execution': self.last_execution,
            'next_execution': self.next_execution,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def calculate_next_execution(self) -> Optional[datetime]:
        """计算下次执行时间"""
        now = datetime.now()
        
        if self.schedule_type == 'once':
            # 一次性任务，使用指定的执行时间
            if 'execution_time' in self.schedule_config:
                exec_time = datetime.fromisoformat(self.schedule_config['execution_time'])
                if exec_time > now:
                    return exec_time
            return None
            
        elif self.schedule_type == 'daily':
            # 每天执行
            hour = self.schedule_config.get('hour', 0)
            minute = self.schedule_config.get('minute', 0)
            exec_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if exec_time <= now:
                exec_time += timedelta(days=1)
            return exec_time
            
        elif self.schedule_type == 'weekly':
            # 每周执行
            day_of_week = self.schedule_config.get('day_of_week', 0)  # 0=周一, 6=周日
            hour = self.schedule_config.get('hour', 0)
            minute = self.schedule_config.get('minute', 0)
            
            # 计算下一个指定星期几
            days_ahead = day_of_week - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            
            exec_time = now + timedelta(days=days_ahead)
            exec_time = exec_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return exec_time
            
        elif self.schedule_type == 'cron':
            # 自定义Cron表达式
            cron_expr = self.schedule_config.get('cron_expr', '')
            if cron_expr:
                try:
                    cron = croniter(cron_expr, now)
                    next_time = cron.get_next(datetime)
                    return next_time
                except Exception as e:
                    logger.error(f"Invalid cron expression {cron_expr}: {e}")
                    return None
            return None
            
        return None


class TaskExecutionLog:
    """任务执行日志"""
    def __init__(self, task_id: str, execution_data: Dict = None):
        self.id = str(uuid4())
        self.task_id = task_id
        self.start_time = execution_data.get('start_time', datetime.now().isoformat())
        self.end_time = execution_data.get('end_time', None)
        self.status = execution_data.get('status', 'running')  # running, success, failed
        self.success_count = execution_data.get('success_count', 0)
        self.failed_count = execution_data.get('failed_count', 0)
        self.error_message = execution_data.get('error_message', '')
        self.details = execution_data.get('details', {})

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'status': self.status,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'error_message': self.error_message,
            'details': self.details
        }


class SchedulerManager:
    """任务排程管理器"""
    def __init__(self):
        self.tasks: List[ScheduledTask] = []
        self.execution_logs: List[TaskExecutionLog] = []
        self._lock = threading.Lock()
        self._scheduler_thread = None
        self._running = False
        self._config_file = os.path.join(os.path.dirname(__file__), 'scheduler_config.json')
        
        # 加载配置
        self._load_config()
        
        # 启动调度器
        self.start()

    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # 加载任务
                if 'tasks' in config:
                    self.tasks = [ScheduledTask(task_data) for task_data in config['tasks']]
                    
                # 加载执行日志
                if 'execution_logs' in config:
                    self.execution_logs = [TaskExecutionLog(log_data['task_id'], log_data) 
                                          for log_data in config['execution_logs']]
                    
                logger.info(f"Loaded {len(self.tasks)} tasks and {len(self.execution_logs)} logs")
                
            except Exception as e:
                logger.error(f"Failed to load scheduler config: {e}")

    def _save_config(self):
        """保存配置文件"""
        try:
            config = {
                'tasks': [task.to_dict() for task in self.tasks],
                'execution_logs': [log.to_dict() for log in self.execution_logs]
            }
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
            logger.info("Scheduler config saved")
            
        except Exception as e:
            logger.error(f"Failed to save scheduler config: {e}")

    def start(self):
        """启动调度器"""
        if not self._running:
            self._running = True
            self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self._scheduler_thread.start()
            logger.info("Scheduler started")

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join()
            logger.info("Scheduler stopped")

    def _scheduler_loop(self):
        """调度器主循环"""
        while self._running:
            now = datetime.now()
            
            with self._lock:
                # 检查所有任务是否需要执行
                for task in self.tasks:
                    if task.enabled and task.next_execution:
                        next_execution = datetime.fromisoformat(task.next_execution)
                        if next_execution <= now:
                            self._execute_task(task)
                            
                            # 更新下次执行时间
                            if task.schedule_type != 'once':
                                next_time = task.calculate_next_execution()
                                task.next_execution = next_time.isoformat() if next_time else None
                            else:
                                task.next_execution = None  # 一次性任务执行后不再执行
                            
                            task.updated_at = datetime.now().isoformat()
                            
                # 保存配置
                self._save_config()
            
            # 每分钟检查一次
            time.sleep(60)

    def _execute_task(self, task: ScheduledTask):
        """执行任务"""
        logger.info(f"Executing task: {task.name} (ID: {task.id})")
        
        # 创建执行日志
        execution_log = TaskExecutionLog(task.id)
        self.execution_logs.append(execution_log)
        
        try:
            # 更新任务状态
            task.last_execution = datetime.now().isoformat()
            
            if task.task_type == 'batch_ocr':
                # 执行批量OCR任务
                success_count, failed_count = self._execute_batch_ocr(task)
                execution_log.success_count = success_count
                execution_log.failed_count = failed_count
                execution_log.status = 'success'
                
            elif task.task_type == 'screenshot_ocr':
                # 执行截图OCR任务
                success_count, failed_count = self._execute_screenshot_ocr(task)
                execution_log.success_count = success_count
                execution_log.failed_count = failed_count
                execution_log.status = 'success'
            
            logger.info(f"Task {task.name} completed successfully: {success_count} success, {failed_count} failed")
            
        except Exception as e:
            execution_log.status = 'failed'
            execution_log.error_message = str(e)
            logger.error(f"Task {task.name} failed: {e}")
            
        finally:
            execution_log.end_time = datetime.now().isoformat()

    def _execute_batch_ocr(self, task: ScheduledTask) -> tuple[int, int]:
        """执行批量OCR任务"""
        success_count = 0
        failed_count = 0
        
        # 遍历所有文件夹
        for folder in task.folders:
            if not os.path.exists(folder):
                logger.warning(f"Folder not found: {folder}")
                failed_count += 1
                continue
                
            # 获取文件夹中的所有图片文件
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
            image_files = []
            
            for root, _, files in os.walk(folder):
                for file in files:
                    if os.path.splitext(file)[1].lower() in image_extensions:
                        image_files.append(os.path.join(root, file))
            
            # 执行OCR
            for image_path in image_files:
                try:
                    # 使用MissionOCR执行OCR
                    msn_info = {
                        'argd': {},  # 需要根据模板配置参数
                        'onStart': lambda *x: None,
                        'onReady': lambda *x: None,
                        'onGet': lambda *x: None,
                        'onEnd': lambda *x: None
                    }
                    
                    msn_list = [{'path': image_path}]
                    results = MissionOCR.addMissionWait(msn_info, msn_list)
                    
                    for result in results:
                        if result.get('result', {}).get('code') == 100:
                            success_count += 1
                        else:
                            failed_count += 1
                            
                except Exception as e:
                    logger.error(f"Failed to process {image_path}: {e}")
                    failed_count += 1
                    
        return success_count, failed_count

    def _execute_screenshot_ocr(self, task: ScheduledTask) -> tuple[int, int]:
        """执行截图OCR任务"""
        # 截图OCR任务需要特殊处理，这里暂时返回0
        # 实际实现需要调用截图功能
        return 0, 0

    # ========================= 【公共接口】 =========================

    def get_tasks(self) -> List[Dict]:
        """获取所有任务"""
        with self._lock:
            return [task.to_dict() for task in self.tasks]

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取单个任务"""
        with self._lock:
            for task in self.tasks:
                if task.id == task_id:
                    return task.to_dict()
            return None

    def add_task(self, task_data: Dict) -> str:
        """添加任务"""
        with self._lock:
            task = ScheduledTask(task_data)
            
            # 计算下次执行时间
            next_time = task.calculate_next_execution()
            task.next_execution = next_time.isoformat() if next_time else None
            
            self.tasks.append(task)
            self._save_config()
            return task.id

    def update_task(self, task_id: str, task_data: Dict) -> bool:
        """更新任务"""
        with self._lock:
            for i, task in enumerate(self.tasks):
                if task.id == task_id:
                    # 更新任务属性
                    for key, value in task_data.items():
                        if hasattr(task, key):
                            setattr(task, key, value)
                    
                    # 重新计算下次执行时间
                    next_time = task.calculate_next_execution()
                    task.next_execution = next_time.isoformat() if next_time else None
                    task.updated_at = datetime.now().isoformat()
                    
                    self._save_config()
                    return True
            return False

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        with self._lock:
            for i, task in enumerate(self.tasks):
                if task.id == task_id:
                    del self.tasks[i]
                    self._save_config()
                    return True
            return False

    def toggle_task(self, task_id: str) -> bool:
        """切换任务启用状态"""
        with self._lock:
            for task in self.tasks:
                if task.id == task_id:
                    task.enabled = not task.enabled
                    self._save_config()
                    return True
            return False

    def get_execution_logs(self, task_id: str = None) -> List[Dict]:
        """获取执行日志"""
        with self._lock:
            if task_id:
                return [log.to_dict() for log in self.execution_logs if log.task_id == task_id]
            return [log.to_dict() for log in self.execution_logs]

    def export_logs(self, file_path: str) -> bool:
        """导出日志到JSON文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([log.to_dict() for log in self.execution_logs], f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to export logs: {e}")
            return False


# 全局任务排程管理器实例
Scheduler = SchedulerManager()