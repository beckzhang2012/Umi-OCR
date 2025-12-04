import os
import time
import logging
from contextlib import contextmanager
from .file_handle_manager import file_handle_manager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@contextmanager
def safe_open(file_path, mode='r', encoding=None, errors=None, newline=None, description=''):
    """安全的文件打开上下文管理器，集成句柄管理和异常处理"""
    file_obj = None
    try:
        # 尝试打开文件
        file_obj = open(file_path, mode, encoding=encoding, errors=errors, newline=newline)
        
        # 注册文件句柄
        file_handle_manager.register_handle(file_obj, file_path, mode, description)
        
        yield file_obj
        
    except PermissionError as e:
        logger.error(f"Permission denied when accessing {file_path}: {e}")
        # 将内容添加到待写队列（仅适用于写操作）
        if 'w' in mode or 'a' in mode or 'x' in mode:
            # 这里我们无法获取要写入的内容，需要在调用处处理
            raise
        else:
            raise
    except FileNotFoundError as e:
        logger.error(f"File not found: {file_path}: {e}")
        raise
    except OSError as e:
        logger.error(f"OS error when accessing {file_path}: {e}")
        # 检查是否是句柄相关的错误
        if e.errno in (24, 11):  # Too many open files or Resource temporarily unavailable
            logger.warning(f"File handle limit reached for {file_path}, adding to pending queue")
            # 将内容添加到待写队列（仅适用于写操作）
            if 'w' in mode or 'a' in mode or 'x' in mode:
                # 这里我们无法获取要写入的内容，需要在调用处处理
                raise
            else:
                raise
        else:
            raise
    finally:
        if file_obj:
            # 关闭文件并注销句柄
            try:
                file_obj.close()
            except Exception as e:
                logger.error(f"Error closing file {file_path}: {e}")
            finally:
                file_handle_manager.unregister_handle(file_obj)

def safe_write(file_path, content, mode='w', encoding='utf-8', description='', retry_on_failure=True):
    """安全的文件写入函数，支持自动重试和队列缓存"""
    attempts = 0
    max_attempts = 3 if retry_on_failure else 1
    
    while attempts < max_attempts:
        try:
            with safe_open(file_path, mode, encoding=encoding, description=description) as f:
                f.write(content)
            file_handle_manager._stats['write_successes'] += 1
            return True
        except Exception as e:
            attempts += 1
            logger.warning(f"Write attempt {attempts}/{max_attempts} failed for {file_path}: {e}")
            
            if attempts >= max_attempts:
                logger.error(f"All write attempts failed for {file_path}")
                file_handle_manager._stats['write_failures'] += 1
                
                # 如果启用重试，将内容添加到待写队列
                if retry_on_failure and ('w' in mode or 'a' in mode):
                    file_handle_manager.add_pending_write(file_path, content, mode, encoding)
                    return False
                else:
                    raise
            
            # 等待一段时间后重试
            time.sleep(0.1 * attempts)  # 指数退避
    
    return False

def safe_read(file_path, encoding='utf-8', description=''):
    """安全的文件读取函数"""
    try:
        with safe_open(file_path, 'r', encoding=encoding, description=description) as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise

def ensure_directory_exists(file_path):
    """确保文件所在的目录存在"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            return False
    return True
