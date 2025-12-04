#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
文件句柄管理模块

功能：
1. 统一的句柄池监控机制
2. 梳理所有输出路径的句柄生命周期
3. 句柄使用统计和异常检测
4. 句柄强制清理功能

使用方法：
1. 在需要进行文件操作的模块中导入FileHandleManager
2. 使用FileHandleManager.open()代替内置的open()函数
3. 使用FileHandleManager.close()关闭文件句柄
4. 定期调用FileHandleManager.get_stats()获取句柄使用统计
"""

import os
import sys
import time
import threading
import weakref
import psutil
from typing import Dict, List, Optional, Tuple

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from imports import umi_log
from .handle_healer import handle_healer

logger = umi_log.get_logger(__name__)

class FileHandleManager:
    """文件句柄管理类"""
    
    def __init__(self):
        # 句柄池：弱引用字典，键为文件路径，值为(文件对象弱引用, 打开时间, 最后使用时间, 操作类型)
        self._handle_pool: Dict[str, Tuple[weakref.ref, float, float, str]] = {}
        
        # 锁：保护句柄池的线程安全
        self._pool_lock = threading.Lock()
        
        # 异常句柄列表：存储出现异常的句柄信息
        self._exception_handles: List[Dict] = []
        
        # 配置参数
        self._max_handle_count = 100  # 最大句柄数
        self._handle_timeout = 30  # 句柄超时时间（秒）
        self._scan_interval = 60  # 定期扫描间隔（秒）
        
        # 守护线程：定期扫描未关闭的句柄
        self._daemon_thread: Optional[threading.Thread] = None
        self._is_daemon_running = False
        self.start_daemon()
        
        # 统计信息
        self._stats = {
            "total_opened": 0,  # 总共打开的句柄数
            "total_closed": 0,  # 总共关闭的句柄数
            "current_open": 0,  # 当前打开的句柄数
            "exception_count": 0,  # 出现异常的句柄数
            "forced_closed": 0,  # 强制关闭的句柄数
            "max_handles_reached": 0,  # 句柄池满的次数
        }
    
    def start_daemon(self):
        """启动后台守护线程"""
        if not self._is_daemon_running:
            self._is_daemon_running = True
            self._daemon_thread = threading.Thread(target=self._daemon_scan, daemon=True)
            self._daemon_thread.start()
            logger.info("文件句柄管理守护线程已启动")
    
    def stop_daemon(self):
        """停止后台守护线程"""
        if self._is_daemon_running:
            self._is_daemon_running = False
            if self._daemon_thread:
                self._daemon_thread.join(timeout=5)
            logger.info("文件句柄管理守护线程已停止")
    
    def _daemon_scan(self):
        """守护线程扫描逻辑"""
        while self._is_daemon_running:
            try:
                self.scan_unclosed_handles()
                self.check_handle_timeouts()
                # 打印资源统计
                self.print_resource_stats()
            except Exception as e:
                logger.error(f"守护线程扫描异常：{str(e)}")
            
            # 等待扫描间隔
            time.sleep(self._scan_interval)
    
    def print_resource_stats(self):
        """打印资源统计信息"""
        logger.info("句柄资源统计:")
        logger.info(f"  总句柄数: {self._stats['total_opened']}")
        logger.info(f"  活跃句柄数: {self._stats['current_open']}")
        logger.info(f"  超时句柄数: {self._stats['forced_closed']}")
        logger.info(f"  异常句柄数: {self._stats['exception_count']}")
        logger.info(f"  句柄池满次数: {self._stats['max_handles_reached']}")
    
    def get_system_handle_count(self) -> int:
        """获取系统级别的文件句柄数"""
        try:
            process = psutil.Process(os.getpid())
            return process.num_fds()
        except Exception as e:
            logger.error(f"获取系统句柄数失败: {e}")
            return -1
    
    def open(self, file_path: str, mode: str = "r", encoding: Optional[str] = None, **kwargs) -> object:
        """打开文件并将句柄加入管理池"""
        # 检查句柄池是否已满
        if self.get_current_handle_count() >= self._max_handle_count:
            # 尝试清理超时句柄
            self.cleanup_timeout_handles()
            
            # 如果仍然已满，记录异常并触发自愈机制
            if self.get_current_handle_count() >= self._max_handle_count:
                exception_info = {
                    "file_path": file_path,
                    "mode": mode,
                    "error": "句柄池已满",
                    "timestamp": time.time()
                }
                self._exception_handles.append(exception_info)
                self._stats["exception_count"] += 1
                self._stats["max_handles_reached"] += 1
                
                logger.warning(f"句柄池已满 (当前: {self.get_current_handle_count()}, 最大: {self._max_handle_count})")
                # 触发句柄自愈机制
                handle_healer.start_healing()
                
                logger.error(f"打开文件失败：{file_path} - 句柄池已满")
                raise Exception(f"句柄池已满，无法打开文件：{file_path}")
        
        try:
            # 打开文件
            if encoding:
                file_obj = open(file_path, mode, encoding=encoding, **kwargs)
            else:
                file_obj = open(file_path, mode, **kwargs)
            
            # 将句柄加入管理池
            with self._pool_lock:
                self._handle_pool[file_path] = (
                    weakref.ref(file_obj, self._handle_finalizer),
                    time.time(),
                    time.time(),
                    mode[0]  # 操作类型：r(读), w(写), a(追加), etc.
                )
            
            # 更新统计信息
            self._stats["total_opened"] += 1
            self._stats["current_open"] += 1
            
            logger.debug(f"文件已打开并加入管理池：{file_path}，当前句柄数：{self._stats['current_open']}")
            
            return file_obj
            
        except Exception as e:
            exception_info = {
                "file_path": file_path,
                "mode": mode,
                "error": str(e),
                "timestamp": time.time()
            }
            self._exception_handles.append(exception_info)
            self._stats["exception_count"] += 1
            
            logger.error(f"打开文件失败：{file_path} - {str(e)}")
            raise
    
    def close(self, file_obj: object) -> bool:
        """关闭文件并从管理池中移除句柄"""
        try:
            # 获取文件路径
            file_path = file_obj.name
            
            # 关闭文件
            file_obj.close()
            
            # 从管理池中移除句柄
            with self._pool_lock:
                if file_path in self._handle_pool:
                    del self._handle_pool[file_path]
            
            # 更新统计信息
            self._stats["total_closed"] += 1
            self._stats["current_open"] -= 1
            
            logger.debug(f"文件已关闭并从管理池移除：{file_path}，当前句柄数：{self._stats['current_open']}")
            
            return True
            
        except Exception as e:
            logger.error(f"关闭文件失败：{str(e)}")
            return False
    
    def _handle_finalizer(self, weak_ref: weakref.ref):
        """句柄被垃圾回收时的回调函数"""
        # 这个函数会在文件对象被垃圾回收时调用
        # 由于我们使用了弱引用，无法直接获取文件路径
        # 因此，我们需要定期扫描管理池中的弱引用是否已经失效
        pass
    
    def scan_unclosed_handles(self):
        """扫描未关闭的句柄"""
        with self._pool_lock:
            # 复制句柄池的键，避免在遍历过程中修改字典
            file_paths = list(self._handle_pool.keys())
            
            for file_path in file_paths:
                weak_ref, open_time, last_use_time, op_type = self._handle_pool[file_path]
                
                # 检查弱引用是否已经失效（文件对象已被垃圾回收）
                file_obj = weak_ref()
                if file_obj is None:
                    # 弱引用已失效，移除该句柄
                    del self._handle_pool[file_path]
                    
                    # 更新统计信息
                    self._stats["total_closed"] += 1
                    self._stats["current_open"] -= 1
                    self._stats["forced_closed"] += 1
                    
                    logger.info(f"发现未关闭的句柄已被垃圾回收：{file_path}，当前句柄数：{self._stats['current_open']}")
                    
                    # 添加到异常句柄列表
                    self._exception_handles.append({
                        "file_path": file_path,
                        "mode": op_type,
                        "error": "句柄未关闭已被垃圾回收",
                        "timestamp": time.time()
                    })
                    self._stats["exception_count"] += 1
    
    def check_handle_timeouts(self):
        """检查句柄是否超时"""
        current_time = time.time()
        
        with self._pool_lock:
            # 复制句柄池的键，避免在遍历过程中修改字典
            file_paths = list(self._handle_pool.keys())
            
            for file_path in file_paths:
                weak_ref, open_time, last_use_time, op_type = self._handle_pool[file_path]
                
                # 检查句柄是否超时
                if current_time - last_use_time > self._handle_timeout:
                    # 获取文件对象
                    file_obj = weak_ref()
                    
                    if file_obj:
                        try:
                            # 强制关闭文件
                            file_obj.close()
                            logger.info(f"强制关闭超时句柄：{file_path}，打开时间：{current_time - open_time:.2f}秒")
                        except Exception as e:
                            logger.error(f"强制关闭超时句柄失败：{file_path} - {str(e)}")
                    
                    # 从管理池中移除句柄
                    del self._handle_pool[file_path]
                    
                    # 更新统计信息
                    self._stats["total_closed"] += 1
                    self._stats["current_open"] -= 1
                    self._stats["forced_closed"] += 1
                    
                    # 添加到异常句柄列表
                    self._exception_handles.append({
                        "file_path": file_path,
                        "mode": op_type,
                        "error": "句柄超时",
                        "timestamp": time.time()
                    })
                    self._stats["exception_count"] += 1
    
    def cleanup_timeout_handles(self):
        """清理超时的句柄"""
        current_time = time.time()
        cleaned_count = 0
        
        with self._pool_lock:
            # 复制句柄池的键，避免在遍历过程中修改字典
            file_paths = list(self._handle_pool.keys())
            
            for file_path in file_paths:
                weak_ref, open_time, last_use_time, op_type = self._handle_pool[file_path]
                
                # 检查句柄是否超时
                if current_time - last_use_time > self._handle_timeout:
                    # 获取文件对象
                    file_obj = weak_ref()
                    
                    if file_obj:
                        try:
                            # 强制关闭文件
                            file_obj.close()
                            cleaned_count += 1
                        except Exception as e:
                            logger.error(f"清理超时句柄失败：{file_path} - {str(e)}")
                    
                    # 从管理池中移除句柄
                    del self._handle_pool[file_path]
                    
                    # 更新统计信息
                    self._stats["total_closed"] += 1
                    self._stats["current_open"] -= 1
                    self._stats["forced_closed"] += 1
                    
                    # 添加到异常句柄列表
                    self._exception_handles.append({
                        "file_path": file_path,
                        "mode": op_type,
                        "error": "句柄超时已清理",
                        "timestamp": time.time()
                    })
                    self._stats["exception_count"] += 1
        
        if cleaned_count > 0:
            logger.info(f"已清理 {cleaned_count} 个超时句柄，当前句柄数：{self._stats['current_open']}")
    
    def get_current_handle_count(self) -> int:
        """获取当前打开的句柄数"""
        return self._stats["current_open"]
    
    def get_stats(self) -> Dict:
        """获取句柄使用统计信息"""
        # 扫描未关闭的句柄，确保统计信息准确
        self.scan_unclosed_handles()
        
        return {
            "total_opened": self._stats["total_opened"],
            "total_closed": self._stats["total_closed"],
            "current_open": self._stats["current_open"],
            "exception_count": self._stats["exception_count"],
            "forced_closed": self._stats["forced_closed"],
            "max_handles_reached": self._stats["max_handles_reached"],
            "max_handle_count": self._max_handle_count,
            "handle_timeout": self._handle_timeout,
            "system_handle_count": self.get_system_handle_count(),
        }
    
    def get_exception_handles(self) -> List[Dict]:
        """获取出现异常的句柄列表"""
        return self._exception_handles.copy()
    
    def clear_exception_handles(self):
        """清除异常句柄列表"""
        self._exception_handles.clear()

# 创建全局的文件句柄管理器实例
file_handle_manager = FileHandleManager()

# 启动后台守护线程
file_handle_manager.start_daemon()

if __name__ == "__main__":
    # 测试文件句柄管理器
    import tempfile
    
    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file_path = temp_file.name
    temp_file.close()
    
    try:
        # 测试打开文件
        logger.info("测试打开文件...")
        file_obj = file_handle_manager.open(temp_file_path, "w", encoding="utf-8")
        
        # 测试写入文件
        logger.info("测试写入文件...")
        file_obj.write("Hello, World!\n")
        file_obj.write("这是一个测试文件。\n")
        
        # 测试关闭文件
        logger.info("测试关闭文件...")
        file_handle_manager.close(file_obj)
        
        # 测试再次打开文件
        logger.info("测试再次打开文件...")
        file_obj = file_handle_manager.open(temp_file_path, "r", encoding="utf-8")
        
        # 测试读取文件
        logger.info("测试读取文件...")
        content = file_obj.read()
        logger.info(f"文件内容：{content}")
        
        # 不关闭文件，测试守护线程是否会清理
        logger.info("测试不关闭文件，等待守护线程清理...")
        
        # 等待一段时间，让守护线程有机会扫描
        time.sleep(15)
        
        # 查看统计信息
        logger.info("查看统计信息...")
        stats = file_handle_manager.get_stats()
        for key, value in stats.items():
            logger.info(f"{key}: {value}")
        
        # 查看异常句柄列表
        logger.info("查看异常句柄列表...")
        exception_handles = file_handle_manager.get_exception_handles()
        for handle in exception_handles:
            logger.info(f"异常句柄：{handle}")
        
    finally:
        # 删除临时文件
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
        # 停止守护线程
        file_handle_manager.stop_daemon()
        
        logger.info("测试完成。")