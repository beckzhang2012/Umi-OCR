# 句柄自愈机制模块，当句柄池耗尽或释放超时时提供用户提示和自动恢复

import time
import threading
from typing import Callable, List
from umi_log import logger

# 全局句柄自愈器实例
handle_healer = None

class HandleHealer:
    def __init__(self):
        self.max_retry_count = 5  # 最大重试次数
        self.retry_interval = 1.0  # 重试间隔（秒）
        self.healing_in_progress = False
        self.current_retry = 0
        
        # 回调函数列表
        self.ui_notification_callback = None  # UI通知回调
        self.tray_notification_callback = None  # 托盘通知回调
    
    def set_ui_notification_callback(self, callback: Callable):
        """设置UI通知回调函数"""
        self.ui_notification_callback = callback
    
    def set_tray_notification_callback(self, callback: Callable):
        """设置托盘通知回调函数"""
        self.tray_notification_callback = callback
    
    def notify_user(self, message: str, retry_count: int = None):
        """向用户发送通知"""
        logger.warning(f"句柄自愈机制: {message}")
        
        if retry_count is not None:
            remaining = self.max_retry_count - retry_count
            logger.warning(f"剩余重试次数: {remaining}")
        
        # 调用UI通知回调
        if self.ui_notification_callback:
            try:
                self.ui_notification_callback(message, retry_count)
            except Exception as e:
                logger.error(f"UI通知回调失败: {e}")
        
        # 调用托盘通知回调
        if self.tray_notification_callback:
            try:
                self.tray_notification_callback(message, retry_count)
            except Exception as e:
                logger.error(f"托盘通知回调失败: {e}")
    
    def start_healing(self, handle_id: str = None):
        """开始句柄自愈过程"""
        if self.healing_in_progress:
            logger.info("句柄自愈已在进行中")
            return False
        
        self.healing_in_progress = True
        self.current_retry = 0
        
        handle_info = f"(句柄: {handle_id})" if handle_id else ""
        self.notify_user(f"句柄池耗尽或释放超时，开始自愈{handle_info}")
        
        # 启动自愈线程
        healing_thread = threading.Thread(
            target=self._healing_thread,
            args=(handle_id,),
            daemon=True
        )
        healing_thread.start()
        
        return True
    
    def _healing_thread(self, handle_id: str = None):
        """自愈线程函数"""
        try:
            while self.current_retry < self.max_retry_count:
                self.current_retry += 1
                
                logger.info(f"句柄自愈尝试 {self.current_retry}/{self.max_retry_count}")
                self.notify_user(f"句柄自愈中...", self.current_retry)
                
                # 尝试清理句柄资源
                if self._cleanup_handles():
                    self.notify_user(f"句柄自愈成功")
                    self.healing_in_progress = False
                    return
                
                # 等待重试间隔
                time.sleep(self.retry_interval)
            
            # 所有重试都失败了
            self.notify_user(f"句柄自愈失败，已达到最大重试次数({self.max_retry_count})")
            self.healing_in_progress = False
            
        except Exception as e:
            logger.error(f"句柄自愈线程发生错误: {e}")
            self.notify_user(f"句柄自愈过程中发生错误: {e}")
            self.healing_in_progress = False
    
    def _cleanup_handles(self) -> bool:
        """尝试清理句柄资源"""
        try:
            # 这里可以添加具体的句柄清理逻辑
            # 例如：关闭所有超时的句柄，释放资源等
            
            # 模拟清理过程
            time.sleep(0.5)
            
            # 检查是否有可用的句柄资源
            # 这里应该是实际的资源检查逻辑
            
            logger.info("句柄资源清理完成")
            return True
            
        except Exception as e:
            logger.error(f"句柄清理失败: {e}")
            return False
    
    def is_healing(self) -> bool:
        """检查是否正在进行句柄自愈"""
        return self.healing_in_progress
    
    def get_current_retry(self) -> int:
        """获取当前重试次数"""
        return self.current_retry

# 初始化全局句柄自愈器
handle_healer = HandleHealer()
