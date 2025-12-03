#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR 启动入口
"""

import sys
import os
import traceback
from typing import List

# 添加当前目录到 Python 搜索路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入 Qt 模块
from PySide6.QtCore import Qt, QUrl, QCoreApplication
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

# 导入项目模块
from event_bus.event_bus import EventBus
from image_controller.image_controller import ImageController
from mission.mission_manager import MissionManager
from ocr.ocr_manager import OCRManager
from plugins_controller.plugins_connector import PluginsConnector
from tag_pages.tag_pages_connector import TagPagesConnector
from server.web_server import WebServer
from utils.call_func import callFuncAsync

# 全局变量
app = None
engine = None


class UmiOCRApp:
    """Umi-OCR 应用程序类"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self.image_controller = ImageController(self.event_bus)
        self.mission_manager = MissionManager(self.event_bus)
        self.ocr_manager = OCRManager(self.event_bus)
        self.plugins_connector = PluginsConnector(self.event_bus)
        self.tag_pages_connector = TagPagesConnector(self.event_bus)
        self.web_server = WebServer(self.event_bus)
        
        self._init_signals()
    
    def _init_signals(self):
        """初始化信号连接"""
        # 事件总线信号连接
        self.event_bus.signal.connect(self._on_event)
    
    def _on_event(self, event_name: str, *args, **kwargs):
        """处理事件总线事件"""
        # 这里可以添加事件处理逻辑
        pass
    
    def start(self):
        """启动应用程序"""
        # 启动所有管理器
        self.image_controller.start()
        self.mission_manager.start()
        self.ocr_manager.start()
        self.plugins_connector.start()
        self.tag_pages_connector.start()
        self.web_server.start()
    
    def stop(self):
        """停止应用程序"""
        # 停止所有管理器
        self.web_server.stop()
        self.tag_pages_connector.stop()
        self.plugins_connector.stop()
        self.ocr_manager.stop()
        self.mission_manager.stop()
        self.image_controller.stop()


class UmiOCRQmlApp:
    """Umi-OCR QML 应用程序类"""
    
    def __init__(self):
        self.umi_app = UmiOCRApp()
        
        self._init_qml()
    
    def _init_qml(self):
        """初始化 QML 引擎"""
        global engine
        
        # 创建 QML 引擎
        engine = QQmlApplicationEngine()
        
        # 注册类型到 QML
        engine.rootContext().setContextProperty("eventBus", self.umi_app.event_bus)
        engine.rootContext().setContextProperty("imageController", self.umi_app.image_controller)
        engine.rootContext().setContextProperty("missionManager", self.umi_app.mission_manager)
        engine.rootContext().setContextProperty("ocrManager", self.umi_app.ocr_manager)
        engine.rootContext().setContextProperty("pluginsConnector", self.umi_app.plugins_connector)
        engine.rootContext().setContextProperty("tagPagesConnector", self.umi_app.tag_pages_connector)
        engine.rootContext().setContextProperty("webServer", self.umi_app.web_server)
    
    def start(self):
        """启动应用程序"""
        # 加载 QML 文件
        qml_file = os.path.join(current_dir, "..", "qt_res", "qml", "Main.qml")
        engine.load(QUrl.fromLocalFile(qml_file))
        
        # 启动 Umi 应用程序
        self.umi_app.start()
    
    def stop(self):
        """停止应用程序"""
        # 停止 Umi 应用程序
        self.umi_app.stop()



def runQml(app_path: str = "", engineAddImportPath: str = ""):
    """启动 QML 应用程序"""
    global app
    
    # 创建 QGuiApplication
    app = QGuiApplication(sys.argv)
    
    # 设置应用程序名称和版本
    app.setApplicationName("Umi-OCR")
    app.setApplicationVersion("2.1.5")
    
    # 设置应用程序图标
    icon_file = os.path.join(current_dir, "..", "qt_res", "images", "icon.ico")
    app.setWindowIcon(QIcon(icon_file))
    
    # 添加 QML 导入路径
    if engineAddImportPath:
        engineAddImportPath = os.path.abspath(engineAddImportPath)
        if os.path.exists(engineAddImportPath):
            app.addLibraryPath(engineAddImportPath)
    
    try:
        # 创建 Umi-OCR QML 应用程序
        umi_qml_app = UmiOCRQmlApp()
        
        # 启动应用程序
        umi_qml_app.start()
        
        # 运行应用程序事件循环
        exit_code = app.exec()
        
        # 停止应用程序
        umi_qml_app.stop()
        
        # 退出应用程序
        sys.exit(exit_code)
    
    except Exception as e:
        # 捕获所有异常并显示错误消息
        err = traceback.format_exc()
        print(f"Failed to startup main program!\n\n{err}")
        
        # 尝试显示错误消息框
        try:
            from PySide6.QtWidgets import QMessageBox
            
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("启动失败")
            msg_box.setText(f"Failed to startup main program!\n\n{err}")
            msg_box.exec()
        except:
            pass
        
        # 退出应用程序
        sys.exit(1)



def main(app_path: str = "", engineAddImportPath: str = ""):
    """主函数"""
    # 启动 QML 应用程序
    runQml(app_path, engineAddImportPath)


if __name__ == "__main__":
    # 解析命令行参数
    app_path = ""
    engineAddImportPath = ""
    
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith("app_path="):
                app_path = arg.split("=", 1)[1]
            elif arg.startswith("engineAddImportPath="):
                engineAddImportPath = arg.split("=", 1)[1]
    
    # 启动应用程序
    main(app_path, engineAddImportPath)