# ======================================== 
# ============== 目录监控器 =============== 
# ======================================== 

import os 
import time 
import json 
import hashlib 
import threading 
import re 
from typing import List, Dict, Any 
from umi_log import logger 
from mission.mission_ocr import MissionOCR, ImageSuf 

class DirectoryMonitor: 
    def __init__(self): 
        self.monitor_items = []  # 监控项列表 
        self.routing_rules = []  # 路由规则列表 
        self.file_queue = []      # 文件队列 
        self.processing_files = {}  # 正在处理的文件 
        self.completed_files = []  # 已完成的文件 
        self.failed_files = []     # 失败的文件 
        
        # 去重记录 
        self.processed_files = set()  # 已处理的文件哈希 
        
        # 配置文件路径 
        self.config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'config') 
        self.monitor_config_file = os.path.join(self.config_dir, 'monitor_config.json') 
        self.queue_config_file = os.path.join(self.config_dir, 'monitor_queue.json') 
        self.log_config_file = os.path.join(self.config_dir, 'monitor_logs.json') 
        
        # 确保配置目录存在 
        if not os.path.exists(self.config_dir): 
            os.makedirs(self.config_dir) 
        
        # 加载配置 
        self.load_config() 
        self.load_queue() 
        self.load_logs() 
        
        # 启动监控线程 
        self.monitor_threads = [] 
        self.start_monitoring() 

    def load_config(self): 
        """加载监控配置""" 
        try: 
            if os.path.exists(self.monitor_config_file): 
                with open(self.monitor_config_file, 'r', encoding='utf-8') as f: 
                    config = json.load(f) 
                    self.monitor_items = config.get('monitor_items', []) 
                    self.routing_rules = config.get('routing_rules', []) 
                logger.info(f"加载了 {len(self.monitor_items)} 个监控项和 {len(self.routing_rules)} 个路由规则") 
        except Exception as e: 
            logger.error(f"加载监控配置失败：{e}") 

    def save_config(self): 
        """保存监控配置""" 
        try: 
            config = { 
                'monitor_items': self.monitor_items, 
                'routing_rules': self.routing_rules 
            } 
            with open(self.monitor_config_file, 'w', encoding='utf-8') as f: 
                json.dump(config, f, ensure_ascii=False, indent=4) 
            logger.info("保存监控配置成功") 
        except Exception as e: 
            logger.error(f"保存监控配置失败：{e}") 

    def load_queue(self): 
        """加载文件队列""" 
        try: 
            if os.path.exists(self.queue_config_file): 
                with open(self.queue_config_file, 'r', encoding='utf-8') as f: 
                    queue_data = json.load(f) 
                    self.file_queue = queue_data.get('file_queue', []) 
                    self.processing_files = queue_data.get('processing_files', {}) 
                    self.completed_files = queue_data.get('completed_files', []) 
                    self.failed_files = queue_data.get('failed_files', []) 
                logger.info(f"加载了文件队列：等待 {len(self.file_queue)} 个，处理中 {len(self.processing_files)} 个，已完成 {len(self.completed_files)} 个，失败 {len(self.failed_files)} 个") 
        except Exception as e: 
            logger.error(f"加载文件队列失败：{e}") 

    def save_queue(self): 
        """保存文件队列""" 
        try: 
            queue_data = { 
                'file_queue': self.file_queue, 
                'processing_files': self.processing_files, 
                'completed_files': self.completed_files, 
                'failed_files': self.failed_files 
            } 
            with open(self.queue_config_file, 'w', encoding='utf-8') as f: 
                json.dump(queue_data, f, ensure_ascii=False, indent=4) 
            logger.info("保存文件队列成功") 
        except Exception as e: 
            logger.error(f"保存文件队列失败：{e}") 

    def load_logs(self): 
        """加载监控日志""" 
        try: 
            if os.path.exists(self.log_config_file): 
                with open(self.log_config_file, 'r', encoding='utf-8') as f: 
                    logs_data = json.load(f) 
                    # 从日志中恢复已处理的文件哈希 
                    for log in logs_data: 
                        if 'file_hash' in log: 
                            self.processed_files.add(log['file_hash']) 
                logger.info(f"加载了 {len(logs_data)} 条监控日志") 
        except Exception as e: 
            logger.error(f"加载监控日志失败：{e}") 

    def save_logs(self, log_entry): 
        """保存监控日志""" 
        try: 
            logs_data = [] 
            if os.path.exists(self.log_config_file): 
                with open(self.log_config_file, 'r', encoding='utf-8') as f: 
                    logs_data = json.load(f) 
            
            # 添加新日志 
            logs_data.append(log_entry) 
            
            # 保存日志 
            with open(self.log_config_file, 'w', encoding='utf-8') as f: 
                json.dump(logs_data, f, ensure_ascii=False, indent=4) 
        except Exception as e: 
            logger.error(f"保存监控日志失败：{e}") 

    def calculate_file_hash(self, file_path): 
        """计算文件哈希值""" 
        try: 
            with open(file_path, 'rb') as f: 
                data = f.read() 
                return hashlib.md5(data).hexdigest() 
        except Exception as e: 
            logger.error(f"计算文件哈希失败：{file_path}，错误：{e}") 
            return None 

    def is_file_processed(self, file_path): 
        """检查文件是否已处理""" 
        file_hash = self.calculate_file_hash(file_path) 
        if file_hash: 
            return file_hash in self.processed_files 
        return False 

    def mark_file_processed(self, file_path): 
        """标记文件为已处理""" 
        file_hash = self.calculate_file_hash(file_path) 
        if file_hash: 
            self.processed_files.add(file_hash) 
            
            # 记录日志 
            log_entry = { 
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), 
                'action': 'file_processed', 
                'file_path': file_path, 
                'file_hash': file_hash 
            } 
            self.save_logs(log_entry) 

    def scan_directory(self, monitor_item): 
        """扫描监控目录""" 
        try: 
            monitor_dir = monitor_item['directory'] 
            file_types = monitor_item.get('file_types', ImageSuf) 
            recursive_level = monitor_item.get('recursive_level', 0) 
            
            # 检查目录是否存在 
            if not os.path.exists(monitor_dir): 
                logger.warning(f"监控目录不存在：{monitor_dir}") 
                return 
            
            # 扫描目录 
            for root, _, files in os.walk(monitor_dir): 
                # 计算当前递归层级 
                current_level = root[len(monitor_dir):].count(os.sep) 
                if current_level > recursive_level: 
                    break 
                
                for file in files: 
                    # 检查文件类型 
                    if os.path.splitext(file)[-1].lower() in file_types: 
                        file_path = os.path.join(root, file) 
                        
                        # 检查文件是否已处理 
                        if not self.is_file_processed(file_path): 
                            # 添加到文件队列 
                            self.add_to_queue(file_path, monitor_item) 
        except Exception as e: 
            logger.error(f"扫描监控目录失败：{monitor_item['directory']}，错误：{e}") 

    def add_to_queue(self, file_path, monitor_item): 
        """将文件添加到队列""" 
        try: 
            # 收集文件信息 
            file_info = { 
                'file_path': file_path, 
                'monitor_item': monitor_item, 
                'added_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), 
                'status': 'waiting' 
            } 
            
            # 添加到文件队列 
            self.file_queue.append(file_info) 
            
            # 保存队列 
            self.save_queue() 
            
            # 记录日志 
            log_entry = { 
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), 
                'action': 'file_added_to_queue', 
                'file_path': file_path, 
                'monitor_directory': monitor_item['directory'] 
            } 
            self.save_logs(log_entry) 
            
            logger.info(f"文件已添加到队列：{file_path}") 
        except Exception as e: 
            logger.error(f"将文件添加到队列失败：{file_path}，错误：{e}") 

    def route_file(self, file_info): 
        """根据路由规则分配文件到不同的OCR任务""" 
        try: 
            file_path = file_info['file_path'] 
            
            # 匹配路由规则 
            for rule in self.routing_rules: 
                # 检查文件名正则 
                if 'filename_regex' in rule: 
                    filename = os.path.basename(file_path) 
                    if not re.match(rule['filename_regex'], filename): 
                        continue 
                
                # 检查文件尺寸 
                if 'min_size' in rule or 'max_size' in rule: 
                    file_size = os.path.getsize(file_path) 
                    if 'min_size' in rule and file_size < rule['min_size']: 
                        continue 
                    if 'max_size' in rule and file_size > rule['max_size']: 
                        continue 
                
                # 检查修改时间 
                if 'min_modified_time' in rule or 'max_modified_time' in rule: 
                    modified_time = os.path.getmtime(file_path) 
                    if 'min_modified_time' in rule and modified_time < rule['min_modified_time']: 
                        continue 
                    if 'max_modified_time' in rule and modified_time > rule['max_modified_time']: 
                        continue 
                
                # 匹配到规则，返回OCR任务参数 
                return rule.get('ocr_params', {}) 
            
            # 如果没有匹配到任何规则，返回默认参数 
            return {} 
        except Exception as e: 
            logger.error(f"路由文件失败：{file_info['file_path']}，错误：{e}") 
            return {} 

    def process_queue(self): 
        """处理文件队列""" 
        try: 
            while self.file_queue: 
                # 获取队列中的第一个文件 
                file_info = self.file_queue.pop(0) 
                file_path = file_info['file_path'] 
                
                # 标记文件为处理中 
                file_info['status'] = 'processing' 
                file_info['processing_start_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) 
                self.processing_files[file_path] = file_info 
                
                # 保存队列 
                self.save_queue() 
                
                # 路由文件到OCR任务 
                ocr_params = self.route_file(file_info) 
                
                # 执行OCR任务 
                try: 
                    # 构造任务参数 
                    argd = { 
                        # OCR模板参数 
                        'ocr.template': ocr_params.get('template', '默认模板'), 
                        
                        # 任务参数 
                        'mission.dirType': ocr_params.get('output_dir_type', 'source'),  # 保存到原目录 
                        'mission.ignoreBlank': True,  # 忽略空白文件 
                        'mission.filesType.txt': True,  # 输出为TXT文件 
                        
                        # 并发限制参数 
                        'mission.concurrency': ocr_params.get('concurrency_limit', 1) 
                    } 
                    
                    # 构造任务信息 
                    msnInfo = { 
                        'onStart': lambda msnInfo: logger.info(f"OCR任务队列开始"), 
                        'onReady': lambda msnInfo, msn: logger.info(f"单个OCR任务准备：{msn['path']}"), 
                        'onGet': lambda msnInfo, msn, res: logger.info(f"单个OCR任务完成：{msn['path']}"), 
                        'onEnd': lambda msnInfo, msg: logger.info(f"OCR任务队列完成：{msg}"), 
                        'argd': argd, 
                    } 
                    
                    # 路径转为任务列表格式，加载进任务管理器 
                    msnList = [{"path": file_path}] 
                    msnID = MissionOCR.addMissionList(msnInfo, msnList) 
                    
                    if msnID.startswith("[Error]"): 
                        logger.error(f"添加OCR任务失败：{msnID}") 
                        raise Exception(f"添加OCR任务失败：{msnID}") 
                    else: 
                        logger.info(f"添加OCR任务成功：{msnID}") 
                        
                        # 等待任务完成 
                        while MissionOCR.isMissionListRunning(msnID): 
                            time.sleep(1) 
                        
                        # 获取任务结果 
                        mission_result = MissionOCR.getMissionListResult(msnID) 
                        
                        if mission_result.get('success_count', 0) > 0: 
                            # 任务成功 
                            file_info['status'] = 'completed' 
                            file_info['processing_end_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) 
                            file_info['result'] = 'success' 
                            self.completed_files.append(file_info) 
                            
                            # 标记文件为已处理 
                            self.mark_file_processed(file_path) 
                            
                            # 记录日志 
                            log_entry = { 
                                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), 
                                'action': 'file_processed_successfully', 
                                'file_path': file_path, 
                                'ocr_template': ocr_params.get('template', '默认模板'), 
                                'output_dir': ocr_params.get('output_dir', '原目录') 
                            } 
                            self.save_logs(log_entry) 
                        else: 
                            # 任务失败 
                            file_info['status'] = 'failed' 
                            file_info['processing_end_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) 
                            file_info['result'] = 'failed' 
                            file_info['error_message'] = mission_result.get('error_message', '未知错误') 
                            self.failed_files.append(file_info) 
                            
                            # 记录日志 
                            log_entry = { 
                                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), 
                                'action': 'file_processed_failed', 
                                'file_path': file_path, 
                                'error_message': file_info['error_message'] 
                            } 
                            self.save_logs(log_entry) 
                except Exception as e: 
                    # 处理过程中发生错误 
                    file_info['status'] = 'failed' 
                    file_info['processing_end_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) 
                    file_info['result'] = 'failed' 
                    file_info['error_message'] = str(e) 
                    self.failed_files.append(file_info) 
                    
                    # 记录日志 
                    log_entry = { 
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), 
                        'action': 'file_processed_failed', 
                        'file_path': file_path, 
                        'error_message': str(e) 
                    } 
                    self.save_logs(log_entry) 
                
                # 从处理中文件中移除 
                del self.processing_files[file_path] 
                
                # 保存队列 
                self.save_queue() 
        except Exception as e: 
            logger.error(f"处理文件队列失败：{e}") 

    def start_monitoring(self): 
        """启动监控""" 
        try: 
            # 停止所有现有的监控线程 
            for thread in self.monitor_threads: 
                if thread.is_alive(): 
                    thread.stop() 
            self.monitor_threads = [] 
            
            # 为每个监控项启动一个线程 
            for item in self.monitor_items: 
                if item.get('enabled', True): 
                    thread = MonitorThread(item, self.scan_directory) 
                    self.monitor_threads.append(thread) 
                    thread.start() 
            
            # 启动队列处理线程 
            queue_thread = threading.Thread(target=self.process_queue, daemon=True) 
            queue_thread.start() 
            
            logger.info(f"启动了 {len(self.monitor_threads)} 个监控线程") 
        except Exception as e: 
            logger.error(f"启动监控失败：{e}") 

    def stop_monitoring(self): 
        """停止监控""" 
        try: 
            # 停止所有监控线程 
            for thread in self.monitor_threads: 
                if thread.is_alive(): 
                    thread.stop() 
            self.monitor_threads = [] 
            
            logger.info("监控已停止") 
        except Exception as e: 
            logger.error(f"停止监控失败：{e}") 

    def restart_monitoring(self): 
        """重启监控""" 
        try: 
            self.stop_monitoring() 
            time.sleep(1) 
            self.start_monitoring() 
            logger.info("监控已重启") 
        except Exception as e: 
            logger.error(f"重启监控失败：{e}") 

    def add_monitor_item(self, monitor_item): 
        """添加监控项""" 
        try: 
            # 生成唯一的监控项ID 
            item_id = f"monitor_{int(time.time() * 1000)}" 
            monitor_item['id'] = item_id 
            
            # 添加到监控项列表 
            self.monitor_items.append(monitor_item) 
            
            # 保存配置 
            self.save_config() 
            
            # 重启监控 
            self.restart_monitoring() 
            
            logger.info(f"添加监控项成功：{item_id}") 
            return item_id 
        except Exception as e: 
            logger.error(f"添加监控项失败：{e}") 
            return "" 

    def update_monitor_item(self, item_id, monitor_item): 
        """更新监控项""" 
        try: 
            # 找到要更新的监控项 
            for i in range(len(self.monitor_items)): 
                if self.monitor_items[i]['id'] == item_id: 
                    # 更新监控项 
                    self.monitor_items[i].update(monitor_item) 
                    self.monitor_items[i]['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) 
                    
                    # 保存配置 
                    self.save_config() 
                    
                    # 重启监控 
                    self.restart_monitoring() 
                    
                    logger.info(f"更新监控项成功：{item_id}") 
                    return True 
            
            logger.error(f"更新监控项失败：监控项 {item_id} 不存在") 
            return False 
        except Exception as e: 
            logger.error(f"更新监控项失败：{e}") 
            return False 

    def delete_monitor_item(self, item_id): 
        """删除监控项""" 
        try: 
            # 找到要删除的监控项 
            for i in range(len(self.monitor_items)): 
                if self.monitor_items[i]['id'] == item_id: 
                    # 删除监控项 
                    del self.monitor_items[i] 
                    
                    # 保存配置 
                    self.save_config() 
                    
                    # 重启监控 
                    self.restart_monitoring() 
                    
                    logger.info(f"删除监控项成功：{item_id}") 
                    return True 
            
            logger.error(f"删除监控项失败：监控项 {item_id} 不存在") 
            return False 
        except Exception as e: 
            logger.error(f"删除监控项失败：{e}") 
            return False 

    def add_routing_rule(self, routing_rule): 
        """添加路由规则""" 
        try: 
            # 生成唯一的路由规则ID 
            rule_id = f"rule_{int(time.time() * 1000)}" 
            routing_rule['id'] = rule_id 
            
            # 添加到路由规则列表 
            self.routing_rules.append(routing_rule) 
            
            # 保存配置 
            self.save_config() 
            
            logger.info(f"添加路由规则成功：{rule_id}") 
            return rule_id 
        except Exception as e: 
            logger.error(f"添加路由规则失败：{e}") 
            return "" 

    def update_routing_rule(self, rule_id, routing_rule): 
        """更新路由规则""" 
        try: 
            # 找到要更新的路由规则 
            for i in range(len(self.routing_rules)): 
                if self.routing_rules[i]['id'] == rule_id: 
                    # 更新路由规则 
                    self.routing_rules[i].update(routing_rule) 
                    self.routing_rules[i]['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) 
                    
                    # 保存配置 
                    self.save_config() 
                    
                    logger.info(f"更新路由规则成功：{rule_id}") 
                    return True 
            
            logger.error(f"更新路由规则失败：路由规则 {rule_id} 不存在") 
            return False 
        except Exception as e: 
            logger.error(f"更新路由规则失败：{e}") 
            return False 

    def delete_routing_rule(self, rule_id): 
        """删除路由规则""" 
        try: 
            # 找到要删除的路由规则 
            for i in range(len(self.routing_rules)): 
                if self.routing_rules[i]['id'] == rule_id: 
                    # 删除路由规则 
                    del self.routing_rules[i] 
                    
                    # 保存配置 
                    self.save_config() 
                    
                    logger.info(f"删除路由规则成功：{rule_id}") 
                    return True 
            
            logger.error(f"删除路由规则失败：路由规则 {rule_id} 不存在") 
            return False 
        except Exception as e: 
            logger.error(f"删除路由规则失败：{e}") 
            return False 

    def get_queue_status(self): 
        """获取队列状态""" 
        return { 
            'waiting': len(self.file_queue), 
            'processing': len(self.processing_files), 
            'completed': len(self.completed_files), 
            'failed': len(self.failed_files) 
        } 

    def retry_failed_file(self, file_path): 
        """重试失败的文件""" 
        try: 
            # 找到要重试的文件 
            for i in range(len(self.failed_files)): 
                if self.failed_files[i]['file_path'] == file_path: 
                    # 移除失败的文件 
                    file_info = self.failed_files.pop(i) 
                    
                    # 重置文件状态 
                    file_info['status'] = 'waiting' 
                    file_info['added_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) 
                    del file_info['processing_start_time'] 
                    del file_info['processing_end_time'] 
                    del file_info['result'] 
                    del file_info['error_message'] 
                    
                    # 添加到文件队列 
                    self.file_queue.append(file_info) 
                    
                    # 保存队列 
                    self.save_queue() 
                    
                    # 记录日志 
                    log_entry = { 
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), 
                        'action': 'file_retried', 
                        'file_path': file_path 
                    } 
                    self.save_logs(log_entry) 
                    
                    logger.info(f"文件重试成功：{file_path}") 
                    return True 
            
            logger.error(f"文件重试失败：文件 {file_path} 不存在于失败列表中") 
            return False 
        except Exception as e: 
            logger.error(f"文件重试失败：{file_path}，错误：{e}") 
            return False 

    def skip_file(self, file_path): 
        """跳过文件""" 
        try: 
            # 检查文件是否在等待队列中 
            for i in range(len(self.file_queue)): 
                if self.file_queue[i]['file_path'] == file_path: 
                    # 移除文件 
                    file_info = self.file_queue.pop(i) 
                    
                    # 标记文件为已处理 
                    self.mark_file_processed(file_path) 
                    
                    # 记录日志 
                    log_entry = { 
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), 
                        'action': 'file_skipped', 
                        'file_path': file_path 
                    } 
                    self.save_logs(log_entry) 
                    
                    # 保存队列 
                    self.save_queue() 
                    
                    logger.info(f"文件跳过成功：{file_path}") 
                    return True 
            
            # 检查文件是否在处理中 
            if file_path in self.processing_files: 
                # 移除文件 
                file_info = self.processing_files.pop(file_path) 
                
                # 标记文件为已处理 
                self.mark_file_processed(file_path) 
                
                # 记录日志 
                log_entry = { 
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), 
                    'action': 'file_skipped', 
                    'file_path': file_path 
                } 
                self.save_logs(log_entry) 
                
                # 保存队列 
                self.save_queue() 
                
                logger.info(f"文件跳过成功：{file_path}") 
                return True 
            
            logger.error(f"文件跳过失败：文件 {file_path} 不存在于队列中") 
            return False 
        except Exception as e: 
            logger.error(f"文件跳过失败：{file_path}，错误：{e}") 
            return False 

class MonitorThread(threading.Thread): 
    def __init__(self, monitor_item, scan_func): 
        super().__init__() 
        self.monitor_item = monitor_item 
        self.scan_func = scan_func 
        self._stop_event = threading.Event() 
        
    def stop(self): 
        self._stop_event.set() 
        
    def run(self): 
        while not self._stop_event.is_set(): 
            # 扫描监控目录 
            self.scan_func(self.monitor_item) 
            
            # 等待轮询间隔 
            time.sleep(self.monitor_item.get('polling_interval', 60)) 

# 创建一个全局的目录监控器实例 
global_monitor = DirectoryMonitor() 
