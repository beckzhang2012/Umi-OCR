#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ===============================================
# ============= 吞吐量监测UI组件 ================
# ===============================================

import os
import time
import threading
from typing import Optional

from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QGroupBox, QGridLayout, QSplitter, QTabWidget
)
from PySide2.QtCore import Qt, QTimer, Signal
from PySide2.QtGui import QFont, QColor, QIcon

from umi_log import logger
from monitor.throughput_monitor import ThroughputMonitorGlobal
from monitor.hardware_status_ui import HardwareStatusUIGlobal


class ThroughputMonitorUI(QWidget):
    """吞吐量监测UI组件"""
    
    def __init__(self):
        super().__init__()
        
        self.throughput_monitor = ThroughputMonitorGlobal
        
        # UI组件
        self.real_time_panel: Optional[QGroupBox] = None
        self.chart_splitter: Optional[QSplitter] = None
        self.history_table_group: Optional[QGroupBox] = None
        
        # 定时器
        self.update_timer: Optional[QTimer] = None
        
        # 初始化UI
        self._init_ui()
        
        # 启动更新定时器
        self._start_update_timer()
        
        logger.info("吞吐量监测UI组件已初始化")
    
    def _init_ui(self):
        """初始化UI组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("系统监控中心")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 标签页控件
        self.tab_widget = QTabWidget()
        
        # 吞吐量监测标签页
        throughput_tab = QWidget()
        throughput_layout = QVBoxLayout(throughput_tab)
        
        # 实时数据面板
        self._init_real_time_panel()
        throughput_layout.addWidget(self.real_time_panel)
        
        # 图表区域
        self._init_chart_area()
        throughput_layout.addWidget(self.chart_splitter)
        
        # 历史数据表格
        self._init_history_table()
        throughput_layout.addWidget(self.history_table_group)
        
        self.tab_widget.addTab(throughput_tab, "吞吐量监测")
        
        # 硬件状态监控标签页
        hardware_tab = QWidget()
        hardware_layout = QVBoxLayout(hardware_tab)
        hardware_layout.addWidget(HardwareStatusUIGlobal)
        
        self.tab_widget.addTab(hardware_tab, "硬件状态监控")
        
        main_layout.addWidget(self.tab_widget)
        
        # 控制按钮
        self._init_control_buttons()
        main_layout.addLayout(self.control_layout)
    
    def _init_real_time_panel(self):
        """初始化实时数据面板"""
        self.real_time_panel = QGroupBox("实时数据")
        real_time_layout = QGridLayout(self.real_time_panel)
        
        # 吞吐量
        real_time_layout.addWidget(QLabel("吞吐量:"), 0, 0)
        self.throughput_label = QLabel("0.00 任务/秒")
        self.throughput_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        real_time_layout.addWidget(self.throughput_label, 0, 1)
        
        # 平均处理时间
        real_time_layout.addWidget(QLabel("平均处理时间:"), 1, 0)
        self.average_time_label = QLabel("0.00 秒")
        real_time_layout.addWidget(self.average_time_label, 1, 1)
        
        # 平均等待时间
        real_time_layout.addWidget(QLabel("平均等待时间:"), 2, 0)
        self.average_wait_label = QLabel("0.00 秒")
        real_time_layout.addWidget(self.average_wait_label, 2, 1)
        
        # 活跃线程数
        real_time_layout.addWidget(QLabel("活跃线程数:"), 0, 2)
        self.active_threads_label = QLabel("0")
        real_time_layout.addWidget(self.active_threads_label, 0, 3)
        
        # 队列长度
        real_time_layout.addWidget(QLabel("队列长度:"), 1, 2)
        self.queue_length_label = QLabel("0")
        real_time_layout.addWidget(self.queue_length_label, 1, 3)
        
        # 累计任务数
        real_time_layout.addWidget(QLabel("累计任务数:"), 2, 2)
        self.total_tasks_label = QLabel("0")
        real_time_layout.addWidget(self.total_tasks_label, 2, 3)
    
    def _init_chart_area(self):
        """初始化图表区域"""
        self.chart_splitter = QSplitter(Qt.Vertical)
        
        # 吞吐量图表
        throughput_chart_group = QGroupBox("吞吐量趋势")
        throughput_chart_layout = QVBoxLayout(throughput_chart_group)
        self.throughput_chart = ThroughputChart()
        throughput_chart_layout.addWidget(self.throughput_chart)
        self.chart_splitter.addWidget(throughput_chart_group)
        
        # 处理时间图表
        processing_time_chart_group = QGroupBox("处理时间趋势")
        processing_time_chart_layout = QVBoxLayout(processing_time_chart_group)
        self.processing_time_chart = ThroughputChart()
        processing_time_chart_layout.addWidget(self.processing_time_chart)
        self.chart_splitter.addWidget(processing_time_chart_group)
        
        # 等待时间图表
        waiting_time_chart_group = QGroupBox("等待时间趋势")
        waiting_time_chart_layout = QVBoxLayout(waiting_time_chart_group)
        self.waiting_time_chart = ThroughputChart()
        waiting_time_chart_layout.addWidget(self.waiting_time_chart)
        self.chart_splitter.addWidget(waiting_time_chart_group)
    
    def _init_history_table(self):
        """初始化历史数据表格"""
        self.history_table_group = QGroupBox("历史数据")
        history_table_layout = QVBoxLayout(self.history_table_group)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "时间", "吞吐量", "平均处理时间", "平均等待时间", "活跃线程数", "队列长度"
        ])
        
        # 设置列宽
        self.history_table.setColumnWidth(0, 150)
        self.history_table.setColumnWidth(1, 100)
        self.history_table.setColumnWidth(2, 120)
        self.history_table.setColumnWidth(3, 120)
        self.history_table.setColumnWidth(4, 100)
        self.history_table.setColumnWidth(5, 100)
        
        history_table_layout.addWidget(self.history_table)
    
    def _init_control_buttons(self):
        """初始化控制按钮"""
        self.control_layout = QHBoxLayout()
        
        # 清空历史数据按钮
        clear_button = QPushButton("清空历史数据")
        clear_button.clicked.connect(self._on_clear_history)
        self.control_layout.addWidget(clear_button)
        
        # 导出数据按钮
        export_button = QPushButton("导出数据")
        export_button.clicked.connect(self._on_export_data)
        self.control_layout.addWidget(export_button)
        
        # 填充剩余空间
        self.control_layout.addStretch()
    
    def _start_update_timer(self):
        """启动更新定时器"""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_ui_data)
        self.update_timer.start(1000)  # 每秒更新一次
    
    def _update_ui_data(self):
        """更新UI数据"""
        # 获取实时统计数据
        real_time_stats = self.throughput_monitor.get_real_time_stats()
        
        # 更新实时数据面板
        self.throughput_label.setText(f"{real_time_stats['throughput']:.2f} 任务/秒")
        self.average_time_label.setText(f"{real_time_stats['average_processing_time']:.2f} 秒")
        self.average_wait_label.setText(f"{real_time_stats['average_waiting_time']:.2f} 秒")
        self.active_threads_label.setText(str(real_time_stats['active_threads']))
        self.queue_length_label.setText(str(real_time_stats['queue_length']))
        self.total_tasks_label.setText(str(real_time_stats['total_tasks']))
        
        # 更新图表数据
        current_time = time.time()
        self.throughput_chart.add_data_point(current_time, real_time_stats['throughput'])
        self.processing_time_chart.add_data_point(current_time, real_time_stats['average_processing_time'])
        self.waiting_time_chart.add_data_point(current_time, real_time_stats['average_waiting_time'])
        
        # 更新历史数据表格
        self._update_history_table_data()
    
    def _update_history_table_data(self):
        """更新历史数据表格"""
        # 获取历史统计数据
        history_stats = self.throughput_monitor.get_history_stats()
        
        # 清空表格
        self.history_table.setRowCount(0)
        
        # 添加历史数据
        for stats in reversed(history_stats):
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            
            # 时间
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stats['timestamp']))
            self.history_table.setItem(row, 0, QTableWidgetItem(time_str))
            
            # 吞吐量
            self.history_table.setItem(row, 1, QTableWidgetItem(f"{stats['throughput']:.2f}"))
            
            # 平均处理时间
            self.history_table.setItem(row, 2, QTableWidgetItem(f"{stats['average_processing_time']:.2f}"))
            
            # 平均等待时间
            self.history_table.setItem(row, 3, QTableWidgetItem(f"{stats['average_waiting_time']:.2f}"))
            
            # 活跃线程数
            self.history_table.setItem(row, 4, QTableWidgetItem(str(stats['active_threads'])))
            
            # 队列长度
            self.history_table.setItem(row, 5, QTableWidgetItem(str(stats['queue_length'])))
    
    def _on_clear_history(self):
        """清空历史数据"""
        self.throughput_monitor.clear_history_stats()
        self._update_history_table_data()
        logger.info("历史数据已清空")
    
    def _on_export_data(self):
        """导出数据"""
        # 获取历史统计数据
        history_stats = self.throughput_monitor.get_history_stats()
        
        if not history_stats:
            logger.warning("没有可导出的历史数据")
            return
        
        # 导出到CSV文件
        export_file_path = f"throughput_data_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            with open(export_file_path, "w", encoding="utf-8") as f:
                # 写入表头
                f.write("时间,吞吐量,平均处理时间,平均等待时间,活跃线程数,队列长度\n")
                
                # 写入数据
                for stats in history_stats:
                    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stats['timestamp']))
                    f.write(f"{time_str},{stats['throughput']:.2f},{stats['average_processing_time']:.2f},{stats['average_waiting_time']:.2f},{stats['active_threads']},{stats['queue_length']}\n")
            
            logger.info(f"数据已导出到文件: {export_file_path}")
        
        except Exception as e:
            logger.error(f"导出数据时发生错误: {e}")
    
    def stop(self):
        """停止吞吐量监测UI组件"""
        if self.update_timer:
            self.update_timer.stop()
            self.update_timer = None
        
        logger.info("吞吐量监测UI组件已停止")


class ThroughputChart(QWidget):
    """吞吐量图表组件"""
    
    def __init__(self):
        super().__init__()
        
        self.data_points: list = []  # 数据点列表 [(时间, 值), ...]
        self.max_data_points = 60  # 最大数据点数量（显示1分钟的数据）
        
        self.setMinimumHeight(150)
    
    def add_data_point(self, timestamp: float, value: float):
        """
        添加数据点
        
        Args:
            timestamp: 时间戳
            value: 数据值
        """
        self.data_points.append((timestamp, value))
        
        # 保持数据点数量在最大值以内
        if len(self.data_points) > self.max_data_points:
            self.data_points = self.data_points[-self.max_data_points:]
        
        # 重绘图表
        self.update()
    
    def paintEvent(self, event):
        """绘制事件"""
        from PySide2.QtGui import QPainter, QPen, QBrush
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 获取绘制区域
        rect = self.rect()
        width = rect.width()
        height = rect.height()
        
        # 清空背景
        painter.fillRect(rect, QColor(255, 255, 255))
        
        if not self.data_points:
            return
        
        # 计算数据范围
        values = [point[1] for point in self.data_points]
        min_value = min(values)
        max_value = max(values)
        
        # 确保范围不为零
        if min_value == max_value:
            max_value = min_value + 1
        
        # 绘制网格线
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        
        # 水平网格线（5条）
        for i in range(5):
            y = rect.top() + (height - 20) * (i / 4) + 10
            painter.drawLine(rect.left() + 40, y, rect.right() - 10, y)
        
        # 垂直网格线（10条）
        for i in range(10):
            x = rect.left() + 40 + (width - 50) * (i / 9)
            painter.drawLine(x, rect.top() + 10, x, rect.bottom() - 10)
        
        # 绘制数据曲线
        painter.setPen(QPen(QColor(0, 120, 215), 2))
        
        for i in range(1, len(self.data_points)):
            # 计算第一个点的坐标
            x1 = rect.left() + 40 + (width - 50) * ((i - 1) / (len(self.data_points) - 1))
            y1 = rect.bottom() - 10 - (height - 20) * ((self.data_points[i - 1][1] - min_value) / (max_value - min_value))
            
            # 计算第二个点的坐标
            x2 = rect.left() + 40 + (width - 50) * (i / (len(self.data_points) - 1))
            y2 = rect.bottom() - 10 - (height - 20) * ((self.data_points[i][1] - min_value) / (max_value - min_value))
            
            # 绘制线段
            painter.drawLine(x1, y1, x2, y2)
        
        # 绘制数据点
        painter.setPen(QPen(QColor(0, 120, 215), 4))
        painter.setBrush(QBrush(QColor(0, 120, 215)))
        
        for i in range(len(self.data_points)):
            x = rect.left() + 40 + (width - 50) * (i / (len(self.data_points) - 1))
            y = rect.bottom() - 10 - (height - 20) * ((self.data_points[i][1] - min_value) / (max_value - min_value))
            
            painter.drawEllipse(x - 2, y - 2, 4, 4)
        
        # 绘制Y轴标签
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.setFont(QFont("Microsoft YaHei", 8))
        
        for i in range(5):
            value = max_value - (max_value - min_value) * (i / 4)
            y = rect.top() + (height - 20) * (i / 4) + 10
            painter.drawText(rect.left() + 10, y + 4, f"{value:.2f}")


# 创建全局吞吐量监测UI实例
ThroughputMonitorUIGlobal = ThroughputMonitorUI()
