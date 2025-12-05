#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ===============================================
# ============= 吞吐量监测 UI 组件 =============
# ===============================================

from typing import List, Dict, Any
from PySide2.QtCore import Qt, QTimer, QPointF
from PySide2.QtGui import QColor, QPainter, QFont, QPen
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QAbstractItemView,
)

from monitor.throughput_monitor import ThroughputMonitorGlobal


class ThroughputMonitorUI(QWidget):
    """吞吐量监测 UI 组件"""
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self._update_interval = 1000  # 1秒更新一次
        self._history_length = 60  # 显示60秒的历史数据
        
        self._history_data = {
            'throughput': [],  # 吞吐量历史数据
            'processing_time': [],  # 处理时间历史数据
            'wait_time': [],  # 等待时间历史数据
            'memory_usage': [],  # 内存使用历史数据
            'cpu_usage': [],  # CPU使用历史数据
        }
        
        self._init_ui()
        self._init_timer()
        self._update_data()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("吞吐量监测")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title_label)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self._update_data)
        control_layout.addWidget(refresh_button)
        
        clear_button = QPushButton("清空历史")
        clear_button.clicked.connect(self._clear_history)
        control_layout.addWidget(clear_button)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 实时数据面板
        realtime_panel = QFrame()
        realtime_panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        realtime_layout = QHBoxLayout(realtime_panel)
        
        # 吞吐量
        throughput_widget = self._create_stat_widget("吞吐量", "0 张/秒")
        realtime_layout.addWidget(throughput_widget)
        
        # 平均处理时间
        processing_time_widget = self._create_stat_widget("平均处理时间", "0 秒")
        realtime_layout.addWidget(processing_time_widget)
        
        # 平均等待时间
        wait_time_widget = self._create_stat_widget("平均等待时间", "0 秒")
        realtime_layout.addWidget(wait_time_widget)
        
        # 峰值内存
        memory_widget = self._create_stat_widget("峰值内存", "0 GB")
        realtime_layout.addWidget(memory_widget)
        
        # 峰值CPU
        cpu_widget = self._create_stat_widget("峰值CPU", "0 %")
        realtime_layout.addWidget(cpu_widget)
        
        layout.addWidget(realtime_panel)
        
        # 图表面板
        chart_layout = QHBoxLayout()
        
        # 吞吐量图表
        self._throughput_chart = ThroughputChart("吞吐量 (张/秒)", QColor(0, 128, 0))
        chart_layout.addWidget(self._throughput_chart)
        
        # 处理时间图表
        self._processing_time_chart = ThroughputChart("处理时间 (秒)", QColor(255, 0, 0))
        chart_layout.addWidget(self._processing_time_chart)
        
        # 等待时间图表
        self._wait_time_chart = ThroughputChart("等待时间 (秒)", QColor(0, 0, 255))
        chart_layout.addWidget(self._wait_time_chart)
        
        layout.addLayout(chart_layout)
        
        # 历史数据表格
        self._history_table = QTableWidget()
        self._history_table.setColumnCount(6)
        self._history_table.setHorizontalHeaderLabels([
            "批次ID", "处理时间", "等待时间", "吞吐量", "内存峰值", "CPU峰值"
        ])
        self._history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        table_scroll_area = QScrollArea()
        table_scroll_area.setWidgetResizable(True)
        table_scroll_area.setWidget(self._history_table)
        
        layout.addWidget(table_scroll_area)
    
    def _create_stat_widget(self, title: str, value: str) -> QWidget:
        """
        创建统计数据组件
        
        Args:
            title: 统计项名称
            value: 统计项值
            
        Returns:
            统计数据组件
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 10))
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setObjectName(f"{title.lower().replace(' ', '_')}_value")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(value_label)
        
        return widget
    
    def _init_timer(self):
        """初始化定时器"""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_data)
        self._timer.start(self._update_interval)
    
    def _update_data(self):
        """更新数据"""
        # 获取实时监测数据
        monitor_data = ThroughputMonitorGlobal.get_monitor_data()
        peak_resources = ThroughputMonitorGlobal.get_peak_resources()
        
        if monitor_data:
            # 计算实时统计数据
            recent_data = monitor_data[-5:]  # 取最近5个批次的数据
            
            avg_processing_time = sum(data['total_processing_time'] for data in recent_data) / len(recent_data)
            avg_wait_time = sum(data['avg_wait_time'] for data in recent_data) / len(recent_data)
            avg_throughput = sum(data['throughput'] for data in recent_data) / len(recent_data)
            
            # 更新实时数据面板
            self.findChild(QLabel, "吞吐量_value").setText(f"{avg_throughput:.2f} 张/秒")
            self.findChild(QLabel, "平均处理时间_value").setText(f"{avg_processing_time:.2f} 秒")
            self.findChild(QLabel, "平均等待时间_value").setText(f"{avg_wait_time:.2f} 秒")
            self.findChild(QLabel, "峰值内存_value").setText(f"{peak_resources['memory_peak']:.2f} GB")
            self.findChild(QLabel, "峰值cpu_value").setText(f"{peak_resources['cpu_peak']:.2f} %")
            
            # 更新历史数据
            self._update_history_data(avg_throughput, avg_processing_time, avg_wait_time, 
                                        peak_resources['memory_peak'], peak_resources['cpu_peak'])
            
            # 更新图表
            self._update_charts()
            
            # 更新历史数据表格
            self._update_history_table(monitor_data)
    
    def _update_history_data(self, throughput: float, processing_time: float, wait_time: float, 
                              memory_usage: float, cpu_usage: float):
        """
        更新历史数据
        
        Args:
            throughput: 吞吐量
            processing_time: 处理时间
            wait_time: 等待时间
            memory_usage: 内存使用
            cpu_usage: CPU使用
        """
        self._history_data['throughput'].append(throughput)
        self._history_data['processing_time'].append(processing_time)
        self._history_data['wait_time'].append(wait_time)
        self._history_data['memory_usage'].append(memory_usage)
        self._history_data['cpu_usage'].append(cpu_usage)
        
        # 保持历史数据长度
        for key in self._history_data:
            if len(self._history_data[key]) > self._history_length:
                self._history_data[key] = self._history_data[key][-self._history_length:]
    
    def _update_charts(self):
        """更新图表"""
        self._throughput_chart.update_data(self._history_data['throughput'])
        self._processing_time_chart.update_data(self._history_data['processing_time'])
        self._wait_time_chart.update_data(self._history_data['wait_time'])
    
    def _update_history_table(self, monitor_data: List[Dict[str, Any]]):
        """
        更新历史数据表格
        
        Args:
            monitor_data: 监测数据列表
        """
        self._history_table.setRowCount(len(monitor_data))
        
        for i, data in enumerate(reversed(monitor_data)):  # 反转显示，最新的在前面
            row = len(monitor_data) - 1 - i
            
            self._history_table.setItem(row, 0, QTableWidgetItem(f"{data['batch_id']}"))
            self._history_table.setItem(row, 1, QTableWidgetItem(f"{data['total_processing_time']:.2f} 秒"))
            self._history_table.setItem(row, 2, QTableWidgetItem(f"{data['avg_wait_time']:.2f} 秒"))
            self._history_table.setItem(row, 3, QTableWidgetItem(f"{data['throughput']:.2f} 张/秒"))
            self._history_table.setItem(row, 4, QTableWidgetItem(f"{data.get('memory_peak', 0):.2f} GB"))
            self._history_table.setItem(row, 5, QTableWidgetItem(f"{data.get('cpu_peak', 0):.2f} %"))
        
        # 调整列宽
        self._history_table.resizeColumnsToContents()
    
    def _clear_history(self):
        """清空历史数据"""
        ThroughputMonitorGlobal.clear_monitor_data()
        
        # 清空历史数据
        for key in self._history_data:
            self._history_data[key] = []
        
        # 清空图表
        self._throughput_chart.update_data([])
        self._processing_time_chart.update_data([])
        self._wait_time_chart.update_data([])
        
        # 清空表格
        self._history_table.setRowCount(0)
        
        # 重置实时数据面板
        self.findChild(QLabel, "吞吐量_value").setText("0 张/秒")
        self.findChild(QLabel, "平均处理时间_value").setText("0 秒")
        self.findChild(QLabel, "平均等待时间_value").setText("0 秒")
        self.findChild(QLabel, "峰值内存_value").setText("0 GB")
        self.findChild(QLabel, "峰值cpu_value").setText("0 %")
    
    def stop_monitoring(self):
        """停止监测"""
        self._timer.stop()


class ThroughputChart(QWidget):
    """吞吐量图表类"""
    
    def __init__(self, title: str, color: QColor, parent: QWidget = None):
        super().__init__(parent)
        
        self._title = title
        self._color = color
        self._data = []
        
        self.setMinimumSize(200, 150)
    
    def update_data(self, data: List[float]):
        """
        更新图表数据
        
        Args:
            data: 新的图表数据
        """
        self._data = data
        self.update()  # 重绘图表
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # 获取绘图区域
        rect = self.rect()
        margin = 40  # 边距
        
        # 标题
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(rect, Qt.AlignTop | Qt.AlignHCenter, self._title)
        
        if not self._data:
            # 没有数据时显示提示
            painter.setFont(QFont("Arial", 9))
            painter.drawText(rect, Qt.AlignCenter, "暂无数据")
            return
        
        # 坐标轴
        painter.setPen(QPen(Qt.gray, 1))
        
        # X轴
        painter.drawLine(margin, rect.height() - margin, rect.width() - margin, rect.height() - margin)
        
        # Y轴
        painter.drawLine(margin, margin, margin, rect.height() - margin)
        
        # 计算数据范围
        max_value = max(self._data) if self._data else 0
        min_value = min(self._data) if self._data else 0
        
        # 确保Y轴有一定的范围
        if max_value == min_value:
            max_value += 1
            min_value -= 1
        
        # 绘制Y轴刻度
        painter.setFont(QFont("Arial", 8))
        
        for i in range(5):
            value = min_value + (max_value - min_value) * i / 4
            y = margin + (rect.height() - 2 * margin) * (1 - i / 4)
            
            painter.drawLine(margin - 5, y, margin, y)
            painter.drawText(margin - 30, y + 4, f"{value:.1f}")
        
        # 绘制数据点和连接线
        if len(self._data) > 1:
            # 计算点的位置
            points = []
            
            for i, value in enumerate(self._data):
                x = margin + (rect.width() - 2 * margin) * i / (len(self._data) - 1)
                y = margin + (rect.height() - 2 * margin) * (1 - (value - min_value) / (max_value - min_value))
                
                points.append(QPointF(x, y))
            
            # 绘制连接线
            painter.setPen(QPen(self._color, 2))
            painter.drawPolyline(points)
            
            # 绘制数据点
            painter.setPen(QPen(self._color, 3))
            painter.setBrush(self._color)
            
            for point in points:
                painter.drawEllipse(point, 3, 3)
