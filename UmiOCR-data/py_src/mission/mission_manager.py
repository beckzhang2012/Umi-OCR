#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR 任务管理器模块
"""

import sys
import os
from PySide6.QtCore import QObject, Signal, Slot, QThreadPool, QRunnable
from typing import List, Dict, Callable

from .mission import Mission
from .mission_queue import MissionQueue


class MissionManager(QObject):
    """任务管理器类，用于管理所有任务的执行"""
    
    # 定义信号
    mission_added = Signal(Mission)  # 任务添加信号
    mission_removed = Signal(Mission)  # 任务移除信号
    mission_started = Signal(Mission)  # 任务开始信号
    mission_completed = Signal(Mission)  # 任务完成信号
    mission_failed = Signal(Mission, str)  # 任务失败信号
    mission_progress_updated = Signal(Mission, int)  # 任务进度更新信号
    
    def __init__(self, event_bus=None):
        super().__init__()
        
        self.event_bus = event_bus
        self.mission_queue = MissionQueue()
        self.thread_pool = QThreadPool.globalInstance()
        
        # 连接信号和槽
        self._connect_signals()
        
        # 注册事件处理函数
        self._register_event_handlers()
    
    def _connect_signals(self):
        """连接信号和槽"""
        # 连接任务队列的信号
        self.mission_queue.mission_added.connect(self.mission_added)
        self.mission_queue.mission_removed.connect(self.mission_removed)
    
    def _register_event_handlers(self):
        """注册事件处理函数"""
        if self.event_bus:
            # 这里可以添加事件处理函数的注册逻辑
            pass
    
    def add_mission(self, mission: Mission):
        """添加任务"""
        # 连接任务的信号
        mission.mission_started.connect(self.mission_started)
        mission.mission_completed.connect(self.mission_completed)
        mission.mission_failed.connect(self.mission_failed)
        mission.mission_progress_updated.connect(self.mission_progress_updated)
        
        # 添加任务到队列
        self.mission_queue.add_mission(mission)
    
    def remove_mission(self, mission: Mission):
        """移除任务"""
        # 移除任务从队列
        self.mission_queue.remove_mission(mission)
    
    def get_missions(self) -> List[Mission]:
        """获取所有任务"""
        return self.mission_queue.get_missions()
    
    def get_mission_by_id(self, mission_id: str) -> Mission:
        """通过ID获取任务"""
        return self.mission_queue.get_mission_by_id(mission_id)
    
    def start_mission(self, mission: Mission):
        """开始任务"""
        if mission in self.mission_queue.get_missions():
            # 将任务提交到线程池执行
            self.thread_pool.start(mission)
        else:
            self.mission_failed.emit(mission, "Mission not found in queue")
    
    def start_all_missions(self):
        """开始所有任务"""
        for mission in self.mission_queue.get_missions():
            self.start_mission(mission)
    
    def stop_mission(self, mission: Mission):
        """停止任务"""
        if mission in self.mission_queue.get_missions():
            mission.stop()
    
    def stop_all_missions(self):
        """停止所有任务"""
        for mission in self.mission_queue.get_missions():
            self.stop_mission(mission)
    
    def clear_missions(self):
        """清除所有任务"""
        # 停止所有任务
        self.stop_all_missions()
        
        # 清除任务队列
        self.mission_queue.clear_missions()
    
    def get_thread_pool_max_threads(self) -> int:
        """获取线程池最大线程数"""
        return self.thread_pool.maxThreadCount()
    
    def set_thread_pool_max_threads(self, max_threads: int):
        """设置线程池最大线程数"""
        self.thread_pool.setMaxThreadCount(max_threads)
    
    def start(self):
        """启动任务管理器"""
        # 这里可以添加启动逻辑
        pass
    
    def stop(self):
        """停止任务管理器"""
        # 停止所有任务
        self.stop_all_missions()
        
        # 清除任务队列
        self.clear_missions()