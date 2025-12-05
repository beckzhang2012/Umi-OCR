# ===============================================
# =============== 性能展示面板 ===============
# ===============================================

"""
UI性能展示模块：在开发者面板显示性能监测数据。
"""

import sys
import time
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QGroupBox, QScrollArea, QGridLayout,
    QProgressBar, QComboBox, QSpinBox, QDoubleSpinBox
)
from PySide2.QtCore import Qt, QTimer, Signal, Slot, QThread
from PySide2.QtGui import QFont, QPalette, QColor
from imports.umi_log import logger
from monitoring import get_performance_monitor, MetricType, MonitorConfig

class PerformanceMonitorThread(QThread):
    """性能监测线程"""
    metrics_updated = Signal(dict)
    
    def __init__(self, update_interval=1.0):
        super().__init__()
        self._update_interval = update_interval
        self._running = False
        self._monitor = get_performance_monitor()
    
    def run(self):
        self._running = True
        while self._running:
            try:
                # 获取性能摘要
                summary = self._monitor.get_performance_summary()
                self.metrics_updated.emit(summary)
                time.sleep(self._update_interval)
            except Exception as e:
                logger.error(f"性能监测线程错误: {e}")
                time.sleep(self._update_interval)
    
    def stop(self):
        self._running = False
        self.wait()

