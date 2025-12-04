# =============================================
# =============== 目录监控控制器 ===============
# =============================================

import os
import time
import json
import hashlib
import threading
import re
from PIL import Image
from PySide2.QtCore import QObject, Signal, Slot
from umi_log import logger
from .page import Page


class DirectoryMonitor(Page):
    """目录监控控制器"""
    
    # 信号定义
    taskAdded = Signal(str)  # 任务添加信号
    taskUpdated = Signal(str)  # 任务更新信号
    taskCompleted = Signal(str)  # 任务完成信号
    taskFailed = Signal(str)  # 任务失败信号
    queueUpdated = Signal()  # 队列更新信号
    monitorStatusChanged = Signal(str, bool)  # 监控状态变化信号
    
    def __init__(self, ctrlKey, controller):
        super().__init__(ctrlKey, controller)
        self.monitors = []  # 监控项列表
        self.queue = []  # 任务队列
        self.processing_tasks = set()  # 正在处理的任务
        self.completed_tasks = []  # 已完成的任务
        self.failed_tasks = []  # 失败的任务
        self.processed_files = set()  # 已处理的文件哈希集合
        self.monitor_threads = []  # 监控线程列表
        self.is_running = False  # 监控是否运行
        
        # 加载配置和日志
        self.load_config()
        self.load_processed_files()
        self.load_queue()
        
    def __del__(self):
        self.stop_monitoring()
        super().__del__()
        
    def load_config(self):
        """加载监控配置"""
        config_path = os.path.join(os.getcwd(), "logs", "directory_monitor_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self.monitors = json.load(f)
                logger.info(f"加载目录监控配置成功，共 {len(self.monitors)} 个监控项")
            except Exception as e:
                logger.error(f"加载目录监控配置失败: {e}")
                self.monitors = []
        else:
            self.monitors = []
            logger.info("目录监控配置文件不存在，将创建新配置")
            
    def save_config(self):
        """保存监控配置"""
        config_path = os.path.join(os.getcwd(), "logs", "directory_monitor_config.json")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.monitors, f, ensure_ascii=False, indent=2)
            logger.info(f"保存目录监控配置成功，共 {len(self.monitors)} 个监控项")
        except Exception as e:
            logger.error(f"保存目录监控配置失败: {e}")
            
    def load_processed_files(self):
        """加载已处理文件记录"""
        processed_path = os.path.join(os.getcwd(), "logs", "directory_monitor_processed.json")
        if os.path.exists(processed_path):
            try:
                with open(processed_path, "r", encoding="utf-8") as f:
                    self.processed_files = set(json.load(f))
                logger.info(f"加载已处理文件记录成功，共 {len(self.processed_files)} 个文件")
            except Exception as e:
                logger.error(f"加载已处理文件记录失败: {e}")
                self.processed_files = set()
        else:
            self.processed_files = set()
            logger.info("已处理文件记录文件不存在，将创建新记录")
            
    def save_processed_files(self):
        """保存已处理文件记录"""
        processed_path = os.path.join(os.getcwd(), "logs", "directory_monitor_processed.json")
        try:
            os.makedirs(os.path.dirname(processed_path), exist_ok=True)
            with open(processed_path, "w", encoding="utf-8") as f:
                json.dump(list(self.processed_files), f, ensure_ascii=False, indent=2)
            logger.info(f"保存已处理文件记录成功，共 {len(self.processed_files)} 个文件")
        except Exception as e:
            logger.error(f"保存已处理文件记录失败: {e}")
            
    def load_queue(self):
        """加载任务队列"""
        queue_path = os.path.join(os.getcwd(), "logs", "directory_monitor_queue.json")
        if os.path.exists(queue_path):
            try:
                with open(queue_path, "r", encoding="utf-8") as f:
                    self.queue = json.load(f)
                logger.info(f"加载任务队列成功，共 {len(self.queue)} 个任务")
            except Exception as e:
                logger.error(f"加载任务队列失败: {e}")
                self.queue = []
        else:
            self.queue = []
            logger.info("任务队列文件不存在，将创建新队列")
            
    def save_queue(self):
        """保存任务队列"""
        queue_path = os.path.join(os.getcwd(), "logs", "directory_monitor_queue.json")
        try:
            os.makedirs(os.path.dirname(queue_path), exist_ok=True)
            with open(queue_path, "w", encoding="utf-8") as f:
                json.dump(self.queue, f, ensure_ascii=False, indent=2)
            logger.info(f"保存任务队列成功，共 {len(self.queue)} 个任务")
        except Exception as e:
            logger.error(f"保存任务队列失败: {e}")
            
    def add_monitor(self, monitor_info):
        """添加监控项
        
        Args:
            monitor_info (str): 监控项信息的JSON字符串
                - name: 监控项名称
                - directory: 监控目录
                - file_types: 文件类型列表
                - poll_interval: 轮询间隔（秒）
                - recursive: 是否递归子目录
                - rules: 路由规则列表
        """
        # 将JSON字符串转换为Python字典
        monitor_info = json.loads(monitor_info)
        monitor_id = f"monitor_{len(self.monitors) + 1}_{int(time.time())}"
        monitor = {
            "id": monitor_id,
            "name": monitor_info.get("name", "未命名监控项"),
            "directory": monitor_info.get("directory", ""),
            "file_types": monitor_info.get("file_types", ["*.png", "*.jpg", "*.jpeg"]),
            "poll_interval": monitor_info.get("poll_interval", 5),
            "recursive": monitor_info.get("recursive", True),
            "rules": monitor_info.get("rules", []),
            "enabled": True
        }
        
        self.monitors.append(monitor)
        self.save_config()
        
        # 如果监控正在运行，启动新的监控线程
        if self.is_running:
            self.start_monitor_thread(monitor)
            
        logger.info(f"添加监控项成功: {monitor['name']}")
        return monitor_id
        
    def update_monitor(self, monitor_id, monitor_info):
        """更新监控项
        
        Args:
            monitor_id (str): 监控项ID
            monitor_info (str): 监控项信息的JSON字符串
        """
        # 将JSON字符串转换为Python字典
        monitor_info = json.loads(monitor_info)
        for i, monitor in enumerate(self.monitors):
            if monitor["id"] == monitor_id:
                # 停止旧的监控线程
                self.stop_monitor_thread(monitor_id)
                
                # 更新监控信息
                self.monitors[i].update(monitor_info)
                self.save_config()
                
                # 启动新的监控线程
                if self.is_running and self.monitors[i].get("enabled", True):
                    self.start_monitor_thread(self.monitors[i])
                    
                logger.info(f"更新监控项成功: {monitor['name']}")
                return True
                
        logger.error(f"更新监控项失败: 监控项 {monitor_id} 不存在")
        return False
        
    def delete_monitor(self, monitor_id):
        """删除监控项
        
        Args:
            monitor_id (str): 监控项ID
        """
        # 停止监控线程
        self.stop_monitor_thread(monitor_id)
        
        # 删除监控项
        self.monitors = [m for m in self.monitors if m["id"] != monitor_id]
        self.save_config()
        
        logger.info(f"删除监控项成功: {monitor_id}")
        return True
        
    def start_monitoring(self):
        """启动所有监控"""
        if self.is_running:
            logger.warning("目录监控已经在运行中")
            return
            
        self.is_running = True
        
        # 启动所有监控线程
        for monitor in self.monitors:
            if monitor.get("enabled", True):
                self.start_monitor_thread(monitor)
                
        logger.info("启动目录监控成功")
        return True
        
    def stop_monitoring(self):
        """停止所有监控"""
        if not self.is_running:
            logger.warning("目录监控已经停止")
            return
            
        self.is_running = False
        
        # 停止所有监控线程
        for thread in self.monitor_threads:
            if thread.is_alive():
                thread.join(timeout=5)
                
        self.monitor_threads.clear()
        logger.info("停止目录监控成功")
        return True
        
    def start_monitor_thread(self, monitor):
        """启动监控线程
        
        Args:
            monitor (dict): 监控项信息
        """
        thread = threading.Thread(
            target=self.monitor_directory,
            args=(monitor,),
            daemon=True,
            name=f"Monitor_{monitor['id']}"
        )
        self.monitor_threads.append(thread)
        thread.start()
        logger.info(f"启动监控线程: {monitor['name']}")
        self.monitorStatusChanged.emit(monitor['id'], True)
        
    def stop_monitor_thread(self, monitor_id):
        """停止监控线程
        
        Args:
            monitor_id (str): 监控项ID
        """
        # 这里通过设置is_running为False来停止线程，因为监控线程会定期检查这个标志
        self.monitorStatusChanged.emit(monitor_id, False)
        logger.info(f"停止监控线程: {monitor_id}")
        
    def monitor_directory(self, monitor):
        """监控目录线程函数
        
        Args:
            monitor (dict): 监控项信息
        """
        logger.info(f"开始监控目录: {monitor['directory']}")
        
        while self.is_running and monitor.get("enabled", True):
            try:
                # 检查目录是否存在
                if not os.path.exists(monitor["directory"]):
                    logger.warning(f"监控目录不存在: {monitor['directory']}")
                    time.sleep(monitor["poll_interval"])
                    continue
                    
                # 遍历目录
                for root, dirs, files in os.walk(monitor["directory"]):
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        # 检查文件类型
                        if not self.is_valid_file_type(file, monitor["file_types"]):
                            continue
                            
                        # 检查是否已处理
                        if self.is_file_processed(file_path):
                            continue
                            
                        # 检查文件是否完整（大小稳定）
                        if not self.is_file_complete(file_path):
                            continue
                            
                        # 应用路由规则
                        task_info = self.apply_routing_rules(file_path, monitor["rules"])
                        if not task_info:
                            logger.warning(f"文件 {file_path} 不匹配任何路由规则")
                            continue
                            
                        # 添加到任务队列
                        self.add_task_to_queue(file_path, task_info, monitor["id"])
                        
                    # 如果不递归子目录，只遍历一级
                    if not monitor["recursive"]:
                        break
                        
            except Exception as e:
                logger.error(f"监控目录 {monitor['directory']} 时出错: {e}")
                
            # 等待下一次轮询
            time.sleep(monitor["poll_interval"])
            
        logger.info(f"停止监控目录: {monitor['directory']}")
        self.monitorStatusChanged.emit(monitor['id'], False)
        
    def is_valid_file_type(self, filename, file_types):
        """检查文件类型是否有效
        
        Args:
            filename (str): 文件名
            file_types (list): 文件类型列表
        """
        for file_type in file_types:
            # 转换为正则表达式
            pattern = file_type.replace("*", ".*")
            if re.match(f"{pattern}$", filename, re.IGNORECASE):
                return True
        return False
        
    def is_file_processed(self, file_path):
        """检查文件是否已处理
        
        Args:
            file_path (str): 文件路径
        """
        file_hash = self.calculate_file_hash(file_path)
        return file_hash in self.processed_files
        
    def is_file_complete(self, file_path):
        """检查文件是否完整（大小稳定）
        
        Args:
            file_path (str): 文件路径
        """
        try:
            size1 = os.path.getsize(file_path)
            time.sleep(0.1)  # 等待0.1秒
            size2 = os.path.getsize(file_path)
            return size1 == size2
        except Exception as e:
            logger.error(f"检查文件完整性时出错 {file_path}: {e}")
            return False
            
    def calculate_file_hash(self, file_path):
        """计算文件哈希值
        
        Args:
            file_path (str): 文件路径
        """
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希值时出错 {file_path}: {e}")
            return None
            
    def apply_routing_rules(self, file_path, rules):
        """应用路由规则
        
        Args:
            file_path (str): 文件路径
            rules (list): 路由规则列表
        """
        filename = os.path.basename(file_path)
        
        for rule in rules:
            rule_type = rule.get("type", "filename_regex")
            pattern = rule.get("pattern", "")
            
            if rule_type == "filename_regex":
                # 文件名正则匹配
                if re.match(pattern, filename):
                    return {
                        "template": rule.get("template", "default"),
                        "output_dir": rule.get("output_dir", ""),
                        "priority": rule.get("priority", 0)
                    }
                    
            elif rule_type == "file_size":
                # 文件大小匹配
                try:
                    file_size = os.path.getsize(file_path)
                    min_size = rule.get("min_size", 0)
                    max_size = rule.get("max_size", float("inf"))
                    if min_size <= file_size <= max_size:
                        return {
                            "template": rule.get("template", "default"),
                            "output_dir": rule.get("output_dir", ""),
                            "priority": rule.get("priority", 0)
                        }
                except Exception as e:
                    logger.error(f"获取文件大小失败 {file_path}: {e}")
                    
            elif rule_type == "modified_time":
                # 修改时间匹配
                try:
                    modified_time = os.path.getmtime(file_path)
                    min_time = rule.get("min_time", 0)
                    max_time = rule.get("max_time", float("inf"))
                    if min_time <= modified_time <= max_time:
                        return {
                            "template": rule.get("template", "default"),
                            "output_dir": rule.get("output_dir", ""),
                            "priority": rule.get("priority", 0)
                        }
                except Exception as e:
                    logger.error(f"获取文件修改时间失败 {file_path}: {e}")
                    
        # 如果没有匹配的规则，返回默认规则
        return {
            "template": "default",
            "output_dir": "",
            "priority": 0
        }
        
    def add_task_to_queue(self, file_path, task_info, monitor_id):
        """添加任务到队列
        
        Args:
            file_path (str): 文件路径
            task_info (dict): 任务信息
            monitor_id (str): 监控项ID
        """
        task_id = f"task_{len(self.queue) + 1}_{int(time.time())}"
        task = {
            "id": task_id,
            "file_path": file_path,
            "template": task_info["template"],
            "output_dir": task_info["output_dir"],
            "priority": task_info["priority"],
            "status": "waiting",  # waiting, processing, completed, failed
            "monitor_id": monitor_id,
            "created_time": time.time(),
            "started_time": None,
            "completed_time": None,
            "error_message": None,
            "retry_count": 0,
            "max_retries": 3
        }
        
        self.queue.append(task)
        self.save_queue()
        self.taskAdded.emit(task_id)
        self.queueUpdated.emit()
        logger.info(f"添加任务到队列: {file_path}")
        
        # 自动开始处理任务
        self.process_queue()
        
    def process_queue(self):
        """处理任务队列"""
        # 只处理等待状态的任务
        waiting_tasks = [t for t in self.queue if t["status"] == "waiting"]
        
        # 按优先级排序
        waiting_tasks.sort(key=lambda x: -x["priority"])
        
        # 处理任务（最多同时处理3个任务）
        for task in waiting_tasks:
            if len(self.processing_tasks) >= 3:
                break
                
            # 标记为处理中
            task["status"] = "processing"
            task["started_time"] = time.time()
            self.processing_tasks.add(task["id"])
            self.save_queue()
            self.taskUpdated.emit(task["id"])
            self.queueUpdated.emit()
            
            # 启动处理线程
            threading.Thread(
                target=self.process_task,
                args=(task,),
                daemon=True,
                name=f"Process_{task['id']}"
            ).start()
            
    def process_task(self, task):
        """处理单个任务
        
        Args:
            task (dict): 任务信息
        """
        logger.info(f"开始处理任务: {task['file_path']}")
        
        try:
            # 调用OCR处理
            result = self.perform_ocr(task)
            
            if result:
                # 任务完成
                task["status"] = "completed"
                task["completed_time"] = time.time()
                self.completed_tasks.append(task)
                self.taskCompleted.emit(task["id"])
                logger.info(f"任务处理成功: {task['file_path']}")
            else:
                # 任务失败
                task["status"] = "failed"
                task["completed_time"] = time.time()
                task["error_message"] = "OCR处理失败"
                self.failed_tasks.append(task)
                self.taskFailed.emit(task["id"])
                logger.error(f"任务处理失败: {task['file_path']}")
                
        except Exception as e:
            # 任务失败
            task["status"] = "failed"
            task["completed_time"] = time.time()
            task["error_message"] = str(e)
            self.failed_tasks.append(task)
            self.taskFailed.emit(task["id"])
            logger.error(f"任务处理出错 {task['file_path']}: {e}")
            
        finally:
            # 从处理中集合中移除
            self.processing_tasks.remove(task["id"])
            self.save_queue()
            self.queueUpdated.emit()
            
            # 标记文件为已处理
            file_hash = self.calculate_file_hash(task["file_path"])
            if file_hash:
                self.processed_files.add(file_hash)
                self.save_processed_files()
                
            # 继续处理下一个任务
            self.process_queue()
            
    def perform_ocr(self, task):
        """执行OCR处理
        
        Args:
            task (dict): 任务信息
        """
        try:
            # 这里需要调用现有的OCR功能
            # 由于我不清楚现有的OCR接口，这里只是一个示例
            # 实际实现时需要替换为真正的OCR调用
            
            # 模拟OCR处理
            time.sleep(2)
            
            # 生成输出文件
            if task["output_dir"]:
                os.makedirs(task["output_dir"], exist_ok=True)
                output_path = os.path.join(task["output_dir"], f"{os.path.basename(task['file_path'])}.txt")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(f"OCR结果 for {task['file_path']}")
                    
            return True
            
        except Exception as e:
            logger.error(f"执行OCR时出错 {task['file_path']}: {e}")
            return False
            
    def retry_task(self, task_id):
        """重试失败的任务
        
        Args:
            task_id (str): 任务ID
        """
        for task in self.queue:
            if task["id"] == task_id and task["status"] == "failed":
                if task["retry_count"] < task["max_retries"]:
                    task["retry_count"] += 1
                    task["status"] = "waiting"
                    task["error_message"] = None
                    self.save_queue()
                    self.taskUpdated.emit(task_id)
                    self.queueUpdated.emit()
                    
                    # 从失败列表中移除
                    self.failed_tasks = [t for t in self.failed_tasks if t["id"] != task_id]
                    
                    # 开始处理队列
                    self.process_queue()
                    
                    logger.info(f"重试任务: {task['file_path']} (第 {task['retry_count']} 次)")
                    return True
                else:
                    logger.warning(f"任务 {task_id} 已达到最大重试次数")
                    return False
                    
        logger.error(f"重试任务失败: 任务 {task_id} 不存在或不是失败状态")
        return False
        
    def skip_task(self, task_id):
        """跳过任务
        
        Args:
            task_id (str): 任务ID
        """
        for task in self.queue:
            if task["id"] == task_id:
                # 标记文件为已处理
                file_hash = self.calculate_file_hash(task["file_path"])
                if file_hash:
                    self.processed_files.add(file_hash)
                    self.save_processed_files()
                    
                # 从队列中移除
                self.queue.remove(task)
                self.save_queue()
                self.queueUpdated.emit()
                
                # 从处理中集合中移除
                if task["id"] in self.processing_tasks:
                    self.processing_tasks.remove(task["id"])
                    
                # 从失败列表中移除
                self.failed_tasks = [t for t in self.failed_tasks if t["id"] != task_id]
                
                logger.info(f"跳过任务: {task['file_path']}")
                return True
                
        logger.error(f"跳过任务失败: 任务 {task_id} 不存在")
        return False
        
    def get_queue_stats(self):
        """获取队列统计信息"""
        waiting = len([t for t in self.queue if t["status"] == "waiting"])
        processing = len(self.processing_tasks)
        completed = len(self.completed_tasks)
        failed = len(self.failed_tasks)
        
        return {
            "waiting": waiting,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "total": waiting + processing + completed + failed
        }
        
    def get_monitors(self):
        """获取监控项列表"""
        return self.monitors
        
    def get_queue(self):
        """获取任务队列"""
        return self.queue
        
    def clear_processed_files(self):
        """清除已处理文件记录"""
        self.processed_files.clear()
        self.save_processed_files()
        logger.info("清除已处理文件记录成功")
        return True
        
    def clear_queue(self):
        """清除任务队列"""
        self.queue.clear()
        self.processing_tasks.clear()
        self.completed_tasks.clear()
        self.failed_tasks.clear()
        self.save_queue()
        self.queueUpdated.emit()
        logger.info("清除任务队列成功")
        return True
