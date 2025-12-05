#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ===============================================
# ============= 硬件状态UI显示组件 ==============
# ===============================================

import os
import time
import threading
from typing import Optional

from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QGroupBox, QGridLayout,
    QComboBox, QLineEdit
)
from PySide2.QtCore import Qt, QTimer, Signal
from PySide2.QtGui import QFont, QColor, QIcon

from umi_log import logger
from ocr.api.hardware_manager import HardwareManagerGlobal, BackendType, SwitchReason


class HardwareStatusUI(QWidget):
    """硬件状态UI显示组件"""
    
    # 信号定义
    backend_switch_signal = Signal(str, str)  # 当前后端, 切换原因
    
    def __init__(self):
        super().__init__()
        
        self.hardware_manager = HardwareManagerGlobal
        
        # UI组件
        self.current_backend_label: Optional[QLabel] = None
        self.switch_reason_label: Optional[QLabel] = None
        self.expected_recovery_time_label: Optional[QLabel] = None
        self.gpu_devices_group: Optional[QGroupBox] = None
        self.manual_switch_combo: Optional[QComboBox] = None
        
        # 定时器
        self.update_timer: Optional[QTimer] = None
        
        # 初始化UI
        self._init_ui()
        
        # 启动更新定时器
        self._start_update_timer()
        
        # 设置后端切换回调
        self.hardware_manager.set_backend_switch_callback(self._on_backend_switch)
        
        logger.info("硬件状态UI组件已初始化")
    
    def _init_ui(self):
        """初始化UI组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("硬件状态监控")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 状态信息区域
        status_group = QGroupBox("当前状态")
        status_layout = QGridLayout(status_group)
        
        # 当前后端
        status_layout.addWidget(QLabel("当前后端:"), 0, 0)
        self.current_backend_label = QLabel("N/A")
        self.current_backend_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        status_layout.addWidget(self.current_backend_label, 0, 1)
        
        # 切换原因
        status_layout.addWidget(QLabel("切换原因:"), 1, 0)
        self.switch_reason_label = QLabel("N/A")
        status_layout.addWidget(self.switch_reason_label, 1, 1)
        
        # 预计恢复时间
        status_layout.addWidget(QLabel("预计恢复时间:"), 2, 0)
        self.expected_recovery_time_label = QLabel("N/A")
        status_layout.addWidget(self.expected_recovery_time_label, 2, 1)
        
        main_layout.addWidget(status_group)
        
        # GPU设备信息区域
        self.gpu_devices_group = QGroupBox("GPU设备信息")
        self.gpu_devices_layout = QGridLayout(self.gpu_devices_group)
        main_layout.addWidget(self.gpu_devices_group)
        
        # 手动切换区域
        manual_switch_group = QGroupBox("手动切换")
        manual_switch_layout = QHBoxLayout(manual_switch_group)
        
        manual_switch_layout.addWidget(QLabel("切换到:"))
        self.manual_switch_combo = QComboBox()
        self.manual_switch_combo.addItem(BackendType.GPU.value, BackendType.GPU)
        self.manual_switch_combo.addItem(BackendType.CPU.value, BackendType.CPU)
        manual_switch_layout.addWidget(self.manual_switch_combo)
        
        manual_switch_button = QPushButton("切换")
        manual_switch_button.clicked.connect(self._on_manual_switch)
        manual_switch_layout.addWidget(manual_switch_button)
        
        main_layout.addWidget(manual_switch_group)
        
        # 填充剩余空间
        main_layout.addStretch()
        
        # 更新UI数据
        self._update_ui_data()
    
    def _start_update_timer(self):
        """启动更新定时器"""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_ui_data)
        self.update_timer.start(1000)  # 每秒更新一次
    
    def _update_ui_data(self):
        """更新UI数据"""
        # 获取硬件信息
        hardware_info = self.hardware_manager.get_hardware_info()
        
        # 更新当前后端
        current_backend = hardware_info["current_backend"]
        self.current_backend_label.setText(current_backend)
        
        # 设置后端标签颜色
        if current_backend == BackendType.GPU.value:
            self.current_backend_label.setStyleSheet("color: #008000;")  # 绿色
        else:
            self.current_backend_label.setStyleSheet("color: #FFA500;")  # 橙色
        
        # 更新切换原因
        switch_reason = hardware_info["switch_reason"]
        self.switch_reason_label.setText(switch_reason if switch_reason else "N/A")
        
        # 更新预计恢复时间
        expected_recovery_time = hardware_info["expected_recovery_time"]
        if expected_recovery_time:
            recovery_time_str = time.strftime("%H:%M:%S", time.localtime(expected_recovery_time))
            self.expected_recovery_time_label.setText(recovery_time_str)
        else:
            self.expected_recovery_time_label.setText("N/A")
        
        # 更新GPU设备信息
        self._update_gpu_devices_info(hardware_info["gpu"])
    
    def _update_gpu_devices_info(self, gpu_devices):
        """更新GPU设备信息"""
        # 清空之前的GPU设备信息
        while self.gpu_devices_layout.count():
            child = self.gpu_devices_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not gpu_devices:
            # 没有GPU设备
            self.gpu_devices_layout.addWidget(QLabel("未检测到GPU设备"), 0, 0)
            self.gpu_devices_group.setVisible(False)
        else:
            # 有GPU设备，显示设备信息
            self.gpu_devices_group.setVisible(True)
            
            for i, device in enumerate(gpu_devices):
                # 设备名称
                self.gpu_devices_layout.addWidget(QLabel(f"GPU {device['index']}:"), i*2, 0)
                self.gpu_devices_layout.addWidget(QLabel(device["name"]), i*2, 1)
                
                # 显存使用情况
                total_memory = device["total_memory"] / 1024 / 1024 / 1024  # 转换为GB
                used_memory = device["used_memory"] / 1024 / 1024 / 1024  # 转换为GB
                free_memory = device["free_memory"] / 1024 / 1024 / 1024  # 转换为GB
                
                memory_label = QLabel(f"显存: {used_memory:.2f} / {total_memory:.2f} GB")
                self.gpu_devices_layout.addWidget(memory_label, i*2+1, 0)
                
                memory_progress = QProgressBar()
                memory_progress.setRange(0, 100)
                memory_progress.setValue(int((used_memory / total_memory) * 100))
                self.gpu_devices_layout.addWidget(memory_progress, i*2+1, 1)
    
    def _on_backend_switch(self, backend: BackendType, reason: SwitchReason):
        """后端切换回调函数"""
        logger.info(f"后端切换事件: {backend.value}, 原因: {reason.value}")
        
        # 发送后端切换信号
        self.backend_switch_signal.emit(backend.value, reason.value)
        
        # 立即更新UI数据
        self._update_ui_data()
    
    def _on_manual_switch(self):
        """手动切换后端"""
        selected_backend = self.manual_switch_combo.currentData()
        
        if selected_backend:
            logger.info(f"手动切换后端到: {selected_backend.value}")
            self.hardware_manager.switch_to_backend(selected_backend, SwitchReason.MANUAL_SWITCH)
        else:
            logger.warning("未选择有效的后端")
    
    def stop(self):
        """停止硬件状态UI组件"""
        if self.update_timer:
            self.update_timer.stop()
            self.update_timer = None
        
        logger.info("硬件状态UI组件已停止")


# 创建全局硬件状态UI实例
HardwareStatusUIGlobal = HardwareStatusUI()
