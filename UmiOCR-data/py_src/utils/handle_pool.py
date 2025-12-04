#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件句柄池监控类
用于监控和管理文件句柄的生命周期，防止句柄泄漏
"""

import os
import time
import threading
from typing import Dict, List, Optional
from umi_log import logger

class HandlePool:
    """文件句柄池监控类"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance
    
    def _init(self):
        self._handles: Dict[str, Dict] = {}  # 句柄字典: {handle_id: {path, mode, create_time, last_access_time, count}}
        self._lock = threading.Lock()
        self._max_handles = 1000  # 最大句柄数限制
        self._cleanup_interval = 60  # 清理间隔（秒）
        self._handle_timeout = 300  # 句柄超时时间（秒）
        self._daemon_thread: Optional[threading.Thread] = None
        self._running = False
        
    def add_handle(self, path: str, mode: str = "r") -> str:
        """添加句柄到监控池，返回句柄ID"""
        handle_id = f"{path}_{mode}_{id(path)}"
        
        with self._lock:
            if handle_id in self._handles:
                # 句柄已存在，更新访问时间
                self._handles[handle_id]["last_access"] = time.time()
                logger.debug(f"句柄已更新: {handle_id} ({path}, {mode})，计数: {self._handles[handle_id]['count']}")
                return handle_id
            
            # 句柄不存在，添加新句柄
            if len(self._handles) >= self._max_handles:
                # 句柄池已满，清理超时句柄
                cleaned_count = self._cleanup_timeout_handles()
                logger.debug(f"句柄池已满，已清理 {cleaned_count} 个超时句柄")
                
                if len(self._handles) >= self._max_handles:
                    # 清理后仍已满，返回None
                    logger.warning(f"句柄池已满，无法添加新句柄: {path} ({mode})")
                    return None
            
            self._handles[handle_id] = {
                "path": path,
                "mode": mode,
                "last_access": time.time(),
                "count": 1
            }
            logger.debug(f"句柄已添加: {handle_id} ({path}, {mode})")
            logger.debug(f"当前句柄池大小: {len(self._handles)}")
            
            return handle_id
    
    def remove_handle(self, handle_id: str):
        """从监控池移除句柄"""
        with self._lock:
            if handle_id in self._handles:
                self._handles[handle_id]["count"] -= 1
                logger.debug(f"句柄引用计数已减少: {handle_id} (当前计数: {self._handles[handle_id]['count']})")
                
                if self._handles[handle_id]["count"] <= 0:
                    del self._handles[handle_id]
                    logger.debug(f"句柄已移除: {handle_id}")
                    logger.debug(f"当前句柄池大小: {len(self._handles)}")
    
    def _cleanup_timeout_handles(self) -> int:
        """清理超时句柄"""
        current_time = time.time()
        timeout_handles = []
        
        with self._lock:
            for handle_id, info in self._handles.items():
                if current_time - info["last_access"] > self._handle_timeout:
                    timeout_handles.append(handle_id)
            
            for handle_id in timeout_handles:
                del self._handles[handle_id]
                logger.warning(f"已清理超时句柄: {handle_id}")
        
        return len(timeout_handles)
    
    def start_daemon(self):
        """启动后台守护线程"""
        if self._running:
            return
            
        self._running = True
        self._daemon_thread = threading.Thread(target=self._daemon_task, daemon=True)
        self._daemon_thread.start()
        logger.info("句柄池守护线程已启动")
    
    def stop_daemon(self):
        """停止后台守护线程"""
        self._running = False
        if self._daemon_thread:
            self._daemon_thread.join(timeout=5)
        logger.info("句柄池守护线程已停止")
    
    def _daemon_task(self):
        """守护线程任务"""
        while self._running:
            try:
                self._cleanup_timeout_handles()
                self._log_handle_stats()
            except Exception as e:
                logger.error(f"句柄池守护线程异常: {e}", exc_info=True)
            
            time.sleep(self._cleanup_interval)
    
    def _log_handle_stats(self):
        """记录句柄统计信息"""
        with self._lock:
            if self._handles:
                logger.info(f"句柄池统计: {len(self._handles)} 个句柄活跃")
                
                # 按路径分组统计
                path_counts: Dict[str, int] = {}
                for info in self._handles.values():
                    path = info["path"]
                    path_counts[path] = path_counts.get(path, 0) + info["count"]
                
                # 记录前5个最活跃的路径
                top_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                for path, count in top_paths:
                    logger.info(f"  {path}: {count} 个句柄")
    
    def get_handle_count(self) -> int:
        """获取当前句柄数量"""
        with self._lock:
            return len(self._handles)
    
    def get_handle_info(self, handle_id: str) -> Optional[Dict]:
        """获取句柄信息"""
        with self._lock:
            return self._handles.get(handle_id)
    
    def get_all_handles(self) -> List[Dict]:
        """获取所有句柄信息"""
        with self._lock:
            handles = []
            for handle_id, info in self._handles.items():
                handles.append({
                    "handle_id": handle_id,
                    "path": info["path"],
                    "mode": info["mode"],
                    "access_time": info["last_access"]
                })
            return handles

# 全局句柄池实例
HandlePoolInstance = HandlePool()