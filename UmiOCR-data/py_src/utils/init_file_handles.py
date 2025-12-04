"""初始化文件句柄管理系统"""
import atexit
from umi_log import logger
from .file_handle_manager import file_handle_manager
from .ui_notifier import ui_notifier

_initialized = False

def init_file_handle_system():
    """初始化文件句柄管理系统"""
    global _initialized
    
    if _initialized:
        return
    
    try:
        # 启动文件句柄监控器
        file_handle_manager.start_monitoring(interval=5)
        logger.info("File handle manager started")
        
        # 启动UI通知器
        ui_notifier.start_auto_notification(interval=10)
        logger.info("UI notifier started")
        
        # 注册退出时的清理函数
        atexit.register(cleanup_file_handle_system)
        
        _initialized = True
        logger.info("File handle management system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize file handle management system: {e}")
        raise

def cleanup_file_handle_system():
    """清理文件句柄管理系统"""
    global _initialized
    
    if not _initialized:
        return
    
    try:
        # 停止监控器
        file_handle_manager.stop_monitoring()
        logger.info("File handle manager stopped")
        
        # 停止UI通知器
        ui_notifier.stop_auto_notification()
        logger.info("UI notifier stopped")
        
        # 重试所有待写内容
        if file_handle_manager._pending_writes:
            logger.info("Writing pending files before exit...")
            file_handle_manager.retry_pending_writes()
        
        # 打印最终统计
        stats = file_handle_manager.get_stats()
        logger.info(f"Final file handle stats: {stats}")
        
    except Exception as e:
        logger.error(f"Error during cleanup of file handle system: {e}")
    
    finally:
        _initialized = False

def get_file_handle_stats():
    """获取文件句柄统计信息"""
    if not _initialized:
        init_file_handle_system()
    
    return file_handle_manager.get_stats()

def get_active_handles():
    """获取活跃文件句柄信息"""
    if not _initialized:
        init_file_handle_system()
    
    return file_handle_manager.get_active_handles()

def get_pending_writes_count():
    """获取待写内容数量"""
    if not _initialized:
        init_file_handle_system()
    
    return file_handle_manager._stats['pending_writes']

# 自动初始化
if not _initialized:
    try:
        init_file_handle_system()
    except Exception as e:
        logger.error(f"Auto-initialization of file handle system failed: {e}")
