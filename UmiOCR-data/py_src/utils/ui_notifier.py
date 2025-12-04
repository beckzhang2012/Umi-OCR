import threading
import logging
import time

# 配置日志
logger = logging.getLogger(__name__)

# 定义UI通知接口
class UINotifier:
    """UI通知接口，用于在文件句柄出现问题时向用户显示提示"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._pending_notifications = []
        self._is_running = False
        self._notification_thread = None
    
    def show_handle_warning(self, message, retry_count=None):
        """显示文件句柄警告通知"""
        with self._lock:
            notification = {
                'type': 'handle_warning',
                'message': message,
                'retry_count': retry_count,
                'timestamp': time.time()
            }
            self._pending_notifications.append(notification)
            logger.warning(f"Handle warning: {message}")
            
            # 触发UI更新
            self._trigger_ui_update(notification)
    
    def show_handle_recovered(self, message):
        """显示文件句柄恢复通知"""
        with self._lock:
            notification = {
                'type': 'handle_recovered',
                'message': message,
                'timestamp': time.time()
            }
            self._pending_notifications.append(notification)
            logger.info(f"Handle recovered: {message}")
            
            # 触发UI更新
            self._trigger_ui_update(notification)
    
    def show_pending_writes_info(self, count):
        """显示待写队列信息"""
        with self._lock:
            notification = {
                'type': 'pending_writes',
                'count': count,
                'message': f"有 {count} 个文件等待写入",
                'timestamp': time.time()
            }
            self._pending_notifications.append(notification)
            logger.info(f"Pending writes info: {count} files waiting")
            
            # 触发UI更新
            self._trigger_ui_update(notification)
    
    def _trigger_ui_update(self, notification):
        """触发UI更新（需要根据实际UI框架实现）"""
        # 这里需要根据实际的UI框架来实现通知显示
        # 例如，在Qt中可以使用信号槽机制
        # 暂时使用日志输出作为替代
        logger.debug(f"UI notification triggered: {notification['type']} - {notification['message']}")
        
        # TODO: 实现实际的UI通知显示
        # 例如：
        # - 显示托盘通知
        # - 在状态栏显示消息
        # - 弹出提示窗口
    
    def get_pending_notifications(self):
        """获取待处理的通知"""
        with self._lock:
            return self._pending_notifications.copy()
    
    def clear_notifications(self):
        """清除所有通知"""
        with self._lock:
            self._pending_notifications.clear()
    
    def start_auto_notification(self, interval=10):
        """启动自动通知线程"""
        if self._is_running:
            return
        
        self._is_running = True
        self._notification_thread = threading.Thread(target=self._auto_notification_loop, args=(interval,), daemon=True)
        self._notification_thread.start()
        logger.info("UI notifier started")
    
    def stop_auto_notification(self):
        """停止自动通知线程"""
        self._is_running = False
        if self._notification_thread:
            self._notification_thread.join(timeout=1)
        logger.info("UI notifier stopped")
    
    def _auto_notification_loop(self, interval):
        """自动通知循环"""
        from .file_handle_manager import file_handle_manager
        
        while self._is_running:
            time.sleep(interval)
            
            # 获取当前统计信息
            stats = file_handle_manager.get_stats()
            
            # 检查是否有待写内容
            if stats['pending_writes'] > 0:
                self.show_pending_writes_info(stats['pending_writes'])

# 创建全局实例
ui_notifier = UINotifier()
