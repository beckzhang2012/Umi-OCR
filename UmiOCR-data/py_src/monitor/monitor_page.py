# ======================================== 
# ============== 监控页面控制器 =============== 
# ======================================== 

from PySide2.QtCore import QObject, Slot, Signal 
from ..tag_pages.tag_pages_connector import TagPageConnector 
from .monitor import global_monitor 
import os 

class MonitorPage(QObject): 
    """监控页面控制器""" 
    
    # 信号：页面初始化完成 
    pageInitialized = Signal() 
    
    # 信号：监控项列表更新 
    monitorItemsUpdated = Signal() 
    
    # 信号：路由规则列表更新 
    routingRulesUpdated = Signal() 
    
    # 信号：队列状态更新 
    queueStatusUpdated = Signal() 
    
    # 信号：文件队列更新 
    fileQueueUpdated = Signal() 
    
    def __init__(self): 
        super().__init__() 
        
        # 注册页面 
        TagPageConnector.instance().registerPage("monitor", self) 
        
        # QML 对象 
        self.qml_obj = None 
        
        # 页面初始化完成 
        self.pageInitialized.emit() 
    
    # ========== 页面连接 ========== 
    @Slot(object) 
    def onPageConnected(self, qml_obj): 
        """页面连接""" 
        self.qml_obj = qml_obj 
        
        # 刷新监控项列表 
        self.refreshMonitorItems() 
        
        # 刷新路由规则列表 
        self.refreshRoutingRules() 
        
        # 刷新队列状态 
        self.refreshQueueStatus() 
        
        # 刷新文件队列 
        self.refreshFileQueue() 
    
    @Slot() 
    def onPageDisconnected(self): 
        """页面断开连接""" 
        self.qml_obj = None 
    
    # ========== 监控项管理 ========== 
    @Slot(str, str, int, int, bool, result=str) 
    def addMonitorItem(self, directory, file_types, polling_interval, recursive_level, enabled): 
        """添加监控项""" 
        try: 
            # 转换文件类型为列表 
            file_types_list = file_types.split(',') 
            file_types_list = [ft.strip().lower() for ft in file_types_list] 
            
            # 创建监控项 
            monitor_item = { 
                'directory': directory, 
                'file_types': file_types_list, 
                'polling_interval': polling_interval, 
                'recursive_level': recursive_level, 
                'enabled': enabled, 
                'created_at': self.getCurrentTime(), 
                'updated_at': self.getCurrentTime() 
            } 
            
            # 添加监控项 
            item_id = global_monitor.add_monitor_item(monitor_item) 
            
            if item_id: 
                # 刷新监控项列表 
                self.refreshMonitorItems() 
                
                return f"添加监控项成功：{item_id}" 
            else: 
                return "添加监控项失败" 
        except Exception as e: 
            return f"添加监控项失败：{e}" 
    
    @Slot(str, str, str, int, int, bool, result=str) 
    def updateMonitorItem(self, item_id, directory, file_types, polling_interval, recursive_level, enabled): 
        """更新监控项""" 
        try: 
            # 转换文件类型为列表 
            file_types_list = file_types.split(',') 
            file_types_list = [ft.strip().lower() for ft in file_types_list] 
            
            # 创建监控项更新信息 
            monitor_item = { 
                'directory': directory, 
                'file_types': file_types_list, 
                'polling_interval': polling_interval, 
                'recursive_level': recursive_level, 
                'enabled': enabled, 
                'updated_at': self.getCurrentTime() 
            } 
            
            # 更新监控项 
            success = global_monitor.update_monitor_item(item_id, monitor_item) 
            
            if success: 
                # 刷新监控项列表 
                self.refreshMonitorItems() 
                
                return f"更新监控项成功：{item_id}" 
            else: 
                return f"更新监控项失败：监控项 {item_id} 不存在" 
        except Exception as e: 
            return f"更新监控项失败：{e}" 
    
    @Slot(str, result=str) 
    def deleteMonitorItem(self, item_id): 
        """删除监控项""" 
        try: 
            # 删除监控项 
            success = global_monitor.delete_monitor_item(item_id) 
            
            if success: 
                # 刷新监控项列表 
                self.refreshMonitorItems() 
                
                return f"删除监控项成功：{item_id}" 
            else: 
                return f"删除监控项失败：监控项 {item_id} 不存在" 
        except Exception as e: 
            return f"删除监控项失败：{e}" 
    
    @Slot() 
    def refreshMonitorItems(self): 
        """刷新监控项列表""" 
        if self.qml_obj: 
            # 获取监控项列表 
            monitor_items = global_monitor.monitor_items 
            
            # 转换为QML可接受的格式 
            qml_monitor_items = [] 
            for item in monitor_items: 
                qml_item = { 
                    'id': item['id'], 
                    'directory': item['directory'], 
                    'file_types': ','.join(item['file_types']), 
                    'polling_interval': item['polling_interval'], 
                    'recursive_level': item['recursive_level'], 
                    'enabled': item['enabled'], 
                    'created_at': item['created_at'], 
                    'updated_at': item['updated_at'] 
                } 
                qml_monitor_items.append(qml_item) 
            
            # 调用QML方法更新监控项列表 
            self.qml_obj.callQml("updateMonitorItems", qml_monitor_items) 
    
    # ========== 路由规则管理 ========== 
    @Slot(str, str, int, int, int, int, str, str, bool, result=str) 
    def addRoutingRule(self, filename_regex, min_size, max_size, min_modified_time, max_modified_time, template, output_dir, enabled): 
        """添加路由规则""" 
        try: 
            # 创建路由规则 
            routing_rule = { 
                'filename_regex': filename_regex, 
                'min_size': min_size, 
                'max_size': max_size, 
                'min_modified_time': min_modified_time, 
                'max_modified_time': max_modified_time, 
                'ocr_params': { 
                    'template': template, 
                    'output_dir': output_dir 
                }, 
                'enabled': enabled, 
                'created_at': self.getCurrentTime(), 
                'updated_at': self.getCurrentTime() 
            } 
            
            # 添加路由规则 
            rule_id = global_monitor.add_routing_rule(routing_rule) 
            
            if rule_id: 
                # 刷新路由规则列表 
                self.refreshRoutingRules() 
                
                return f"添加路由规则成功：{rule_id}" 
            else: 
                return "添加路由规则失败" 
        except Exception as e: 
            return f"添加路由规则失败：{e}" 
    
    @Slot(str, str, str, int, int, int, int, str, str, bool, result=str) 
    def updateRoutingRule(self, rule_id, filename_regex, min_size, max_size, min_modified_time, max_modified_time, template, output_dir, enabled): 
        """更新路由规则""" 
        try: 
            # 创建路由规则更新信息 
            routing_rule = { 
                'filename_regex': filename_regex, 
                'min_size': min_size, 
                'max_size': max_size, 
                'min_modified_time': min_modified_time, 
                'max_modified_time': max_modified_time, 
                'ocr_params': { 
                    'template': template, 
                    'output_dir': output_dir 
                }, 
                'enabled': enabled, 
                'updated_at': self.getCurrentTime() 
            } 
            
            # 更新路由规则 
            success = global_monitor.update_routing_rule(rule_id, routing_rule) 
            
            if success: 
                # 刷新路由规则列表 
                self.refreshRoutingRules() 
                
                return f"更新路由规则成功：{rule_id}" 
            else: 
                return f"更新路由规则失败：路由规则 {rule_id} 不存在" 
        except Exception as e: 
            return f"更新路由规则失败：{e}" 
    
    @Slot(str, result=str) 
    def deleteRoutingRule(self, rule_id): 
        """删除路由规则""" 
        try: 
            # 删除路由规则 
            success = global_monitor.delete_routing_rule(rule_id) 
            
            if success: 
                # 刷新路由规则列表 
                self.refreshRoutingRules() 
                
                return f"删除路由规则成功：{rule_id}" 
            else: 
                return f"删除路由规则失败：路由规则 {rule_id} 不存在" 
        except Exception as e: 
            return f"删除路由规则失败：{e}" 
    
    @Slot() 
    def refreshRoutingRules(self): 
        """刷新路由规则列表""" 
        if self.qml_obj: 
            # 获取路由规则列表 
            routing_rules = global_monitor.routing_rules 
            
            # 转换为QML可接受的格式 
            qml_routing_rules = [] 
            for rule in routing_rules: 
                qml_rule = { 
                    'id': rule['id'], 
                    'filename_regex': rule.get('filename_regex', ''), 
                    'min_size': rule.get('min_size', 0), 
                    'max_size': rule.get('max_size', 0), 
                    'min_modified_time': rule.get('min_modified_time', 0), 
                    'max_modified_time': rule.get('max_modified_time', 0), 
                    'template': rule['ocr_params'].get('template', ''), 
                    'output_dir': rule['ocr_params'].get('output_dir', ''), 
                    'enabled': rule['enabled'], 
                    'created_at': rule['created_at'], 
                    'updated_at': rule['updated_at'] 
                } 
                qml_routing_rules.append(qml_rule) 
            
            # 调用QML方法更新路由规则列表 
            self.qml_obj.callQml("updateRoutingRules", qml_routing_rules) 
    
    # ========== 队列管理 ========== 
    @Slot() 
    def refreshQueueStatus(self): 
        """刷新队列状态""" 
        if self.qml_obj: 
            # 获取队列状态 
            queue_status = global_monitor.get_queue_status() 
            
            # 调用QML方法更新队列状态 
            self.qml_obj.callQml("updateQueueStatus", queue_status['waiting'], queue_status['processing'], queue_status['completed'], queue_status['failed']) 
    
    @Slot() 
    def refreshFileQueue(self): 
        """刷新文件队列""" 
        if self.qml_obj: 
            # 获取文件队列 
            file_queue = global_monitor.file_queue 
            processing_files = global_monitor.processing_files 
            completed_files = global_monitor.completed_files 
            failed_files = global_monitor.failed_files 
            
            # 合并所有文件 
            all_files = [] 
            all_files.extend(file_queue) 
            all_files.extend(processing_files.values()) 
            all_files.extend(completed_files) 
            all_files.extend(failed_files) 
            
            # 转换为QML可接受的格式 
            qml_files = [] 
            for file in all_files: 
                qml_file = { 
                    'file_path': file['file_path'], 
                    'file_name': os.path.basename(file['file_path']), 
                    'status': file['status'], 
                    'added_time': file['added_time'], 
                    'processing_start_time': file.get('processing_start_time', ''), 
                    'processing_end_time': file.get('processing_end_time', ''), 
                    'result': file.get('result', ''), 
                    'error_message': file.get('error_message', '') 
                } 
                qml_files.append(qml_file) 
            
            # 调用QML方法更新文件队列 
            self.qml_obj.callQml("updateFileQueue", qml_files) 
    
    @Slot(str, result=str) 
    def retryFailedFile(self, file_path): 
        """重试失败的文件""" 
        try: 
            # 重试文件 
            success = global_monitor.retry_failed_file(file_path) 
            
            if success: 
                # 刷新文件队列 
                self.refreshFileQueue() 
                
                return f"文件重试成功：{file_path}" 
            else: 
                return f"文件重试失败：文件 {file_path} 不存在于失败列表中" 
        except Exception as e: 
            return f"文件重试失败：{file_path}，错误：{e}" 
    
    @Slot(str, result=str) 
    def skipFile(self, file_path): 
        """跳过文件""" 
        try: 
            # 跳过文件 
            success = global_monitor.skip_file(file_path) 
            
            if success: 
                # 刷新文件队列 
                self.refreshFileQueue() 
                
                return f"文件跳过成功：{file_path}" 
            else: 
                return f"文件跳过失败：文件 {file_path} 不存在于队列中" 
        except Exception as e: 
            return f"文件跳过失败：{file_path}，错误：{e}" 
    
    # ========== 监控控制 ========== 
    @Slot(result=str) 
    def startMonitoring(self): 
        """启动监控""" 
        try: 
            global_monitor.start_monitoring() 
            return "监控启动成功" 
        except Exception as e: 
            return f"监控启动失败：{e}" 
    
    @Slot(result=str) 
    def stopMonitoring(self): 
        """停止监控""" 
        try: 
            global_monitor.stop_monitoring() 
            return "监控停止成功" 
        except Exception as e: 
            return f"监控停止失败：{e}" 
    
    @Slot(result=str) 
    def restartMonitoring(self): 
        """重启监控""" 
        try: 
            global_monitor.restart_monitoring() 
            return "监控重启成功" 
        except Exception as e: 
            return f"监控重启失败：{e}" 
    
    # ========== 辅助方法 ========== 
    def getCurrentTime(self): 
        """获取当前时间""" 
        import time 
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) 