class PerformanceMetricsWidget(QWidget):
    """性能指标展示部件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self._monitor = get_performance_monitor()
        
        # 启动监测线程
        self._monitor_thread = PerformanceMonitorThread(update_interval=1.0)
        self._monitor_thread.metrics_updated.connect(self.update_metrics)
        self._monitor_thread.start()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("性能监测面板")
        title_font = QFont("Arial", 14, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 实时指标组
        realtime_group = QGroupBox("实时指标")
        realtime_layout = QGridLayout()
        
        # 内存峰值
        self.memory_peak_label = QLabel("内存峰值: 0 MB")
        realtime_layout.addWidget(self.memory_peak_label, 0, 0)
        
        # GPU内存峰值
        self.gpu_memory_peak_label = QLabel("GPU内存峰值: 0 MB")
        realtime_layout.addWidget(self.gpu_memory_peak_label, 0, 1)
        
        # 总批次
        self.total_batches_label = QLabel("总批次: 0")
        realtime_layout.addWidget(self.total_batches_label, 1, 0)
        
        # 总指标数
        self.total_metrics_label = QLabel("总指标数: 0")
        realtime_layout.addWidget(self.total_metrics_label, 1, 1)
        
        realtime_group.setLayout(realtime_layout)
        layout.addWidget(realtime_group)
        
        # 最近指标组
        recent_group = QGroupBox("最近指标")
        recent_layout = QVBoxLayout()
        
        self.recent_metrics_text = QTextEdit()
        self.recent_metrics_text.setReadOnly(True)
        self.recent_metrics_text.setMaximumHeight(200)
        recent_layout.addWidget(self.recent_metrics_text)
        
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        
        # 控制按钮组
        control_group = QGroupBox("控制面板")
        control_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("清除历史数据")
        self.clear_button.clicked.connect(self.clear_history)
        control_layout.addWidget(self.clear_button)
        
        self.export_button = QPushButton("导出数据")
        self.export_button.clicked.connect(self.export_data)
        control_layout.addWidget(self.export_button)
        
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.manual_refresh)
        control_layout.addWidget(self.refresh_button)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 配置组
        config_group = QGroupBox("监测配置")
        config_layout = QGridLayout()
        
        # 采样间隔
        config_layout.addWidget(QLabel("采样间隔(秒):"), 0, 0)
        self.sampling_interval_spin = QDoubleSpinBox()
        self.sampling_interval_spin.setRange(0.01, 10.0)
        self.sampling_interval_spin.setValue(0.1)
        self.sampling_interval_spin.setSingleStep(0.01)
        config_layout.addWidget(self.sampling_interval_spin, 0, 1)
        
        # 最大历史记录
        config_layout.addWidget(QLabel("最大历史记录:"), 1, 0)
        self.max_history_spin = QSpinBox()
        self.max_history_spin.setRange(100, 10000)
        self.max_history_spin.setValue(1000)
        self.max_history_spin.setSingleStep(100)
        config_layout.addWidget(self.max_history_spin, 1, 1)
        
        # 启用GPU监测
        self.gpu_monitor_check = QComboBox()
        self.gpu_monitor_check.addItems(["禁用", "启用"])
        config_layout.addWidget(QLabel("GPU监测:"), 2, 0)
        config_layout.addWidget(self.gpu_monitor_check, 2, 1)
        
        # 应用配置按钮
        self.apply_config_button = QPushButton("应用配置")
        self.apply_config_button.clicked.connect(self.apply_config)
        config_layout.addWidget(self.apply_config_button, 3, 0, 1, 2)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        self.setLayout(layout)
    
    @Slot(dict)
    def update_metrics(self, summary):
        """更新性能指标显示"""
        try:
            if "error" in summary:
                self.recent_metrics_text.setText(summary["error"])
                return
            
            # 更新实时指标
            self.memory_peak_label.setText(
                f"内存峰值: {summary['current_memory_peak']:.2f} MB"
            )
            
            self.gpu_memory_peak_label.setText(
                f"GPU内存峰值: {summary['current_gpu_memory_peak']:.2f} MB"
            )
            
            self.total_batches_label.setText(
                f"总批次: {summary['total_batches']}"
            )
            
            self.total_metrics_label.setText(
                f"总指标数: {summary['total_metrics']}"
            )
            
            # 更新最近指标
            recent_text = "最近指标:\n"
            for metric in summary.get("recent_metrics", []):
                timestamp = time.strftime(
                    "%H:%M:%S", 
                    time.localtime(metric["timestamp"])
                )
                recent_text += (
                    f"[{timestamp}] {metric['type']}: {metric['value']:.4f} {metric['unit']}\n"
                )
            
            self.recent_metrics_text.setText(recent_text)
            
        except Exception as e:
            logger.error(f"更新性能指标失败: {e}")
    
    @Slot()
    def clear_history(self):
        """清除历史数据"""
        try:
            self._monitor.clear_history()
            self.recent_metrics_text.setText("历史数据已清除")
        except Exception as e:
            logger.error(f"清除历史数据失败: {e}")
    
    @Slot()
    def export_data(self):
        """导出数据"""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"performance_data_{timestamp}.json"
            success = self._monitor.export_metrics(filename)
            if success:
                self.recent_metrics_text.setText(f"数据已导出到: {filename}")
            else:
                self.recent_metrics_text.setText("导出失败")
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            self.recent_metrics_text.setText(f"导出失败: {str(e)}")
    
    @Slot()
    def manual_refresh(self):
        """手动刷新"""
        try:
            summary = self._monitor.get_performance_summary()
            self.update_metrics(summary)
        except Exception as e:
            logger.error(f"手动刷新失败: {e}")
    
    @Slot()
    def apply_config(self):
        """应用配置"""
        try:
            config = MonitorConfig()
            config.sampling_interval = self.sampling_interval_spin.value()
            config.max_history_size = self.max_history_spin.value()
            config.enable_gpu_monitoring = (self.gpu_monitor_check.currentIndex() == 1)
            
            from monitoring import set_monitor_config
            set_monitor_config(config)
            
            self.recent_metrics_text.setText("配置已应用")
        except Exception as e:
            logger.error(f"应用配置失败: {e}")
            self.recent_metrics_text.setText(f"配置应用失败: {str(e)}")
    
    def closeEvent(self, event):
        """关闭事件"""
        self._monitor_thread.stop()
        event.accept()

class PerformancePanel(QWidget):
    """性能展示面板"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("性能监测面板")
        self.setGeometry(100, 100, 600, 500)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # 创建性能指标部件
        self.metrics_widget = PerformanceMetricsWidget()
        scroll_area.setWidget(self.metrics_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)
    
    def closeEvent(self, event):
        """关闭事件"""
        self.metrics_widget.closeEvent(event)
        event.accept()

def show_performance_panel():
    """显示性能面板"""
    from PySide2.QtWidgets import QApplication
    
    app = QApplication.instance() or QApplication(sys.argv)
    panel = PerformancePanel()
    panel.show()
    return app, panel

if __name__ == "__main__":
    app, panel = show_performance_panel()
    sys.exit(app.exec_())
