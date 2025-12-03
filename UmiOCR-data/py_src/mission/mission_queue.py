#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR 任务队列模块
"""

import sys
import os
from PySide6.QtCore import QObject, Signal
from typing import List, Dict, Callable

from .mission import Mission


class MissionQueue(QObject):
    """任务队列类，用于管理任务的添加、移除和查询"""
    
    # 定义信号
    mission_added = Signal(Mission)  # 任务添加信号
    mission_removed = Signal(Mission)  # 任务移除信号
    
    def __init__(self):
        super().__init__()
        
        self.missions = []  # 任务列表
    
    def add_mission(self, mission: Mission):
        """添加任务"""
        if mission not in self.missions:
            self.missions.append(mission)
            self.mission_added.emit(mission)
    
    def remove_mission(self, mission: Mission):
        """移除任务"""
        if mission in self.missions:
            self.missions.remove(mission)
            self.mission_removed.emit(mission)
    
    def get_missions(self) -> List[Mission]:
        """获取所有任务"""
        return self.missions
    
    def get_mission_by_id(self, mission_id: str) -> Mission:
        """通过ID获取任务"""
        for mission in self.missions:
            if mission.get_mission_id() == mission_id:
                return mission
        return None
    
    def get_missions_by_type(self, mission_type: str) -> List[Mission]:
        """通过类型获取任务列表"""
        return [mission for mission in self.missions if mission.get_mission_type() == mission_type]
    
    def get_running_missions(self) -> List[Mission]:
        """获取正在运行的任务列表"""
        return [mission for mission in self.missions if mission.is_running()]
    
    def get_completed_missions(self) -> List[Mission]:
        """获取已完成的任务列表"""
        return [mission for mission in self.missions if mission.is_completed()]
    
    def get_failed_missions(self) -> List[Mission]:
        """获取失败的任务列表"""
        return [mission for mission in self.missions if mission.is_failed()]
    
    def clear_missions(self):
        """清除所有任务"""
        for mission in self.missions:
            self.remove_mission(mission)
    
    def get_mission_count(self) -> int:
        """获取任务总数"""
        return len(self.missions)
    
    def get_running_mission_count(self) -> int:
        """获取正在运行的任务数"""
        return len(self.get_running_missions())
    
    def get_completed_mission_count(self) -> int:
        """获取已完成的任务数"""
        return len(self.get_completed_missions())
    
    def get_failed_mission_count(self) -> int:
        """获取失败的任务数"""
        return len(self.get_failed_missions())