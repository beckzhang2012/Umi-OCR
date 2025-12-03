#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR 任务基类模块
"""

import sys
import os
from PySide6.QtCore import QObject, Signal, Slot, QRunnable
from typing import Dict, Any


class Mission(QRunnable):
    """任务基类，所有具体任务类都应该继承自这个类"""
    
    # 定义信号
    mission_started = Signal(object)  # 任务开始信号
    mission_completed = Signal(object)  # 任务完成信号
    mission_failed = Signal(object, str)  # 任务失败信号
    mission_progress_updated = Signal(object, int)  # 任务进度更新信号
    
    def __init__(self, mission_id: str, mission_type: str, mission_data: Dict[str, Any]):
        super().__init__()
        
        self.mission_id = mission_id  # 任务ID
        self.mission_type = mission_type  # 任务类型
        self.mission_data = mission_data  # 任务数据
        
        self.is_running = False  # 任务是否正在运行
        self.is_completed = False  # 任务是否完成
        self.is_failed = False  # 任务是否失败
        self.error_message = ""  # 错误消息
        self.progress = 0  # 任务进度 (0-100)
    
    def run(self):
        """任务执行方法，需要在子类中实现"""
        try:
            self.is_running = True
            self.mission_started.emit(self)
            
            # 这里是任务执行的具体逻辑，需要在子类中实现
            self._execute()
            
            self.is_running = False
            self.is_completed = True
            self.progress = 100
            self.mission_completed.emit(self)
        except Exception as e:
            self.is_running = False
            self.is_failed = True
            self.error_message = str(e)
            self.mission_failed.emit(self, self.error_message)
    
    def _execute(self):
        """任务执行的具体逻辑，需要在子类中实现"""
        raise NotImplementedError("_execute() method must be implemented in subclass")
    
    def stop(self):
        """停止任务"""
        self.is_running = False
    
    def get_mission_id(self) -> str:
        """获取任务ID"""
        return self.mission_id
    
    def get_mission_type(self) -> str:
        """获取任务类型"""
        return self.mission_type
    
    def get_mission_data(self) -> Dict[str, Any]:
        """获取任务数据"""
        return self.mission_data
    
    def is_running(self) -> bool:
        """检查任务是否正在运行"""
        return self.is_running
    
    def is_completed(self) -> bool:
        """检查任务是否完成"""
        return self.is_completed
    
    def is_failed(self) -> bool:
        """检查任务是否失败"""
        return self.is_failed
    
    def get_error_message(self) -> str:
        """获取错误消息"""
        return self.error_message
    
    def get_progress(self) -> int:
        """获取任务进度"""
        return self.progress
    
    def set_progress(self, progress: int):
        """设置任务进度"""
        if 0 <= progress <= 100:
            self.progress = progress
            self.mission_progress_updated.emit(self, self.progress)