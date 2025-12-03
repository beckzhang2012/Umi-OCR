import json
import os
import threading
from PySide2.QtCore import QObject, Signal, Slot, Property
from .mission.mission_multi_ocr import MissionMultiOCR
from .mission.multi_ocr_comparator import MultiOCRComparatorInstance
from .mission.multi_ocr_profile_manager import MultiOCRProfileManagerInstance
from ocr.api import getApiOcr, initOcrPlugins

class MultiOCRBridge(QObject):
    """多引擎OCR对比功能的Python桥接类，用于连接QML界面和Python后端"""
    
    # 信号定义
    availableEnginesChanged = Signal(list)
    comparisonProfilesChanged = Signal(list)
    comparisonResultReady = Signal(object)
    messageReady = Signal(str)
    progressUpdated = Signal(int, int, str)
    multiEngineModeChanged = Signal(bool)
    
    def __init__(self):
        super().__init__()
        self._is_multi_engine_mode = False
        self._selected_engines = []
        self._comparison_strategy = "confidence"
        self._current_comparison_result = None
        
        # 初始化OCR插件
        initOcrPlugins()
        
        # 加载可用引擎
        self._available_engines = self._load_available_engines()
        
        # 初始化方案管理器
        self._profile_manager = MultiOCRProfileManagerInstance
        self._comparison_profiles = self._load_profiles()
        
        # 初始化多引擎OCR任务管理器
        self._multi_ocr = MissionMultiOCR
        
        # 初始化对比器
        self._comparator = MultiOCRComparatorInstance
        
        # 连接信号
        self._multi_ocr.missionProgress.connect(self._on_mission_progress)
        self._multi_ocr.missionComplete.connect(self._on_mission_complete)
        self._multi_ocr.missionError.connect(self._on_mission_error)
    
    # 属性定义
    @Property(bool, notify=multiEngineModeChanged)
    def isMultiEngineMode(self):
        return self._is_multi_engine_mode
    
    @isMultiEngineMode.setter
    def isMultiEngineMode(self, value):
        if self._is_multi_engine_mode != value:
            self._is_multi_engine_mode = value
            self.multiEngineModeChanged.emit(value)
    
    @Property(list, notify=availableEnginesChanged)
    def availableEngines(self):
        return self._available_engines
    
    @Property(list, notify=comparisonProfilesChanged)
    def comparisonProfiles(self):
        return self._comparison_profiles
    
    @Property(str, notify=comparisonProfilesChanged)
    def comparisonStrategy(self):
        return self._comparison_strategy
    
    @comparisonStrategy.setter
    def comparisonStrategy(self, value):
        if self._comparison_strategy != value:
            self._comparison_strategy = value
            self.comparisonProfilesChanged.emit(self._comparison_profiles)
    
    # 槽函数：设置多引擎模式
    @Slot(bool)
    def setMultiEngineMode(self, enabled):
        """设置多引擎模式"""
        self.isMultiEngineMode = enabled
        self.messageReady.emit(f"多引擎模式{'已开启' if enabled else '已关闭'}")
    
    # 槽函数：选择引擎
    @Slot(list)
    def selectEngines(self, engines):
        """选择要使用的OCR引擎"""
        if len(engines) > 3:
            self.messageReady.emit("最多只能选择3个引擎进行对比")
            return
            
        self._selected_engines = engines
        self.messageReady.emit(f"已选择 {len(engines)} 个引擎")
    
    # 槽函数：选择方案
    @Slot(str)
    def selectProfile(self, profile_name):
        """选择多引擎方案"""
        profile = self._profile_manager.get_profile(profile_name)
        if not profile:
            self.messageReady.emit(f"方案 '{profile_name}' 不存在")
            return
        
        # 应用方案设置
        self._selected_engines = profile.engines
        self._comparison_strategy = profile.strategy
        
        # 通知界面更新
        self.comparisonProfilesChanged.emit(self._comparison_profiles)
        self.messageReady.emit(f"已应用方案 '{profile_name}'")
    
    # 槽函数：开始多引擎OCR对比
    @Slot(list, str)
    def startMultiOCRComparison(self, image_paths, output_dir=None):
        """开始多引擎OCR对比任务"""
        if not self._selected_engines or len(self._selected_engines) < 2:
            self.messageReady.emit("请至少选择2个引擎进行对比")
            return
        
        if not image_paths or len(image_paths) == 0:
            self.messageReady.emit("请选择要识别的图片")
            return
        
        # 准备引擎配置
        engine_configs = []
        for engine in self._selected_engines:
            # 获取引擎的默认配置
            try:
                api = getApiOcr(engine.key)
                default_options = api.getLocalOptions() if hasattr(api, 'getLocalOptions') else {}
                engine_configs.append({
                    'engine_key': engine.key,
                    'engine_name': engine.name,
                    'config': default_options
                })
            except Exception as e:
                self.messageReady.emit(f"初始化引擎 {engine.name} 失败: {str(e)}")
                return
        
        # 启动多引擎OCR任务
        self._multi_ocr.set_engines(engine_configs)
        self._multi_ocr.set_comparison_strategy(self._comparison_strategy)
        
        # 准备任务参数
        missions = []
        for image_path in image_paths:
            missions.append({
                'image_path': image_path,
                'output_dir': output_dir or os.path.dirname(image_path)
            })
        
        # 添加任务
        self._multi_ocr.addMissionList(missions)
        self.messageReady.emit(f"已开始多引擎OCR对比任务，共 {len(image_paths)} 张图片")
    
    # 槽函数：执行截图OCR对比
    @Slot(str, str)
    def performScreenshotOCRComparison(self, image_data, output_dir=None):
        """执行截图OCR对比"""
        if not self._selected_engines or len(self._selected_engines) < 2:
            self.messageReady.emit("请至少选择2个引擎进行对比")
            return
        
        # 准备引擎配置
        engine_configs = []
        for engine in self._selected_engines:
            try:
                api = getApiOcr(engine.key)
                default_options = api.getLocalOptions() if hasattr(api, 'getLocalOptions') else {}
                engine_configs.append({
                    'engine_key': engine.key,
                    'engine_name': engine.name,
                    'config': default_options
                })
            except Exception as e:
                self.messageReady.emit(f"初始化引擎 {engine.name} 失败: {str(e)}")
                return
        
        # 启动多引擎OCR任务
        self._multi_ocr.set_engines(engine_configs)
        self._multi_ocr.set_comparison_strategy(self._comparison_strategy)
        
        # 添加截图任务
        mission = {
            'image_base64': image_data,
            'output_dir': output_dir or os.getcwd()
        }
        
        self._multi_ocr.addMissionList([mission])
        self.messageReady.emit("已开始截图OCR对比任务")
    
    # 槽函数：生成对比报告
    @Slot(str, str)
    def generateComparisonReport(self, output_path, report_format="json"):
        """生成对比报告"""
        if not self._current_comparison_result:
            self.messageReady.emit("没有可导出的对比结果")
            return
        
        try:
            self._comparator.export_report(
                self._current_comparison_result,
                output_path,
                report_format
            )
            self.messageReady.emit(f"对比报告已导出到: {output_path}")
        except Exception as e:
            self.messageReady.emit(f"导出对比报告失败: {str(e)}")
    
    # 方案管理相关槽函数
    @Slot()
    def refreshProfiles(self):
        """刷新方案列表"""
        self._comparison_profiles = self._load_profiles()
        self.comparisonProfilesChanged.emit(self._comparison_profiles)
        self.messageReady.emit("方案列表已刷新")
    
    @Slot(object)
    def createProfile(self, profile_data):
        """创建新方案"""
        try:
            profile = self._profile_manager.create_profile(
                name=profile_data.get('name'),
                description=profile_data.get('description', ''),
                engines=self._selected_engines,
                strategy=self._comparison_strategy
            )
            self.refreshProfiles()
            self.messageReady.emit(f"方案 '{profile.name}' 创建成功")
        except Exception as e:
            self.messageReady.emit(f"创建方案失败: {str(e)}")
    
    @Slot(str, str, str, str)
    def updateProfile(self, old_name, new_name, description, strategy):
        """更新方案"""
        try:
            self._profile_manager.update_profile(
                old_name=old_name,
                new_name=new_name,
                description=description,
                strategy=strategy
            )
            self.refreshProfiles()
            self.messageReady.emit(f"方案 '{new_name}' 更新成功")
        except Exception as e:
            self.messageReady.emit(f"更新方案失败: {str(e)}")
    
    @Slot(str)
    def deleteProfile(self, profile_name):
        """删除方案"""
        try:
            self._profile_manager.delete_profile(profile_name)
            self.refreshProfiles()
            self.messageReady.emit(f"方案 '{profile_name}' 删除成功")
        except Exception as e:
            self.messageReady.emit(f"删除方案失败: {str(e)}")
    
    @Slot(str, str, str)
    def duplicateProfile(self, original_name, new_name, description=""):
        """复制方案"""
        try:
            self._profile_manager.duplicate_profile(
                original_name=original_name,
                new_name=new_name,
                new_description=description
            )
            self.refreshProfiles()
            self.messageReady.emit(f"方案 '{new_name}' 复制成功")
        except Exception as e:
            self.messageReady.emit(f"复制方案失败: {str(e)}")
    
    @Slot(str)
    def exportProfile(self, profile_name):
        """导出方案"""
        try:
            # 打开文件选择对话框
            from PySide6.QtWidgets import QFileDialog
            
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "导出多引擎方案",
                f"{profile_name}.json",
                "JSON Files (*.json);;All Files (*)",
                options=options
            )
            
            if file_path:
                self._profile_manager.export_profile(profile_name, file_path)
                self.messageReady.emit(f"方案已导出到: {file_path}")
        except Exception as e:
            self.messageReady.emit(f"导出方案失败: {str(e)}")
    
    @Slot()
    def importProfile(self):
        """导入方案"""
        try:
            # 打开文件选择对话框
            from PySide6.QtWidgets import QFileDialog
            
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "导入多引擎方案",
                "",
                "JSON Files (*.json);;All Files (*)",
                options=options
            )
            
            if file_path:
                self._profile_manager.import_profile(file_path)
                self.refreshProfiles()
                self.messageReady.emit(f"方案已从: {file_path} 导入")
        except Exception as e:
            self.messageReady.emit(f"导入方案失败: {str(e)}")
    
    @Slot(str, str, bool)
    def updateProfileEngines(self, profile_name, engine_key, enabled):
        """更新方案的引擎配置"""
        try:
            profile = self._profile_manager.get_profile(profile_name)
            if not profile:
                self.messageReady.emit(f"方案 '{profile_name}' 不存在")
                return
            
            engine = next((e for e in self._available_engines if e['key'] == engine_key), None)
            if not engine:
                self.messageReady.emit(f"引擎 '{engine_key}' 不存在")
                return
            
            if enabled:
                # 添加引擎（最多3个）
                if len(profile.engines) < 3:
                    profile.add_engine(engine)
                else:
                    self.messageReady.emit("方案中最多只能包含3个引擎")
                    return
            else:
                # 移除引擎（至少保留2个）
                if len(profile.engines) > 2:
                    profile.remove_engine(engine_key)
                else:
                    self.messageReady.emit("方案中至少需要保留2个引擎")
                    return
            
            self._profile_manager.save_profiles()
            self.refreshProfiles()
            self.messageReady.emit(f"方案 '{profile_name}' 引擎配置已更新")
        except Exception as e:
            self.messageReady.emit(f"更新方案引擎配置失败: {str(e)}")
    
    # 私有方法：加载可用引擎
    def _load_available_engines(self):
        """加载可用的OCR引擎列表"""
        try:
            from ocr.api import ApiDict
            engines = []
            for key, api_class in ApiDict.items():
                try:
                    api = api_class()
                    engines.append({
                        'key': key,
                        'name': api.plugin_info['name'] if hasattr(api, 'plugin_info') else key,
                        'description': api.plugin_info['description'] if hasattr(api, 'plugin_info') else ''
                    })
                except Exception:
                    continue
            return engines
        except Exception as e:
            self.messageReady.emit(f"加载可用引擎失败: {str(e)}")
            return []
    
    # 私有方法：加载方案列表
    def _load_profiles(self):
        """加载多引擎方案列表"""
        try:
            profiles = self._profile_manager.get_profiles()
            return [{
                'name': profile.name,
                'description': profile.description,
                'engine_count': len(profile.engines),
                'strategy': profile.strategy,
                'engines': profile.engines
            } for profile in profiles]
        except Exception as e:
            self.messageReady.emit(f"加载方案列表失败: {str(e)}")
            return []
    
    # 私有方法：处理任务进度
    def _on_mission_progress(self, mission_id, current, total, status):
        """处理任务进度更新"""
        self.progressUpdated.emit(current, total, status)
    
    # 私有方法：处理任务完成
    def _on_mission_complete(self, mission_id, result):
        """处理任务完成"""
        try:
            # 获取多引擎OCR结果
            multi_ocr_result = result.get('multi_ocr_result')
            if not multi_ocr_result:
                self.messageReady.emit("未获取到多引擎OCR结果")
                return
            
            # 执行结果对比
            comparison_result = self._comparator.compare_results(multi_ocr_result)
            
            # 保存当前对比结果
            self._current_comparison_result = comparison_result
            
            # 通知界面结果已准备好
            self.comparisonResultReady.emit(comparison_result)
            
            # 显示对比统计信息
            stats = comparison_result.get('statistics', {})
            self.messageReady.emit(
                f"多引擎OCR对比完成！\n" +
                f"总聚类数: {stats.get('total_clusters', 0)}\n" +
                f"差异聚类数: {stats.get('clusters_with_differences', 0)}\n" +
                f"差异率: {stats.get('difference_rate', 0.0):.1%}"
            )
        except Exception as e:
            self.messageReady.emit(f"处理多引擎OCR结果失败: {str(e)}")
    
    # 私有方法：处理任务错误
    def _on_mission_error(self, mission_id, error_message):
        """处理任务错误"""
        self.messageReady.emit(f"多引擎OCR任务出错: {error_message}")
    
    # 槽函数：获取当前对比结果
    @Slot(result=object)
    def getCurrentComparisonResult(self):
        """获取当前对比结果"""
        return self._current_comparison_result
    
    # 槽函数：设置对比策略
    @Slot(str)
    def setComparisonStrategy(self, strategy):
        """设置对比策略"""
        valid_strategies = ['confidence', 'vote', 'merge']
        if strategy not in valid_strategies:
            self.messageReady.emit(f"无效的对比策略: {strategy}")
            return
        
        self._comparison_strategy = strategy
        self.comparisonProfilesChanged.emit(self._comparison_profiles)
        self.messageReady.emit(f"对比策略已设置为: {strategy}")
    
    # 槽函数：获取最佳结果
    @Slot(result=str)
    def getBestResult(self):
        """获取最佳结果"""
        if not self._current_comparison_result:
            return ""
        
        best_result = self._current_comparison_result.get('best_result', {})
        return best_result.get('text', '')
    
    # 槽函数：获取差异详情
    @Slot(result=object)
    def getDifferenceDetails(self):
        """获取差异详情"""
        if not self._current_comparison_result:
            return None
        
        return self._current_comparison_result.get('clusters', [])
    
    # 槽函数：显示消息
    @Slot(str)
    def showMessage(self, message):
        """显示消息"""
        self.messageReady.emit(message)

# 创建全局实例
MultiOCRBridgeInstance = MultiOCRBridge()
