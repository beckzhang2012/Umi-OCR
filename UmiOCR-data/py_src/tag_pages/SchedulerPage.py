# ========================================
# ============= 任务排程页面 ==============
# ========================================

from umi_tools import getUmiRoot
from ..base.tag_page import Page
from ..scheduler.scheduler import global_scheduler
from umi_log import logger
import json

class SchedulerPage(Page):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 绑定QML信号
        self.bindQmlSignal(self, "qml_add_job", self.py_add_job)
        self.bindQmlSignal(self, "qml_update_job", self.py_update_job)
        self.bindQmlSignal(self, "qml_delete_job", self.py_delete_job)
        self.bindQmlSignal(self, "qml_toggle_job", self.py_toggle_job)
        self.bindQmlSignal(self, "qml_run_job_now", self.py_run_job_now)
        self.bindQmlSignal(self, "qml_get_jobs", self.py_get_jobs)
        self.bindQmlSignal(self, "qml_get_job_logs", self.py_get_job_logs)
        self.bindQmlSignal(self, "qml_export_logs", self.py_export_logs)
        
        # 初始化任务列表
        self.update_jobs_list()

    def update_jobs_list(self):
        """更新任务列表并通知QML"""
        jobs = global_scheduler.get_jobs()
        self.callQmlInMain("updateJobsList", jobs)

    def py_add_job(self, job_info_str):
        """添加新任务"""
        try:
            # 解析任务信息
            job_info = json.loads(job_info_str)
            
            # 添加任务
            job_id = global_scheduler.add_job(job_info)
            
            if job_id:
                # 添加成功，更新任务列表
                self.update_jobs_list()
                self.callQmlInMain("showMessage", f"任务添加成功: {job_id}")
            else:
                self.callQmlInMain("showMessage", "任务添加失败")
        except Exception as e:
            logger.error(f"添加任务失败: {e}")
            self.callQmlInMain("showMessage", f"任务添加失败: {str(e)}")

    def py_update_job(self, job_id, job_info_str):
        """更新任务"""
        try:
            # 解析任务信息
            job_info = json.loads(job_info_str)
            
            # 更新任务
            success = global_scheduler.update_job(job_id, job_info)
            
            if success:
                # 更新成功，更新任务列表
                self.update_jobs_list()
                self.callQmlInMain("showMessage", f"任务更新成功: {job_id}")
            else:
                self.callQmlInMain("showMessage", "任务更新失败")
        except Exception as e:
            logger.error(f"更新任务失败: {e}")
            self.callQmlInMain("showMessage", f"任务更新失败: {str(e)}")

    def py_delete_job(self, job_id):
        """删除任务"""
        try:
            # 删除任务
            success = global_scheduler.delete_job(job_id)
            
            if success:
                # 删除成功，更新任务列表
                self.update_jobs_list()
                self.callQmlInMain("showMessage", f"任务删除成功: {job_id}")
            else:
                self.callQmlInMain("showMessage", "任务删除失败")
        except Exception as e:
            logger.error(f"删除任务失败: {e}")
            self.callQmlInMain("showMessage", f"任务删除失败: {str(e)}")

    def py_toggle_job(self, job_id):
        """切换任务的启用/禁用状态"""
        try:
            # 切换任务状态
            success = global_scheduler.toggle_job(job_id)
            
            if success:
                # 切换成功，更新任务列表
                self.update_jobs_list()
                job = global_scheduler.get_job(job_id)
                status = "启用" if job.get('enabled', False) else "禁用"
                self.callQmlInMain("showMessage", f"任务状态切换成功: {job_id} 现在是 {status} 状态")
            else:
                self.callQmlInMain("showMessage", "任务状态切换失败")
        except Exception as e:
            logger.error(f"切换任务状态失败: {e}")
            self.callQmlInMain("showMessage", f"任务状态切换失败: {str(e)}")

    def py_run_job_now(self, job_id):
        """立即运行任务"""
        try:
            # 立即运行任务
            success = global_scheduler.run_job_now(job_id)
            
            if success:
                self.callQmlInMain("showMessage", f"任务已开始运行: {job_id}")
            else:
                self.callQmlInMain("showMessage", "任务运行失败")
        except Exception as e:
            logger.error(f"运行任务失败: {e}")
            self.callQmlInMain("showMessage", f"任务运行失败: {str(e)}")

    def py_get_jobs(self):
        """获取所有任务"""
        try:
            jobs = global_scheduler.get_jobs()
            self.callQmlInMain("updateJobsList", jobs)
        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
            self.callQmlInMain("showMessage", f"获取任务列表失败: {str(e)}")

    def py_get_job_logs(self, job_id):
        """获取任务日志"""
        try:
            logs = global_scheduler.get_job_logs(job_id)
            self.callQmlInMain("updateJobLogs", job_id, logs)
        except Exception as e:
            logger.error(f"获取任务日志失败: {e}")
            self.callQmlInMain("showMessage", f"获取任务日志失败: {str(e)}")

    def py_export_logs(self):
        """导出日志"""
        try:
            export_file = global_scheduler.export_logs()
            if export_file:
                self.callQmlInMain("showMessage", f"日志导出成功: {export_file}")
            else:
                self.callQmlInMain("showMessage", "日志导出失败")
        except Exception as e:
            logger.error(f"导出日志失败: {e}")
            self.callQmlInMain("showMessage", f"日志导出失败: {str(e)}")
