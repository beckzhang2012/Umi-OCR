#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
句柄扫描守护线程类
用于定期扫描未关闭句柄并触发强制清理
"""

import threading
import time
from typing import Optional
from umi_log import logger
from .handle_pool import HandlePoolInstance

class HandleScanner:
    """句柄扫描守护线程类"""
    
    _instance: Optional['HandleScanner'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化句柄扫描器"""
        if self._initialized:
            return
            
        self._initialized = True
        self._scanner_thread: Optional[threading.Thread] = None
        self._running = False
        self._scan_interval = 60  # 扫描间隔（秒）
        self._timeout_threshold = 300  # 超时阈值（秒）
    
    def start(self, scan_interval: int = 60, timeout_threshold: int = 300):
        """启动句柄扫描器"""
        if self._running:
            logger.warning("句柄扫描器已在运行中")
            return
            
        self._scan_interval = scan_interval
        self._timeout_threshold = timeout_threshold
        self._running = True
        
        self._scanner_thread = threading.Thread(
            target=self._scan_loop,
            name="HandleScannerThread",
            daemon=True
        )
        self._scanner_thread.start()
        
        logger.info(f"句柄扫描器已启动，扫描间隔: {scan_interval}秒，超时阈值: {timeout_threshold}秒")
    
    def stop(self):
        """停止句柄扫描器"""
        if not self._running:
            return
            
        self._running = False
        if self._scanner_thread:
            self._scanner_thread.join(timeout=5)
        
        logger.info("句柄扫描器已停止")
    
    def _scan_loop(self):
        """扫描循环"""
        while self._running:
            try:
                self._scan_handles()
            except Exception as e:
                logger.error(f"句柄扫描器异常: {e}")
            
            # 等待下一次扫描
            for _ in range(self._scan_interval):
                if not self._running:
                    break
                time.sleep(1)
    
    def _scan_handles(self):
        """扫描未关闭句柄"""
        logger.debug("开始扫描未关闭句柄...")
        
        # 获取所有句柄
        handles = HandlePoolInstance.get_all_handles()
        
        if not handles:
            logger.debug("没有找到未关闭句柄")
            return
            
        logger.info(f"扫描到 {len(handles)} 个句柄")
        
        # 检查超时句柄
        current_time = time.time()
        timeout_handles = []
        
        for handle in handles:
            handle_id = handle["handle_id"]
            path = handle["path"]
            mode = handle["mode"]
            access_time = handle["access_time"]
            
            age = current_time - access_time
            
            if age > self._timeout_threshold:
                timeout_handles.append(handle)
                logger.warning(f"发现超时句柄: {path} (模式: {mode}, 超时: {age:.1f}秒)")
            else:
                logger.debug(f"句柄正常: {path} (模式: {mode}, 年龄: {age:.1f}秒)")
        
        # 清理超时句柄
        if timeout_handles:
            logger.warning(f"开始清理 {len(timeout_handles)} 个超时句柄...")
            cleaned_count = HandlePoolInstance._cleanup_timeout_handles()
            logger.info(f"已清理 {cleaned_count} 个超时句柄")
        
        # 统计句柄信息
        total_count = len(handles)
        timeout_count = len(timeout_handles)
        
        logger.info(f"句柄扫描完成: 总句柄数={total_count}, 超时句柄数={timeout_count}")
        
        # 通知UI统计信息
        self._notify_ui_statistics(total_count, timeout_count)
    
    def _notify_ui_statistics(self, total_count: int, timeout_count: int):
        """通知UI句柄统计信息"""
        try:
            from ..tag_pages.page import Page
            Page().callQmlInMain("onHandleStatistics", total_count, timeout_count)
        except Exception as e:
            logger.warning(f"无法通知UI句柄统计信息: {e}")

# 创建全局句柄扫描器实例
HandleScannerInstance = HandleScanner()