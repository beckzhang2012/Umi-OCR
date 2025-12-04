import os
import time
import json
import threading
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Callable
from PySide2.QtCore import QObject, Slot, Signal, QMutex, QThread
import logging

logger = logging.getLogger(__name__)

class MonitorItem:
    """监控项模型"""
    def __init__(self, data: Dict):
        self.id = data.get('id', str(int(time.time() * 1000)))
        self.name = data.get('name', '')
        self.directory = data.get('directory', '')
        self.file_types = data.get('file_types', ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'])
        self.polling_interval = data.get('polling_interval', 60)  # 轮询间隔（秒）
        self.recursive_level = data.get('recursive_level', 0)  # 递归层级，0表示不递归
        self.enabled = data.get('enabled', True)
        self.routes = data.get('routes', [])  # 路由规则
        self.last_polled = data.get('last_polled', None)
        self.created_at = data.get('created_at', datetime.now().isoformat())
        self.updated_at = data.get('updated_at', datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'directory': self.directory,
            'file_types': self.file_types,
            'polling_interval': self.polling_interval,
            'recursive_level': self.recursive_level,
            'enabled': self.enabled,
            'routes': self.routes,
            'last_polled': self.last_polled,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class RouteRule:
    """路由规则模型"""
    def __init__(self, data: Dict):
        self.id = data.get('id', str(int(time.time() * 1000)))
        self.name = data.get('name', '')
        self.conditions = data.get('conditions', [])  # 条件列表
        self.template_id = data.get('template_id', '')  # 目标模板ID
        self.output_directory = data.get('output_directory', '')  # 输出目录
        self.priority = data.get('priority', 0)  # 优先级，数字越大越优先

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'conditions': self.conditions,
            'template_id': self.template_id,
            'output_directory': self.output_directory,
            'priority': self.priority
        }

class FileTask:
    """文件任务模型"""
    def __init__(self, file_path: str, monitor_item_id: str):
        self.id = str(int(time.time() * 1000)) + str(hash(file_path) % 1000)
        self.file_path = file_path
        self.monitor_item_id = monitor_item_id
        self.status = 'waiting'  # waiting, processing, completed, failed
        self.assigned_template = None
        self.assigned_output = None
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.file_hash = self._calculate_file_hash()

    def _calculate_file_hash(self) -> str:
        """计算文件哈希值"""
        try:
            hasher = hashlib.md5()
            with open(self.file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {self.file_path}: {e}")
            return ''

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'monitor_item_id': self.monitor_item_id,
            'status': self.status,
            'assigned_template': self.assigned_template,
            'assigned_output': self.assigned_output,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error_message': self.error_message,
            'file_hash': self.file_hash
        }

class DirectoryMonitor(QObject):
    """目录监控管理器"""
    
    # 信号
    monitorItemAdded = Signal(dict)
    monitorItemUpdated = Signal(dict)
    monitorItemDeleted = Signal(str)
    fileTaskAdded = Signal(dict)
    fileTaskUpdated = Signal(dict)
    fileTaskDeleted = Signal(str)
    statusChanged = Signal(str)
    alertTriggered = Signal(str, str)  # 告警类型, 告警消息

    def __init__(self):
        super().__init__()
        self._monitor_items: List[MonitorItem] = []
        self._file_tasks: List[FileTask] = []
        self._processed_files: Dict[str, Dict] = {}  # 已处理文件记录 {file_hash: {last_processed, template_id}}
        self._running = False
        self._lock = QMutex()
        self._threads: List[threading.Thread] = []
        self._config_path = os.path.join(os.getcwd(), 'directory_monitor_config.json')
        self._logs_path = os.path.join(os.getcwd(), 'directory_monitor_logs.json')
        self._load_config()

    def start(self):
        """启动目录监控"""
        if self._running:
            return
        
        self._running = True
        self.statusChanged.emit('running')
        logger.info("Directory monitor started")
        
        # 为每个监控项启动轮询线程
        for item in self._monitor_items:
            if item.enabled:
                self._start_monitor_thread(item)

    def stop(self):
        """停止目录监控"""
        self._running = False
        self.statusChanged.emit('stopped')
        logger.info("Directory monitor stopped")
        
        # 等待所有线程结束
        for thread in self._threads:
            thread.join()
        self._threads.clear()

    def _start_monitor_thread(self, item: MonitorItem):
        """启动监控项的轮询线程"""
        thread = threading.Thread(target=self._monitor_loop, args=(item,))
        thread.daemon = True
        thread.start()
        self._threads.append(thread)

    def _monitor_loop(self, item: MonitorItem):
        """监控项轮询循环"""
        while self._running and item.enabled:
            try:
                self._scan_directory(item)
                item.last_polled = datetime.now().isoformat()
                self._save_config()
            except Exception as e:
                logger.error(f"Error monitoring {item.directory}: {e}")
                self.alertTriggered.emit('monitor_error', f"监控目录 {item.directory} 时出错: {e}")
            
            # 等待轮询间隔
            time.sleep(item.polling_interval)

    def _scan_directory(self, item: MonitorItem):
        """扫描目录中的文件"""
        if not os.path.exists(item.directory):
            logger.warning(f"Directory not found: {item.directory}")
            self.alertTriggered.emit('directory_not_found', f"监控目录不存在: {item.directory}")
            return
        
        # 获取目录中的所有文件
        image_files = []
        for root, _, files in os.walk(item.directory):
            # 计算当前递归层级
            current_level = root.replace(item.directory, '').count(os.sep)
            if item.recursive_level >= 0 and current_level > item.recursive_level:
                continue
                
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in item.file_types:
                    file_path = os.path.join(root, file)
                    image_files.append(file_path)
        
        # 处理新文件
        for file_path in image_files:
            self._process_new_file(file_path, item)

    def _process_new_file(self, file_path: str, item: MonitorItem):
        """处理新发现的文件"""
        # 检查是否已处理过
        file_hash = self._calculate_file_hash(file_path)
        if file_hash in self._processed_files:
            return
        
        # 创建文件任务
        task = FileTask(file_path, item.id)
        
        # 应用路由规则
        self._apply_routing_rules(task, item)
        
        # 添加到任务队列
        with self._lock:
            self._file_tasks.append(task)
            self._processed_files[file_hash] = {
                'last_processed': datetime.now().isoformat(),
                'template_id': task.assigned_template
            }
        
        self.fileTaskAdded.emit(task.to_dict())
        logger.info(f"New file detected and added to queue: {file_path}")

    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return ''

    def _apply_routing_rules(self, task: FileTask, item: MonitorItem):
        """应用路由规则"""
        # 按优先级排序路由规则
        sorted_routes = sorted(item.routes, key=lambda x: x.get('priority', 0), reverse=True)
        
        for route in sorted_routes:
            if self._check_route_conditions(task.file_path, route.get('conditions', [])):
                task.assigned_template = route.get('template_id')
                task.assigned_output = route.get('output_directory')
                break

    def _check_route_conditions(self, file_path: str, conditions: List[Dict]) -> bool:
        """检查路由条件是否满足"""
        if not conditions:
            return True
        
        for condition in conditions:
            condition_type = condition.get('type')
            value = condition.get('value')
            
            if condition_type == 'filename_regex':
                import re
                if not re.search(value, os.path.basename(file_path)):
                    return False
            elif condition_type == 'file_size_min':
                if os.path.getsize(file_path) < int(value):
                    return False
            elif condition_type == 'file_size_max':
                if os.path.getsize(file_path) > int(value):
                    return False
            elif condition_type == 'modified_time_hours':
                # 检查文件修改时间是否在指定小时内
                modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                hours_diff = (datetime.now() - modified_time).total_seconds() / 3600
                if hours_diff > float(value):
                    return False
            # 可以添加更多条件类型
        
        return True

    # ========================= 【监控项管理接口】 =========================

    @Slot(result='QVariantList')
    def get_monitor_items(self) -> List[Dict]:
        """获取所有监控项"""
        with self._lock:
            return [item.to_dict() for item in self._monitor_items]

    @Slot(str, result='QVariant')
    def get_monitor_item(self, item_id: str) -> Optional[Dict]:
        """获取单个监控项"""
        with self._lock:
            for item in self._monitor_items:
                if item.id == item_id:
                    return item.to_dict()
            return None

    @Slot('QVariant', result=str)
    def add_monitor_item(self, item_data: Dict) -> str:
        """添加监控项"""
        with self._lock:
            item = MonitorItem(item_data)
            self._monitor_items.append(item)
            self._save_config()
            
            # 如果监控项已启用且监控器正在运行，启动轮询线程
            if item.enabled and self._running:
                self._start_monitor_thread(item)
            
            self.monitorItemAdded.emit(item.to_dict())
            logger.info(f"Monitor item added: {item.name}")
            return item.id

    @Slot(str, 'QVariant', result=bool)
    def update_monitor_item(self, item_id: str, item_data: Dict) -> bool:
        """更新监控项"""
        with self._lock:
            for i, item in enumerate(self._monitor_items):
                if item.id == item_id:
                    # 更新属性
                    for key, value in item_data.items():
                        if hasattr(item, key):
                            setattr(item, key, value)
                    item.updated_at = datetime.now().isoformat()
                    self._save_config()
                    self.monitorItemUpdated.emit(item.to_dict())
                    logger.info(f"Monitor item updated: {item.name}")
                    return True
            return False

    @Slot(str, result=bool)
    def delete_monitor_item(self, item_id: str) -> bool:
        """删除监控项"""
        with self._lock:
            for i, item in enumerate(self._monitor_items):
                if item.id == item_id:
                    del self._monitor_items[i]
                    self._save_config()
                    self.monitorItemDeleted.emit(item_id)
                    logger.info(f"Monitor item deleted: {item.name}")
                    return True
            return False

    @Slot(str, result=bool)
    def toggle_monitor_item(self, item_id: str) -> bool:
        """切换监控项启用状态"""
        with self._lock:
            for item in self._monitor_items:
                if item.id == item_id:
                    item.enabled = not item.enabled
                    self._save_config()
                    
                    # 如果监控器正在运行，启动或停止轮询线程
                    if self._running:
                        if item.enabled:
                            self._start_monitor_thread(item)
                    
                    self.monitorItemUpdated.emit(item.to_dict())
                    logger.info(f"Monitor item {'enabled' if item.enabled else 'disabled'}: {item.name}")
                    return True
            return False

    # ========================= 【任务管理接口】 =========================

    @Slot(result='QVariantList')
    def get_file_tasks(self) -> List[Dict]:
        """获取所有文件任务"""
        with self._lock:
            return [task.to_dict() for task in self._file_tasks]

    @Slot(str, result='QVariant')
    def get_file_task(self, task_id: str) -> Optional[Dict]:
        """获取单个文件任务"""
        with self._lock:
            for task in self._file_tasks:
                if task.id == task_id:
                    return task.to_dict()
            return None

    @Slot(str, result=bool)
    def retry_file_task(self, task_id: str) -> bool:
        """重试文件任务"""
        with self._lock:
            for task in self._file_tasks:
                if task.id == task_id:
                    task.status = 'waiting'
                    task.error_message = None
                    task.started_at = None
                    task.completed_at = None
                    self.fileTaskUpdated.emit(task.to_dict())
                    logger.info(f"File task retried: {task.file_path}")
                    return True
            return False

    @Slot(str, result=bool)
    def skip_file_task(self, task_id: str) -> bool:
        """跳过文件任务"""
        with self._lock:
            for task in self._file_tasks:
                if task.id == task_id:
                    task.status = 'completed'
                    task.completed_at = datetime.now().isoformat()
                    self.fileTaskUpdated.emit(task.to_dict())
                    logger.info(f"File task skipped: {task.file_path}")
                    return True
            return False

    @Slot(str, result=bool)
    def delete_file_task(self, task_id: str) -> bool:
        """删除文件任务"""
        with self._lock:
            for i, task in enumerate(self._file_tasks):
                if task.id == task_id:
                    del self._file_tasks[i]
                    self.fileTaskDeleted.emit(task_id)
                    logger.info(f"File task deleted: {task.file_path}")
                    return True
            return False

    # ========================= 【统计信息接口】 =========================

    @Slot(result='QVariant')
    def get_task_stats(self) -> Dict:
        """获取任务统计信息"""
        with self._lock:
            stats = {
                'waiting': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0,
                'total': len(self._file_tasks)
            }
            for task in self._file_tasks:
                if task.status in stats:
                    stats[task.status] += 1
            return stats

    # ========================= 【配置管理】 =========================

    def _load_config(self):
        """加载配置"""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._monitor_items = [MonitorItem(item) for item in config.get('monitor_items', [])]
                    self._processed_files = config.get('processed_files', {})
                logger.info("Directory monitor config loaded")
            except Exception as e:
                logger.error(f"Failed to load directory monitor config: {e}")

    def _save_config(self):
        """保存配置"""
        try:
            config = {
                'monitor_items': [item.to_dict() for item in self._monitor_items],
                'processed_files': self._processed_files
            }
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info("Directory monitor config saved")
        except Exception as e:
            logger.error(f"Failed to save directory monitor config: {e}")

    # ========================= 【日志管理】 =========================

    def _log_task(self, task: FileTask):
        """记录任务日志"""
        try:
            log_entry = {
                'task_id': task.id,
                'file_path': task.file_path,
                'status': task.status,
                'assigned_template': task.assigned_template,
                'assigned_output': task.assigned_output,
                'created_at': task.created_at,
                'started_at': task.started_at,
                'completed_at': task.completed_at,
                'error_message': task.error_message,
                'file_hash': task.file_hash,
                'timestamp': datetime.now().isoformat()
            }
            
            # 读取现有日志
            logs = []
            if os.path.exists(self._logs_path):
                with open(self._logs_path, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            # 添加新日志
            logs.append(log_entry)
            
            # 保留最近10000条日志
            if len(logs) > 10000:
                logs = logs[-10000:]
            
            # 保存日志
            with open(self._logs_path, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to log task: {e}")

# 全局目录监控管理器实例
DirectoryMonitorInstance = DirectoryMonitor()