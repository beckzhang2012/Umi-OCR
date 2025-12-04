# 增强型文件写入工具，带句柄管理、异常缓存、自动重试和句柄自愈机制

import os
import queue
from typing import List, Callable
from .file_handle_manager import FileHandleManager
from .handle_healer import handle_healer

# 全局文件句柄管理器
file_handle_manager = FileHandleManager()

class FileWriter:
    def __init__(self):
        self.write_queue = queue.Queue()  # 异常时的缓存队列
        self.retry_count = 3  # 最大重试次数
        
    def write_file(self, file_path: str, content: str, mode: str = 'w', encoding: str = 'utf-8') -> bool:
        """带异常处理的文件写入方法"""
        
        for attempt in range(self.retry_count):
            try:
                # 注册文件句柄
                handle_id = f"{file_path}_{mode}"
                
                with file_handle_manager.register_handle(handle_id, file_path):
                    with open(file_path, mode, encoding=encoding) as f:
                        f.write(content)
                        
                # 写入成功，返回True
                return True
                
            except Exception as e:
                print(f"文件写入失败 (尝试 {attempt + 1}/{self.retry_count}): {file_path}")
                print(f"错误信息: {e}")
                
                # 最后一次尝试失败
                if attempt == self.retry_count - 1:
                    # 将内容加入缓存队列
                    self.write_queue.put((file_path, content, mode, encoding))
                    print(f"内容已加入缓存队列: {file_path}")
                    
                    # 触发句柄自愈机制
                    print(f"触发句柄自愈机制...")
                    handle_healer.start_healing(handle_id)
                
                # 等待一段时间后重试
                import time
                time.sleep(0.1 * (attempt + 1))  # 指数退避
                
        return False
    
    def create_file(self, file_path: str) -> bool:
        """带异常处理的文件创建方法"""
        
        for attempt in range(self.retry_count):
            try:
                handle_id = f"create_{file_path}"
                
                with file_handle_manager.register_handle(handle_id, file_path):
                    open(file_path, "w").close()
                    
                return True
                
            except Exception as e:
                print(f"文件创建失败 (尝试 {attempt + 1}/{self.retry_count}): {file_path}")
                print(f"错误信息: {e}")
                
                # 最后一次尝试失败，触发句柄自愈机制
                if attempt == self.retry_count - 1:
                    print(f"触发句柄自愈机制...")
                    handle_healer.start_healing(handle_id)
                
                # 等待一段时间后重试
                import time
                time.sleep(0.1 * (attempt + 1))
                
        return False
    
    def process_queue(self) -> int:
        """处理缓存队列中的内容"""
        processed = 0
        
        while not self.write_queue.empty():
            try:
                file_path, content, mode, encoding = self.write_queue.get_nowait()
                
                if self.write_file(file_path, content, mode, encoding):
                    processed += 1
                    print(f"缓存内容写入成功: {file_path}")
                else:
                    # 再次失败，将内容放回队列
                    self.write_queue.put((file_path, content, mode, encoding))
                    print(f"缓存内容写入失败，已放回队列: {file_path}")
                    break
                    
            except queue.Empty:
                break
            except Exception as e:
                print(f"处理缓存队列时发生错误: {e}")
                break
        
        return processed
    
    def get_queue_size(self) -> int:
        """获取缓存队列的大小"""
        return self.write_queue.qsize()

# 全局文件写入工具
file_writer = FileWriter()
