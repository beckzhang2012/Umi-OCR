from PySide2.QtCore import QObject, Signal, Slot, Property
from ..post_processing import PostProcessingManagerInstance
from typing import List, Dict, Any

class PostProcessingController(QObject):
    """后处理规则页面控制器"""
    
    # 信号
    ruleSetsChanged = Signal(list)
    currentSetChanged = Signal(str)
    previewResultsChanged = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = PostProcessingManagerInstance
        self._preview_text = ""
        self._current_preview_results = []
        
        # 连接管理器信号
        self._manager.ruleSetsChanged.connect(self._on_rule_sets_changed)
        self._manager.currentSetChanged.connect(self._on_current_set_changed)
    
    def _on_rule_sets_changed(self, rule_sets: List[Dict[str, Any]]):
        """规则集变化回调"""
        self.ruleSetsChanged.emit(rule_sets)
    
    def _on_current_set_changed(self, set_id: str):
        """当前规则集变化回调"""
        self.currentSetChanged.emit(set_id)
    
    # 属性访问器
    @Property(list, notify=ruleSetsChanged)
    def ruleSets(self):
        return self._manager.ruleSets
    
    @Property(str, notify=currentSetChanged)
    def currentSetId(self):
        return self._manager.currentSetId
    
    @currentSetId.setter
    def currentSetId(self, value: str):
        self._manager.currentSetId = value
    
    @Property(list, notify=previewResultsChanged)
    def previewResults(self):
        return self._current_preview_results
    
    @Slot(str, result=dict)
    def getRuleSet(self, set_id: str) -> Dict[str, Any]:
        """获取规则集"""
        return self._manager.getRuleSet(set_id)
    
    @Slot(dict, result=str)
    def addRuleSet(self, set_data: Dict[str, Any]) -> str:
        """添加规则集"""
        return self._manager.addRuleSet(set_data)
    
    @Slot(str, dict)
    def updateRuleSet(self, set_id: str, set_data: Dict[str, Any]):
        """更新规则集"""
        self._manager.updateRuleSet(set_id, set_data)
    
    @Slot(str)
    def deleteRuleSet(self, set_id: str):
        """删除规则集"""
        self._manager.deleteRuleSet(set_id)
    
    @Slot(str, str, str, result=str)
    def addStepToSet(self, set_id: str, step_type: str, step_name: str) -> str:
        """向规则集添加步骤"""
        return self._manager.addStepToSet(set_id, step_type, step_name)
    
    @Slot(str, str)
    def removeStepFromSet(self, set_id: str, step_id: str):
        """从规则集移除步骤"""
        self._manager.removeStepFromSet(set_id, step_id)
    
    @Slot(str, int, int)
    def moveStepInSet(self, set_id: str, from_index: int, to_index: int):
        """移动规则集中的步骤"""
        self._manager.moveStepInSet(set_id, from_index, to_index)
    
    @Slot(str, str)
    def toggleStepInSet(self, set_id: str, step_id: str):
        """切换规则集中步骤的启用状态"""
        self._manager.toggleStepInSet(set_id, step_id)
    
    @Slot(str, str, dict)
    def updateStepInSet(self, set_id: str, step_id: str, step_data: Dict[str, Any]):
        """更新规则集中的步骤"""
        self._manager.updateStepInSet(set_id, step_id, step_data)
    
    @Slot(str, str)
    def previewText(self, set_id: str, text: str):
        """预览文本处理结果"""
        self._preview_text = text
        self._current_preview_results = self._manager.processTextWithPreview(set_id, text)
        self.previewResultsChanged.emit(self._current_preview_results)
    
    @Slot(str, str, result=str)
    def processText(self, set_id: str, text: str) -> str:
        """处理文本"""
        return self._manager.processText(set_id, text)
    
    @Slot(str, result=list)
    def getRuleSetsForType(self, ocr_type: str) -> List[Dict[str, Any]]:
        """获取指定OCR类型的规则集"""
        return self._manager.getRuleSetsForType(ocr_type)
    
    @Slot(str, str, result=str)
    def exportRuleSet(self, set_id: str, file_path: str) -> str:
        """导出规则集"""
        return self._manager.exportRuleSet(set_id, file_path)
    
    @Slot(str, result=str)
    def importRuleSet(self, file_path: str) -> str:
        """导入规则集"""
        return self._manager.importRuleSet(file_path)
    
    @Slot(result=list)
    def getAvailableStepTypes(self) -> List[Dict[str, Any]]:
        """获取可用的规则步骤类型"""
        from ..post_processing.post_processing import RuleStep
        
        return [
            {
                "type": RuleStep.TYPE_REGEX_REPLACE,
                "name": "正则替换",
                "description": "使用正则表达式替换文本",
                "default_params": {
                    "pattern": "",
                    "replacement": "",
                    "flags": 0
                }
            },
            {
                "type": RuleStep.TYPE_CASE_CONVERT,
                "name": "大小写转换",
                "description": "转换文本大小写",
                "default_params": {
                    "case_type": RuleStep.CASE_UPPER
                }
            },
            {
                "type": RuleStep.TYPE_MERGE_EMPTY_LINES,
                "name": "合并空行",
                "description": "合并连续的空行",
                "default_params": {}
            },
            {
                "type": RuleStep.TYPE_REMOVE_EMPTY_LINES,
                "name": "移除空行",
                "description": "移除所有空行",
                "default_params": {}
            },
            {
                "type": RuleStep.TYPE_FULL_WIDTH_TO_HALF,
                "name": "全角转半角",
                "description": "将全角字符转换为半角字符",
                "default_params": {}
            },
            {
                "type": RuleStep.TYPE_HALF_WIDTH_TO_FULL,
                "name": "半角转全角",
                "description": "将半角字符转换为全角字符",
                "default_params": {}
            },
            {
                "type": RuleStep.TYPE_REMOVE_NUMBERS,
                "name": "移除数字",
                "description": "移除文本中的所有数字",
                "default_params": {}
            },
            {
                "type": RuleStep.TYPE_REMOVE_PUNCTUATION,
                "name": "移除标点",
                "description": "移除文本中的标点符号",
                "default_params": {
                    "keep_chinese": False,
                    "keep_english": False
                }
            },
            {
                "type": RuleStep.TYPE_TRIM_LINES,
                "name": "修剪行首尾",
                "description": "修剪每行首尾的空格",
                "default_params": {}
            },
            {
                "type": RuleStep.TYPE_CUSTOM_PYTHON,
                "name": "自定义Python",
                "description": "使用自定义Python代码处理文本",
                "default_params": {
                    "code": """def process(text):
    # 在此处编写自定义处理逻辑
    # 示例：返回原始文本
    return text"""
                }
            }
        ]
    
    @Slot(result=list)
    def getCaseTypes(self) -> List[Dict[str, str]]:
        """获取大小写转换类型"""
        from ..post_processing.post_processing import RuleStep
        
        return [
            {"value": RuleStep.CASE_UPPER, "name": "全部大写"},
            {"value": RuleStep.CASE_LOWER, "name": "全部小写"},
            {"value": RuleStep.CASE_TITLE, "name": "首字母大写"}
        ]
    
    @Slot(result=list)
    def getOCRTypes(self) -> List[Dict[str, str]]:
        """获取OCR类型"""
        return [
            {"value": "screenshot", "name": "截图OCR"},
            {"value": "batch", "name": "批量OCR"},
            {"value": "document", "name": "文档OCR"}
        ]
    
    @Slot(str, result=list)
    def getRuleSetsByOCRType(self, ocr_type: str) -> List[Dict[str, Any]]:
        """根据OCR类型获取绑定的规则集"""
        return self._manager.get_rule_sets_by_ocr_type(ocr_type)
    
    @Slot(str, str, result=str)
    def applyRuleSetsToText(self, text: str, ocr_type: str) -> str:
        """对指定OCR类型的文本应用所有绑定的规则集"""
        return self._manager.apply_rule_sets_to_text(text, ocr_type)
    
    @Slot(str, str, result=str)
    def addBoundOCRType(self, rule_set_id: str, ocr_type: str) -> str:
        """为规则集添加绑定的OCR类型"""
        return self._manager.add_bound_ocr_type(rule_set_id, ocr_type)
    
    @Slot(str, str)
    def removeBoundOCRType(self, rule_set_id: str, ocr_type: str):
        """移除规则集绑定的OCR类型"""
        self._manager.remove_bound_ocr_type(rule_set_id, ocr_type)
    
    @Slot(str, str, result=bool)
    def isRuleSetBoundToOCRType(self, rule_set_id: str, ocr_type: str) -> bool:
        """检查规则集是否绑定到指定的OCR类型"""
        return self._manager.is_rule_set_bound_to_ocr_type(rule_set_id, ocr_type)

def create_controller():
    """创建控制器实例"""
    return PostProcessingController()