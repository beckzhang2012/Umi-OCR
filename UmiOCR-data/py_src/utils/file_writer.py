#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全文件写入器类
用于优化文件写入逻辑，包括异常缓存和重写机制
"""

import os
import time
import threading
from typing import Dict, List, Optional, Callable
from umi_log import logger
from .handle_pool import HandlePoolInstance

class SafeFileWriter:
    """安全文件写入器类"""
    
    def __init__(self, path: str, mode: str = "w", encoding: str = "utf-8", 
                 max_retries: int = 3, retry_delay: float = 1.0, 
                 buffer_size: int = 1000):
        self._path = path
        self._mode = mode
        self._encoding = encoding
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._buffer_size = buffer_size
        
        self._buffer: List[str] = []  # 写入缓冲区
        self._lock = threading.Lock()
        self._handle_id: Optional[str] = None
        self._file = None
        
        # 初始化句柄监控
        self._handle_id = HandlePoolInstance.add_handle(path, mode)
        
    def write(self, content: str, flush: bool = False):
        """写入内容到文件"""
        with self._lock:
            self._buffer.append(content)
            
            # 如果缓冲区已满或需要立即刷新
            if flush or len(self._buffer) >= self._buffer_size:
                self._flush_buffer()
    
    def _flush_buffer(self):
        """刷新缓冲区到文件"""
        if not self._buffer:
            return
            
        content = "".join(self._buffer)
        self._buffer = []
        
        for retry in range(self._max_retries):
            try:
                with open(self._path, self._mode, encoding=self._encoding) as f:
                    f.write(content)
                
                # 更新句柄访问时间
                HandlePoolInstance.add_handle(self._path, self._mode)
                
                logger.debug(f"文件写入成功: {self._path} (重试: {retry})")
                return
                
            except Exception as e:
                logger.warning(f"文件写入失败 (重试 {retry + 1}/{self._max_retries}): {self._path} - {e}")
                
                if retry < self._max_retries - 1:
                    time.sleep(self._retry_delay)
                    continue
                
                # 所有重试都失败，缓存内容并触发自愈
                logger.error(f"文件写入最终失败: {self._path} - {e}")
                self._buffer.insert(0, content)  # 将内容放回缓冲区
                self._trigger_self_healing()
                raise
    
    def _trigger_self_healing(self):
        """触发句柄自愈机制"""
        logger.warning(f"触发句柄自愈: {self._path}")
        
        # 清理超时句柄
        HandlePoolInstance._cleanup_timeout_handles()
        
        # 通知UI和托盘
        try:
            from ..tag_pages.page import Page
            Page().callQmlInMain("onHandleSelfHealing", self._path, len(self._buffer))
        except Exception as e:
            logger.warning(f"无法通知UI自愈状态: {e}")
    
    def flush(self):
        """立即刷新缓冲区"""
        with self._lock:
            self._flush_buffer()
    
    def close(self):
        """关闭文件写入器"""
        with self._lock:
            self._flush_buffer()
            
            # 移除句柄监控
            if self._handle_id:
                HandlePoolInstance.remove_handle(self._handle_id)
                self._handle_id = None
                logger.debug(f"文件写入器已关闭: {self._path}")
    
    def __enter__(self):
        """上下文管理器进入"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
    
    def __del__(self):
        """析构函数"""
        self.close()

class FileWriterFactory:
    """文件写入器工厂类"""
    
    _writers: Dict[str, SafeFileWriter] = {}
    _lock = threading.Lock()
    
    @staticmethod
    def get_writer(path: str, mode: str = "w", encoding: str = "utf-8", 
                   max_retries: int = 3, retry_delay: float = 1.0, 
                   buffer_size: int = 1000) -> SafeFileWriter:
        """获取或创建文件写入器"""
        key = f"{path}_{mode}_{encoding}"
        
        with FileWriterFactory._lock:
            if key not in FileWriterFactory._writers:
                FileWriterFactory._writers[key] = SafeFileWriter(
                    path, mode, encoding, max_retries, retry_delay, buffer_size
                )
            
            return FileWriterFactory._writers[key]
    
    @staticmethod
    def close_writer(path: str, mode: str = "w", encoding: str = "utf-8"):
        """关闭文件写入器"""
        key = f"{path}_{mode}_{encoding}"
        
        with FileWriterFactory._lock:
            if key in FileWriterFactory._writers:
                FileWriterFactory._writers[key].close()
                del FileWriterFactory._writers[key]
    
    @staticmethod
    def close_all_writers():
        """关闭所有文件写入器"""
        with FileWriterFactory._lock:
            for writer in FileWriterFactory._writers.values():
                writer.close()
            FileWriterFactory._writers.clear()