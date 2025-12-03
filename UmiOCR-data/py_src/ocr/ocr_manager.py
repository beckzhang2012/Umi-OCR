#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR OCR管理器模块
"""

import sys
import os
from PySide6.QtCore import QObject, Signal, Slot, QThreadPool, QRunnable
from typing import List, Dict, Any, Callable

from .api import OCR_API
from .output import OCR_Output
from .tbpu import TBPU_API


class OCRManager(QObject):
    """OCR管理器类，用于管理OCR任务的执行"""
    
    # 定义信号
    ocr_task_added = Signal(str)  # OCR任务添加信号
    ocr_task_removed = Signal(str)  # OCR任务移除信号
    ocr_task_started = Signal(str)  # OCR任务开始信号
    ocr_task_completed = Signal(str, Dict[str, Any])  # OCR任务完成信号
    ocr_task_failed = Signal(str, str)  # OCR任务失败信号
    ocr_task_progress_updated = Signal(str, int)  # OCR任务进度更新信号
    
    def __init__(self, event_bus=None):
        super().__init__()
        
        self.event_bus = event_bus
        self.ocr_api = OCR_API()
        self.ocr_output = OCR_Output()
        self.tbpu_api = TBPU_API()
        
        self.thread_pool = QThreadPool.globalInstance()
        self.ocr_tasks = {}  # OCR任务字典，key: 任务ID，value: 任务数据
        
        # 连接信号和槽
        self._connect_signals()
        
        # 注册事件处理函数
        self._register_event_handlers()
    
    def _connect_signals(self):
        """连接信号和槽"""
        # 这里可以添加信号和槽的连接逻辑
        pass
    
    def _register_event_handlers(self):
        """注册事件处理函数"""
        if self.event_bus:
            # 这里可以添加事件处理函数的注册逻辑
            pass
    
    def add_ocr_task(self, task_id: str, image_path: str, ocr_params: Dict[str, Any] = None):
        """添加OCR任务"""
        if ocr_params is None:
            ocr_params = {}
        
        # 检查任务ID是否已经存在
        if task_id in self.ocr_tasks:
            self.ocr_task_failed.emit(task_id, "Task ID already exists")
            return
        
        # 创建OCR任务数据
        task_data = {
            "task_id": task_id,
            "image_path": image_path,
            "ocr_params": ocr_params,
            "is_running": False,
            "is_completed": False,
            "is_failed": False,
            "error_message": "",
            "progress": 0,
            "result": None
        }
        
        # 添加OCR任务到字典
        self.ocr_tasks[task_id] = task_data
        
        # 发送任务添加信号
        self.ocr_task_added.emit(task_id)
    
    def remove_ocr_task(self, task_id: str):
        """移除OCR任务"""
        # 检查任务ID是否存在
        if task_id not in self.ocr_tasks:
            self.ocr_task_failed.emit(task_id, "Task ID not found")
            return
        
        # 获取任务数据
        task_data = self.ocr_tasks[task_id]
        
        # 检查任务是否正在运行
        if task_data["is_running"]:
            self.ocr_task_failed.emit(task_id, "Task is running, cannot remove")
            return
        
        # 移除OCR任务从字典
        del self.ocr_tasks[task_id]
        
        # 发送任务移除信号
        self.ocr_task_removed.emit(task_id)
    
    def start_ocr_task(self, task_id: str):
        """开始OCR任务"""
        # 检查任务ID是否存在
        if task_id not in self.ocr_tasks:
            self.ocr_task_failed.emit(task_id, "Task ID not found")
            return
        
        # 获取任务数据
        task_data = self.ocr_tasks[task_id]
        
        # 检查任务是否正在运行
        if task_data["is_running"]:
            self.ocr_task_failed.emit(task_id, "Task is already running")
            return
        
        # 检查任务是否已经完成
        if task_data["is_completed"]:
            self.ocr_task_failed.emit(task_id, "Task has already completed")
            return
        
        # 检查任务是否已经失败
        if task_data["is_failed"]:
            # 重置任务状态
            task_data["is_failed"] = False
            task_data["error_message"] = ""
            task_data["progress"] = 0
            task_data["result"] = None
        
        # 设置任务状态为运行中
        task_data["is_running"] = True
        
        # 发送任务开始信号
        self.ocr_task_started.emit(task_id)
        
        # 创建OCR任务线程
        ocr_task_thread = OCRTaskThread(
            task_id,
            task_data["image_path"],
            task_data["ocr_params"],
            self.ocr_api,
            self.tbpu_api,
            self._update_ocr_task_progress,
            self._complete_ocr_task,
            self._fail_ocr_task
        )
        
        # 将任务提交到线程池执行
        self.thread_pool.start(ocr_task_thread)
    
    def stop_ocr_task(self, task_id: str):
        """停止OCR任务"""
        # 检查任务ID是否存在
        if task_id not in self.ocr_tasks:
            self.ocr_task_failed.emit(task_id, "Task ID not found")
            return
        
        # 获取任务数据
        task_data = self.ocr_tasks[task_id]
        
        # 检查任务是否正在运行
        if not task_data["is_running"]:
            self.ocr_task_failed.emit(task_id, "Task is not running")
            return
        
        # 这里可以添加停止OCR任务的逻辑
        # 由于OCR任务是在另一个线程中执行的，所以需要一种方式来停止它
        # 一种可能的方式是设置一个标志，然后在OCR任务执行过程中检查这个标志
    
    def get_ocr_task(self, task_id: str) -> Dict[str, Any]:
        """获取OCR任务数据"""
        return self.ocr_tasks.get(task_id, None)
    
    def get_all_ocr_tasks(self) -> List[Dict[str, Any]]:
        """获取所有OCR任务数据"""
        return list(self.ocr_tasks.values())
    
    def _update_ocr_task_progress(self, task_id: str, progress: int):
        """更新OCR任务进度"""
        # 检查任务ID是否存在
        if task_id not in self.ocr_tasks:
            return
        
        # 获取任务数据
        task_data = self.ocr_tasks[task_id]
        
        # 设置任务进度
        task_data["progress"] = progress
        
        # 发送任务进度更新信号
        self.ocr_task_progress_updated.emit(task_id, progress)
    
    def _complete_ocr_task(self, task_id: str, result: Dict[str, Any]):
        """完成OCR任务"""
        # 检查任务ID是否存在
        if task_id not in self.ocr_tasks:
            return
        
        # 获取任务数据
        task_data = self.ocr_tasks[task_id]
        
        # 设置任务状态为已完成
        task_data["is_running"] = False
        task_data["is_completed"] = True
        task_data["progress"] = 100
        task_data["result"] = result
        
        # 发送任务完成信号
        self.ocr_task_completed.emit(task_id, result)
    
    def _fail_ocr_task(self, task_id: str, error_message: str):
        """失败OCR任务"""
        # 检查任务ID是否存在
        if task_id not in self.ocr_tasks:
            return
        
        # 获取任务数据
        task_data = self.ocr_tasks[task_id]
        
        # 设置任务状态为失败
        task_data["is_running"] = False
        task_data["is_failed"] = True
        task_data["error_message"] = error_message
        
        # 发送任务失败信号
        self.ocr_task_failed.emit(task_id, error_message)
    
    def start(self):
        """启动OCR管理器"""
        # 这里可以添加启动逻辑
        pass
    
    def stop(self):
        """停止OCR管理器"""
        # 停止所有OCR任务
        for task_id in self.ocr_tasks:
            self.stop_ocr_task(task_id)
        
        # 清空OCR任务字典
        self.ocr_tasks.clear()


class OCRTaskThread(QRunnable):
    """OCR任务线程类，用于在后台执行OCR任务"""
    
    def __init__(self, task_id: str, image_path: str, ocr_params: Dict[str, Any], ocr_api: OCR_API, 
                 tbpu_api: TBPU_API, update_progress_callback: Callable[[str, int], None], 
                 complete_callback: Callable[[str, Dict[str, Any]], None], 
                 fail_callback: Callable[[str, str], None]):
        super().__init__()
        
        self.task_id = task_id
        self.image_path = image_path
        self.ocr_params = ocr_params
        self.ocr_api = ocr_api
        self.tbpu_api = tbpu_api
        self.update_progress_callback = update_progress_callback
        self.complete_callback = complete_callback
        self.fail_callback = fail_callback
    
    def run(self):
        """OCR任务执行方法"""
        try:
            # 更新进度为10%（开始）
            self.update_progress_callback(self.task_id, 10)
            
            # 检查图像文件是否存在
            if not os.path.exists(self.image_path):
                raise FileNotFoundError(f"Image file not found: {self.image_path}")
            
            # 更新进度为20%（图像文件检查完成）
            self.update_progress_callback(self.task_id, 20)
            
            # 执行OCR识别
            ocr_result = self.ocr_api.recognize(self.image_path, self.ocr_params)
            
            # 更新进度为50%（OCR识别完成）
            self.update_progress_callback(self.task_id, 50)
            
            # 执行TBPU处理（如果需要）
            if self.ocr_params.get("tbpu_enabled", False):
                tbpu_result = self.tbpu_api.process(ocr_result, self.ocr_params)
                
                # 更新进度为80%（TBPU处理完成）
                self.update_progress_callback(self.task_id, 80)
            else:
                tbpu_result = ocr_result
            
            # 更新进度为90%（结果处理完成）
            self.update_progress_callback(self.task_id, 90)
            
            # 整理最终结果
            final_result = {
                "ocr_result": ocr_result,
                "tbpu_result": tbpu_result
            }
            
            # 更新进度为100%（任务完成）
            self.update_progress_callback(self.task_id, 100)
            
            # 调用完成回调函数
            self.complete_callback(self.task_id, final_result)
        except Exception as e:
            # 调用失败回调函数
            self.fail_callback(self.task_id, str(e))