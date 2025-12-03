#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR 日志记录模块
"""

import os
import logging
import time
from logging.handlers import RotatingFileHandler

# 日志目录
Logs_Dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))

# 确保日志目录存在
if not os.path.exists(Logs_Dir):
    os.makedirs(Logs_Dir)

# 日志文件名格式
Log_File_Format = "umi-%Y%m%d-%H%M%S.log"

# 日志级别
Log_Level = logging.DEBUG

# 日志格式
Log_Format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 日志处理器
log_handlers = []


class UmiLogger(logging.Logger):
    """Umi-OCR 日志记录器"""
    
    def __init__(self, name):
        super().__init__(name, Log_Level)
        
        # 设置日志格式
        formatter = logging.Formatter(Log_Format)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(Log_Level)
        console_handler.setFormatter(formatter)
        
        # 文件处理器
        file_handler = RotatingFileHandler(
            os.path.join(Logs_Dir, time.strftime(Log_File_Format)),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5  # 保留5个备份文件
        )
        file_handler.setLevel(Log_Level)
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        self.addHandler(console_handler)
        self.addHandler(file_handler)
        
        # 记录启动日志
        self.info(f"UmiLogger initialized for {name}")


# 设置日志记录器类
logging.setLoggerClass(UmiLogger)



def getLogger(name):
    """获取日志记录器"""
    return logging.getLogger(name)


# 全局日志记录器
logger = getLogger(__name__)




def openLogDir():
    """打开日志目录"""
    try:
        if os.name == "nt":
            # Windows 系统
            os.startfile(Logs_Dir)
        else:
            # Linux 或 macOS 系统
            import subprocess
            subprocess.run(["xdg-open", Logs_Dir])
    except Exception as e:
        logger = getLogger(__name__)
        logger.error(f"Failed to open log directory: {e}")



if __name__ == "__main__":
    # 测试日志记录器
    logger = getLogger("test")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    # 测试打开日志目录
    openLogDir()