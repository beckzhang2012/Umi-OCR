import os
import time
import threading
import weakref
from collections import defaultdict
import logging
from .ui_notifier import ui_notifier

# 配置日志
logger = logging.getLogger(__name__)

class FileHandleManager:
    """文件句柄管理和监控系统"""
    
    def __init__(self):
        self._handle_registry = weakref.WeakKeyDictionary()  # 存储文件句柄和相关信息
        self._lock = threading.Lock()
        self._pending_writes = defaultdict(list)  # 待写内容缓存队列
        self._max_retries = 3  # 最大重试次数
        self._retry_delay = 0.1  # 重试延迟（秒）
        self._monitor_thread = None
        self._is_running = False
        self._stats = {
            'total_handles': 0,
            'active_handles': 0,
            'pending_writes': 0,
            'write_failures': 0,
            'write_successes': 0
        }
    
    def register_handle(self, file_obj, file_path, mode='r', description=''):
        """注册文件句柄"""
        with self._lock:
            self._handle_registry[file_obj] = {
                'path': file_path,
                'mode': mode,
                'description': description,
                'opened_time': time.time(),
                'last_accessed': time.time()
            }
            self._stats['total_handles'] += 1
            self._stats['active_handles'] += 1
            logger.debug(f"Registered file handle: {file_path}, mode: {mode}")
    
    def unregister_handle(self, file_obj):
        """注销文件句柄"""
        with self._lock:
            if file_obj in self._handle_registry:
                info = self._handle_registry.pop(file_obj)
                self._stats['active_handles'] -= 1
                logger.debug(f"Unregistered file handle: {info['path']}")
    
    def update_access_time(self, file_obj):
        """更新文件句柄访问时间"""
        with self._lock:
            if file_obj in self._handle_registry:
                self._handle_registry[file_obj]['last_accessed'] = time.time()
    
    def add_pending_write(self, file_path, content, mode='a', encoding='utf-8'):
        """添加待写内容到缓存队列"""
        with self._lock:
            self._pending_writes[file_path].append({
                'content': content,
                'mode': mode,
                'encoding': encoding,
                'retries': 0,
                'added_time': time.time()
            })
            self._stats['pending_writes'] += 1
            logger.warning(f"Added pending write for {file_path}, queue size: {len(self._pending_writes[file_path])}")
            
            # 显示UI通知
            if self._stats['pending_writes'] >= 5:  # 当待写队列超过5个时显示通知
                ui_notifier.show_handle_warning(
                    f"文件句柄资源紧张，{self._stats['pending_writes']} 个任务等待处理",
                    retry_count=self._max_retries
                )
    
    def retry_pending_writes(self):
        """重试缓存中的待写内容"""
        with self._lock:
            paths_to_remove = []
            
            for file_path, writes in self._pending_writes.items():
                writes_to_keep = []
                
                for write in writes:
                    if write['retries'] >= self._max_retries:
                        logger.error(f"Max retries reached for writing to {file_path}")
                        self._stats['write_failures'] += 1
                        continue
                    
                    try:
                        with open(file_path, write['mode'], encoding=write['encoding']) as f:
                            f.write(write['content'])
                        logger.info(f"Successfully retried writing to {file_path}")
                        self._stats['write_successes'] += 1
                        self._stats['pending_writes'] -= 1
                        
                        # 如果所有待写任务都完成了，显示恢复通知
                        if self._stats['pending_writes'] == 0:
                            ui_notifier.show_handle_recovered("所有文件写入任务已恢复正常")
                    except Exception as e:
                        write['retries'] += 1
                        write['added_time'] = time.time()
                        writes_to_keep.append(write)
                        logger.warning(f"Retry {write['retries']}/{self._max_retries} failed for {file_path}: {e}")
                
                if writes_to_keep:
                    self._pending_writes[file_path] = writes_to_keep
                else:
                    paths_to_remove.append(file_path)
            
            # 清理空的路径条目
            for path in paths_to_remove:
                del self._pending_writes[path]
    
    def get_stats(self):
        """获取统计信息"""
        with self._lock:
            return self._stats.copy()
    
    def get_active_handles(self):
        """获取活跃句柄信息"""
        with self._lock:
            return [info for info in self._handle_registry.values()]
    
    def start_monitoring(self, interval=5):
        """启动后台监控线程"""
        if self._is_running:
            return
        
        self._is_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()
        logger.info("File handle monitor started")
    
    def stop_monitoring(self):
        """停止后台监控线程"""
        self._is_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
        logger.info("File handle monitor stopped")
    
    def _monitor_loop(self, interval):
        """监控循环"""
        while self._is_running:
            time.sleep(interval)
            
            # 检查活跃句柄
            active_handles = self.get_active_handles()
            logger.debug(f"Active file handles: {len(active_handles)}")
            
            # 检查长时间未访问的句柄
            current_time = time.time()
            for info in active_handles:
                if current_time - info['last_accessed'] > 60:  # 超过60秒未访问
                    logger.warning(f"File handle {info['path']} inactive for {current_time - info['last_accessed']:.1f}s")
            
            # 重试待写内容
            if self._pending_writes:
                logger.info(f"Retrying {self._stats['pending_writes']} pending writes")
                self.retry_pending_writes()
            
            # 记录统计信息
            stats = self.get_stats()
            logger.debug(f"File handle stats: {stats}")
            
            # 检查句柄使用情况，如果活跃句柄过多，显示警告
            if stats['active_handles'] > 50:  # 阈值可根据实际情况调整
                ui_notifier.show_handle_warning(
                    f"系统文件句柄使用率较高，当前活跃句柄: {stats['active_handles']}",
                    retry_count=self._max_retries
                )

# 创建全局实例
file_handle_manager = FileHandleManager()
