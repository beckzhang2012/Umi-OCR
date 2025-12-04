# ========================================
# =============== 任务排程器 ===============
# ========================================

import os
import time
import json
import sched
import threading
import croniter
from typing import List, Dict, Any
from umi_log import logger
from ..mission.mission_ocr import MissionOCR

class Scheduler:
    def __init__(self):
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.scheduler_thread = None
        self.jobs = {}  # 存储所有任务：{job_id: job_info}
        self.job_logs = {}  # 存储所有任务日志：{job_id: [log1, log2, ...]}
        self.scheduled_events = {}  # 存储已调度的事件：{job_id: event}
        
        # 配置文件路径
        self.config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'config')
        self.jobs_file = os.path.join(self.config_dir, 'scheduler_jobs.json')
        self.logs_file = os.path.join(self.config_dir, 'scheduler_logs.json')
        
        # 确保配置目录存在
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        
        # 加载任务和日志
        self.load_jobs()
        self.load_logs()
        
        # 启动调度器线程
        self.start_scheduler_thread()
        
        # 调度所有启用的任务
        for job_id in self.jobs:
            if self.jobs[job_id].get('enabled', True):
                self.schedule_job(job_id)

    def start_scheduler_thread(self):
        """启动调度器线程"""
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.scheduler_thread = threading.Thread(target=self.scheduler.run, daemon=True)
            self.scheduler_thread.start()

    def load_jobs(self):
        """从JSON文件加载任务"""
        try:
            if os.path.exists(self.jobs_file):
                with open(self.jobs_file, 'r', encoding='utf-8') as f:
                    self.jobs = json.load(f)
                logger.info(f"加载了 {len(self.jobs)} 个任务")
        except Exception as e:
            logger.error(f"加载任务失败：{e}")

    def save_jobs(self):
        """将任务保存到JSON文件"""
        try:
            with open(self.jobs_file, 'w', encoding='utf-8') as f:
                json.dump(self.jobs, f, ensure_ascii=False, indent=4)
            logger.info(f"保存了 {len(self.jobs)} 个任务")
        except Exception as e:
            logger.error(f"保存任务失败：{e}")

    def load_logs(self):
        """从JSON文件加载日志"""
        try:
            if os.path.exists(self.logs_file):
                with open(self.logs_file, 'r', encoding='utf-8') as f:
                    self.job_logs = json.load(f)
                logger.info(f"加载了 {len(self.job_logs)} 个任务的日志")
        except Exception as e:
            logger.error(f"加载日志失败：{e}")

    def save_logs(self):
        """将日志保存到JSON文件"""
        try:
            with open(self.logs_file, 'w', encoding='utf-8') as f:
                json.dump(self.job_logs, f, ensure_ascii=False, indent=4)
            logger.info(f"保存了日志")
        except Exception as e:
            logger.error(f"保存日志失败：{e}")

    def calculate_next_execution_time(self, schedule_type: str, schedule_value: str) -> float:
        """计算下次执行时间"""
        current_time = time.time()
        
        if schedule_type == "once":
            # 一次性任务：schedule_value 是一个时间戳
            next_time = float(schedule_value)
            if next_time < current_time:
                # 如果指定的时间已经过去，返回当前时间（立即执行）
                next_time = current_time
            return next_time
        
        elif schedule_type == "daily":
            # 每天任务：schedule_value 是一个时间字符串，格式为 "HH:MM"
            hour, minute = map(int, schedule_value.split(':'))
            next_time = time.mktime(time.localtime(current_time)[:3] + (hour, minute, 0, 0, 0, 0))
            if next_time < current_time:
                # 如果今天的时间已经过去，明天同一时间执行
                next_time += 24 * 60 * 60
            return next_time
        
        elif schedule_type == "weekly":
            # 每周任务：schedule_value 是一个字符串，格式为 "周几 HH:MM"，其中周几是 0-6（0=周日）
            day_of_week, time_str = schedule_value.split(' ')
            day_of_week = int(day_of_week)
            hour, minute = map(int, time_str.split(':'))
            
            # 计算本周指定时间的时间戳
            current_localtime = time.localtime(current_time)
            current_day_of_week = current_localtime.tm_wday  # 0=周一，1=周二，...，6=周日
            # 转换为 0=周日，1=周一，...，6=周六
            current_day_of_week = (current_day_of_week + 1) % 7
            
            days_until = (day_of_week - current_day_of_week) % 7
            next_time = time.mktime(current_localtime[:3] + (hour, minute, 0, 0, 0, 0))
            next_time += days_until * 24 * 60 * 60
            
            # 如果计算的时间已经过去，下周同一时间执行
            if next_time < current_time:
                next_time += 7 * 24 * 60 * 60
            
            return next_time
        
        elif schedule_type == "cron":
            # 自定义Cron表达式：schedule_value 是一个Cron表达式
            try:
                cron = croniter.croniter(schedule_value, current_time)
                next_time = cron.get_next(float)
                return next_time
            except Exception as e:
                logger.error(f"解析Cron表达式失败：{e}")
                # 如果解析失败，返回当前时间（立即执行）
                return current_time
        
        else:
            logger.error(f"未知的调度类型：{schedule_type}")
            # 如果调度类型未知，返回当前时间（立即执行）
            return current_time

    def schedule_job(self, job_id: str):
        """调度一个任务"""
        try:
            if job_id not in self.jobs:
                logger.error(f"调度任务失败：任务 {job_id} 不存在")
                return
            
            # 取消之前的调度（如果有的话）
            if job_id in self.scheduled_events:
                self.scheduler.cancel(self.scheduled_events[job_id])
                del self.scheduled_events[job_id]
            
            # 获取任务信息
            job_info = self.jobs[job_id]
            
            # 计算下次执行时间
            next_exec_time = self.calculate_next_execution_time(job_info['schedule_type'], job_info['schedule_value'])
            self.jobs[job_id]['next_execution_time'] = next_exec_time
            
            # 调度任务
            event = self.scheduler.enterabs(next_exec_time, 1, self.execute_job, (job_id,))
            self.scheduled_events[job_id] = event
            
            logger.info(f"调度任务成功：{job_id}，下次执行时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_exec_time))}")
        except Exception as e:
            logger.error(f"调度任务失败：{e}")

    def execute_job(self, job_id: str):
        """执行一个任务"""
        try:
            if job_id not in self.jobs:
                logger.error(f"执行任务失败：任务 {job_id} 不存在")
                return
            
            # 获取任务信息
            job_info = self.jobs[job_id]
            
            # 记录任务开始时间
            start_time = time.time()
            start_datetime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
            
            logger.info(f"开始执行任务：{job_id} ({job_info['name']})")
            
            # 执行任务
            result = self.run_job(job_info)
            
            # 记录任务结束时间
            end_time = time.time()
            end_datetime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))
            
            # 计算任务执行时间
            execution_time = end_time - start_time
            
            # 记录任务日志
            log_entry = {
                'start_time': start_datetime,
                'end_time': end_datetime,
                'execution_time': execution_time,
                'result': result['status'],
                'success_count': result.get('success_count', 0),
                'failure_count': result.get('failure_count', 0),
                'error_message': result.get('error_message', '')
            }
            
            if job_id not in self.job_logs:
                self.job_logs[job_id] = []
            self.job_logs[job_id].append(log_entry)
            
            # 保存日志
            self.save_logs()
            
            logger.info(f"任务执行完成：{job_id} ({job_info['name']})，结果：{result['status']}")
            
            # 对于不是一次性的任务，重新调度它
            if job_info['schedule_type'] != 'once':
                self.schedule_job(job_id)
        except Exception as e:
            logger.error(f"执行任务失败：{e}")

    def run_job(self, job_info: Dict[str, Any]) -> Dict[str, Any]:
        """运行具体的任务逻辑"""
        try:
            if job_info['type'] == 'batch_ocr':
                # 批量OCR任务
                return self.run_batch_ocr_job(job_info)
            elif job_info['type'] == 'screenshot_ocr':
                # 截图OCR任务
                return self.run_screenshot_ocr_job(job_info)
            else:
                logger.error(f"未知的任务类型：{job_info['type']}")
                return {
                    'status': 'failed',
                    'error_message': f'未知的任务类型：{job_info['type']}'
                }
        except Exception as e:
            logger.error(f"运行任务失败：{e}")
            return {
                'status': 'failed',
                'error_message': str(e)
            }

    def run_batch_ocr_job(self, job_info: Dict[str, Any]) -> Dict[str, Any]:
        """运行批量OCR任务"""
        try:
            # 收集所有目标文件夹中的图片文件
            image_files = []
            for folder in job_info['target_folders']:
                if os.path.exists(folder):
                    for root, _, files in os.walk(folder):
                        for file in files:
                            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff')):
                                image_files.append(os.path.join(root, file))
                else:
                    logger.warning(f"目标文件夹不存在：{folder}")
            
            if not image_files:
                logger.info(f"批量OCR任务没有找到任何图片文件")
                return {
                    'status': 'success',
                    'success_count': 0,
                    'failure_count': 0
                }
            
            # 构造任务参数
            argd = {
                # OCR模板参数
                'ocr.template': job_info['ocr_template'],
                
                # 任务参数
                'mission.dirType': 'source',  # 保存到原目录
                'mission.ignoreBlank': True,  # 忽略空白文件
                'mission.filesType.txt': True,  # 输出为TXT文件
                
                # 并发限制参数
                'mission.concurrency': job_info['concurrency_limit']
            }
            
            # 构造任务信息
            msnInfo = {
                'onStart': lambda msnInfo: logger.info(f"批量OCR任务队列开始"),
                'onReady': lambda msnInfo, msn: logger.info(f"单个批量OCR任务准备：{msn['path']}"),
                'onGet': lambda msnInfo, msn, res: logger.info(f"单个批量OCR任务完成：{msn['path']}"),
                'onEnd': lambda msnInfo, msg: logger.info(f"批量OCR任务队列完成：{msg}"),
                'argd': argd,
            }
            
            # 路径转为任务列表格式，加载进任务管理器
            msnList = [{"path": x} for x in image_files]
            msnID = MissionOCR.addMissionList(msnInfo, msnList)
            
            if msnID.startswith("[Error]"):
                logger.error(f"添加批量OCR任务失败：{msnID}")
                return {
                    'status': 'failed',
                    'error_message': msnID
                }
            else:
                logger.info(f"添加批量OCR任务成功：{msnID}")
                
                # 等待任务完成
                while MissionOCR.isMissionListRunning(msnID):
                    time.sleep(1)
                
                # 获取任务结果
                mission_result = MissionOCR.getMissionListResult(msnID)
                
                return {
                    'status': 'success',
                    'success_count': mission_result.get('success_count', 0),
                    'failure_count': mission_result.get('failure_count', 0)
                }
        except Exception as e:
            logger.error(f"运行批量OCR任务失败：{e}")
            return {
                'status': 'failed',
                'error_message': str(e)
            }

    def run_screenshot_ocr_job(self, job_info: Dict[str, Any]) -> Dict[str, Any]:
        """运行截图OCR任务"""
        try:
            # 截图OCR任务的实现
            # 这里需要根据实际的截图OCR实现来编写
            logger.info(f"运行截图OCR任务：{job_info['name']}")
            
            # 暂时返回一个成功的结果
            return {
                'status': 'success',
                'success_count': 1,
                'failure_count': 0
            }
        except Exception as e:
            logger.error(f"运行截图OCR任务失败：{e}")
            return {
                'status': 'failed',
                'error_message': str(e)
            }

    def add_job(self, job_info: Dict[str, Any]) -> str:
        """
        添加一个新任务
        
        Args:
            job_info: 任务信息字典，包含以下字段：
                - name: 任务名称
                - type: 任务类型（"batch_ocr" 或 "screenshot_ocr"）
                - schedule_type: 调度类型（"once"、"daily"、"weekly"、"cron"）
                - schedule_value: 调度值（根据schedule_type不同而不同）
                - ocr_template: OCR模板名称
                - target_folders: 目标文件夹列表
                - retry_strategy: 失败重试策略（"none"、"retry_once"、"retry_always"）
                - concurrency_limit: 并发限制（整数）
                - enabled: 是否启用任务（布尔值，可选，默认True）
        
        Returns:
            任务ID，如果添加失败则返回空字符串
        """
        try:
            # 生成唯一的任务ID
            job_id = f"job_{int(time.time() * 1000)}"
            
            # 计算下次执行时间
            next_exec_time = self.calculate_next_execution_time(job_info['schedule_type'], job_info['schedule_value'])
            
            # 构造完整的任务信息
            full_job_info = {
                'id': job_id,
                'name': job_info['name'],
                'type': job_info['type'],
                'schedule_type': job_info['schedule_type'],
                'schedule_value': job_info['schedule_value'],
                'next_execution_time': next_exec_time,
                'ocr_template': job_info['ocr_template'],
                'target_folders': job_info['target_folders'],
                'retry_strategy': job_info['retry_strategy'],
                'concurrency_limit': job_info['concurrency_limit'],
                'enabled': job_info.get('enabled', True),
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                'updated_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            }
            
            # 添加到任务字典
            self.jobs[job_id] = full_job_info
            
            # 保存任务
            self.save_jobs()
            
            # 如果任务是启用的，则调度它
            if full_job_info['enabled']:
                self.schedule_job(job_id)
            
            logger.info(f"添加任务成功：{job_id}")
            return job_id
        except Exception as e:
            logger.error(f"添加任务失败：{e}")
            return ""

    def update_job(self, job_id: str, job_info: Dict[str, Any]) -> bool:
        """更新一个任务"""
        try:
            if job_id not in self.jobs:
                logger.error(f"更新任务失败：任务 {job_id} 不存在")
                return False
            
            # 取消之前的调度（如果有的话）
            if job_id in self.scheduled_events:
                self.scheduler.cancel(self.scheduled_events[job_id])
                del self.scheduled_events[job_id]
            
            # 更新任务信息
            self.jobs[job_id].update(job_info)
            self.jobs[job_id]['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            
            # 重新计算下次执行时间
            if 'schedule_type' in job_info or 'schedule_value' in job_info:
                schedule_type = job_info.get('schedule_type', self.jobs[job_id]['schedule_type'])
                schedule_value = job_info.get('schedule_value', self.jobs[job_id]['schedule_value'])
                next_exec_time = self.calculate_next_execution_time(schedule_type, schedule_value)
                self.jobs[job_id]['next_execution_time'] = next_exec_time
            
            # 保存任务
            self.save_jobs()
            
            # 如果任务是启用的，则重新调度它
            if self.jobs[job_id]['enabled']:
                self.schedule_job(job_id)
            
            logger.info(f"更新任务成功：{job_id}")
            return True
        except Exception as e:
            logger.error(f"更新任务失败：{e}")
            return False

    def delete_job(self, job_id: str) -> bool:
        """删除一个任务"""
        try:
            if job_id not in self.jobs:
                logger.error(f"删除任务失败：任务 {job_id} 不存在")
                return False
            
            # 取消调度（如果有的话）
            if job_id in self.scheduled_events:
                self.scheduler.cancel(self.scheduled_events[job_id])
                del self.scheduled_events[job_id]
            
            # 删除任务
            del self.jobs[job_id]
            
            # 如果有日志，也删除日志
            if job_id in self.job_logs:
                del self.job_logs[job_id]
            
            # 保存任务和日志
            self.save_jobs()
            self.save_logs()
            
            logger.info(f"删除任务成功：{job_id}")
            return True
        except Exception as e:
            logger.error(f"删除任务失败：{e}")
            return False

    def toggle_job(self, job_id: str) -> bool:
        """切换任务的启用/禁用状态"""
        try:
            if job_id not in self.jobs:
                logger.error(f"切换任务状态失败：任务 {job_id} 不存在")
                return False
            
            # 切换状态
            self.jobs[job_id]['enabled'] = not self.jobs[job_id]['enabled']
            self.jobs[job_id]['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            
            if self.jobs[job_id]['enabled']:
                # 启用任务，调度它
                self.schedule_job(job_id)
            else:
                # 禁用任务，取消调度
                if job_id in self.scheduled_events:
                    self.scheduler.cancel(self.scheduled_events[job_id])
                    del self.scheduled_events[job_id]
            
            # 保存任务
            self.save_jobs()
            
            logger.info(f"切换任务状态成功：{job_id}，新状态：{'启用' if self.jobs[job_id]['enabled'] else '禁用'}")
            return True
        except Exception as e:
            logger.error(f"切换任务状态失败：{e}")
            return False

    def run_job_now(self, job_id: str) -> bool:
        """立即运行一个任务"""
        try:
            if job_id not in self.jobs:
                logger.error(f"立即运行任务失败：任务 {job_id} 不存在")
                return False
            
            # 执行任务
            threading.Thread(target=self.execute_job, args=(job_id,), daemon=True).start()
            
            logger.info(f"立即运行任务成功：{job_id}")
            return True
        except Exception as e:
            logger.error(f"立即运行任务失败：{e}")
            return False

    def get_jobs(self) -> List[Dict[str, Any]]:
        """获取所有任务列表"""
        return list(self.jobs.values())

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """获取一个任务的详细信息"""
        return self.jobs.get(job_id, {})

    def get_job_logs(self, job_id: str) -> List[Dict[str, Any]]:
        """获取一个任务的所有日志"""
        return self.job_logs.get(job_id, [])

    def export_logs(self) -> str:
        """导出所有日志到JSON文件"""
        try:
            # 生成导出文件路径
            export_file = os.path.join(self.config_dir, f"scheduler_logs_export_{int(time.time())}.json")
            
            # 导出日志
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.job_logs, f, ensure_ascii=False, indent=4)
            
            logger.info(f"导出日志成功：{export_file}")
            return export_file
        except Exception as e:
            logger.error(f"导出日志失败：{e}")
            return ""

# 创建一个全局的调度器实例
global_scheduler = Scheduler()
