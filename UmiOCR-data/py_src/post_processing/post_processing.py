import json
import re
import uuid
import os
from typing import List, Dict, Any, Optional
from PySide2.QtCore import QObject, Signal, Slot, Property

class RuleStep(QObject):
    """规则步骤模型"""
    
    # 规则类型
    TYPE_REGEX_REPLACE = "regex_replace"
    TYPE_CASE_CONVERT = "case_convert"
    TYPE_MERGE_EMPTY_LINES = "merge_empty_lines"
    TYPE_REMOVE_EMPTY_LINES = "remove_empty_lines"
    TYPE_FULL_WIDTH_TO_HALF = "full_width_to_half"
    TYPE_HALF_WIDTH_TO_FULL = "half_width_to_full"
    TYPE_REMOVE_NUMBERS = "remove_numbers"
    TYPE_REMOVE_PUNCTUATION = "remove_punctuation"
    TYPE_TRIM_LINES = "trim_lines"
    TYPE_CUSTOM_PYTHON = "custom_python"
    
    # 大小写转换选项
    CASE_UPPER = "upper"
    CASE_LOWER = "lower"
    CASE_TITLE = "title"
    
    # 信号
    idChanged = Signal(str)
    nameChanged = Signal(str)
    typeChanged = Signal(str)
    enabledChanged = Signal(bool)
    paramsChanged = Signal(dict)
    
    def __init__(self, 
                 step_id: Optional[str] = None,
                 name: str = "",
                 step_type: str = TYPE_REGEX_REPLACE,
                 enabled: bool = True,
                 params: Optional[Dict[str, Any]] = None,
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        self._id = step_id or str(uuid.uuid4())
        self._name = name
        self._type = step_type
        self._enabled = enabled
        self._params = params or {}
        
        # 设置默认参数
        self._set_default_params()
    
    def _set_default_params(self):
        """设置默认参数"""
        if self._type == self.TYPE_REGEX_REPLACE:
            if "pattern" not in self._params:
                self._params["pattern"] = ""
            if "replacement" not in self._params:
                self._params["replacement"] = ""
            if "flags" not in self._params:
                self._params["flags"] = 0
        elif self._type == self.TYPE_CASE_CONVERT:
            if "case_type" not in self._params:
                self._params["case_type"] = self.CASE_UPPER
        elif self._type == self.TYPE_CUSTOM_PYTHON:
            if "code" not in self._params:
                self._params["code"] = """def process(text):
    # 在此处编写自定义处理逻辑
    # 示例：返回原始文本
    return text"""
    
    # 属性访问器
    @Property(str, notify=idChanged)
    def id(self):
        return self._id
    
    @Property(str, notify=nameChanged)
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value: str):
        if self._name != value:
            self._name = value
            self.nameChanged.emit(value)
    
    @Property(str, notify=typeChanged)
    def type(self):
        return self._type
    
    @type.setter
    def type(self, value: str):
        if self._type != value:
            self._type = value
            self._set_default_params()
            self.typeChanged.emit(value)
    
    @Property(bool, notify=enabledChanged)
    def enabled(self):
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        if self._enabled != value:
            self._enabled = value
            self.enabledChanged.emit(value)
    
    @Property(dict, notify=paramsChanged)
    def params(self):
        return self._params
    
    @params.setter
    def params(self, value: Dict[str, Any]):
        if self._params != value:
            self._params = value
            self.paramsChanged.emit(value)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self._id,
            "name": self._name,
            "type": self._type,
            "enabled": self._enabled,
            "params": self._params
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleStep':
        """从字典创建"""
        return cls(
            step_id=data.get("id"),
            name=data.get("name", ""),
            step_type=data.get("type", cls.TYPE_REGEX_REPLACE),
            enabled=data.get("enabled", True),
            params=data.get("params", {})
        )

class RuleSet(QObject):
    """规则集模型"""
    
    # 信号
    idChanged = Signal(str)
    nameChanged = Signal(str)
    descriptionChanged = Signal(str)
    stepsChanged = Signal(list)
    bindTypesChanged = Signal(list)
    
    def __init__(self, 
                 set_id: Optional[str] = None,
                 name: str = "",
                 description: str = "",
                 steps: Optional[List[RuleStep]] = None,
                 bind_types: Optional[List[str]] = None,
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        self._id = set_id or str(uuid.uuid4())
        self._name = name
        self._description = description
        self._steps = steps or []
        self._bind_types = bind_types or []
    
    def get_bound_ocr_types(self):
        """获取绑定的OCR类型列表"""
        return self._bind_types
    
    def add_bound_ocr_type(self, ocr_type):
        """添加绑定的OCR类型"""
        if ocr_type not in self._bind_types:
            self._bind_types.append(ocr_type)
            self.bindTypesChanged.emit(self._bind_types)
    
    def remove_bound_ocr_type(self, ocr_type):
        """移除绑定的OCR类型"""
        if ocr_type in self._bind_types:
            self._bind_types.remove(ocr_type)
            self.bindTypesChanged.emit(self._bind_types)
    
    def is_bound_to_ocr_type(self, ocr_type):
        """检查是否绑定到指定的OCR类型"""
        return ocr_type in self._bind_types
    
    # 属性访问器
    @Property(str, notify=idChanged)
    def id(self):
        return self._id
    
    @Property(str, notify=nameChanged)
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value: str):
        if self._name != value:
            self._name = value
            self.nameChanged.emit(value)
    
    @Property(str, notify=descriptionChanged)
    def description(self):
        return self._description
    
    @description.setter
    def description(self, value: str):
        if self._description != value:
            self._description = value
            self.descriptionChanged.emit(value)
    
    @Property(list, notify=stepsChanged)
    def steps(self):
        return [step.to_dict() for step in self._steps]
    
    @steps.setter
    def steps(self, value: List[Dict[str, Any]]):
        self._steps = [RuleStep.from_dict(data) for data in value]
        self.stepsChanged.emit(self.steps)
    
    @Property(list, notify=bindTypesChanged)
    def bindTypes(self):
        return self._bind_types
    
    @bindTypes.setter
    def bindTypes(self, value: List[str]):
        if self._bind_types != value:
            self._bind_types = value
            self.bindTypesChanged.emit(value)
    
    def add_step(self, step: RuleStep):
        """添加步骤"""
        self._steps.append(step)
        self.stepsChanged.emit(self.steps)
    
    def remove_step(self, step_id: str):
        """移除步骤"""
        self._steps = [step for step in self._steps if step.id != step_id]
        self.stepsChanged.emit(self.steps)
    
    def move_step(self, from_index: int, to_index: int):
        """移动步骤"""
        if 0 <= from_index < len(self._steps) and 0 <= to_index < len(self._steps):
            step = self._steps.pop(from_index)
            self._steps.insert(to_index, step)
            self.stepsChanged.emit(self.steps)
    
    def toggle_step(self, step_id: str):
        """切换步骤启用状态"""
        for step in self._steps:
            if step.id == step_id:
                step.enabled = not step.enabled
                self.stepsChanged.emit(self.steps)
                break
    
    def process_text(self, text: str) -> str:
        """处理文本"""
        current_text = text
        
        for step in self._steps:
            if not step.enabled:
                continue
            
            try:
                current_text = self._process_step(step, current_text)
            except Exception as e:
                # 处理步骤出错时跳过该步骤
                print(f"Rule step '{step.name}' failed: {e}")
        
        return current_text
    
    def _process_step(self, step: RuleStep, text: str) -> str:
        """执行单个步骤"""
        step_type = step.type
        params = step.params
        
        if step_type == RuleStep.TYPE_REGEX_REPLACE:
            return self._process_regex_replace(text, params)
        elif step_type == RuleStep.TYPE_CASE_CONVERT:
            return self._process_case_convert(text, params)
        elif step_type == RuleStep.TYPE_MERGE_EMPTY_LINES:
            return self._process_merge_empty_lines(text, params)
        elif step_type == RuleStep.TYPE_REMOVE_EMPTY_LINES:
            return self._process_remove_empty_lines(text, params)
        elif step_type == RuleStep.TYPE_FULL_WIDTH_TO_HALF:
            return self._process_full_width_to_half(text, params)
        elif step_type == RuleStep.TYPE_HALF_WIDTH_TO_FULL:
            return self._process_half_width_to_full(text, params)
        elif step_type == RuleStep.TYPE_REMOVE_NUMBERS:
            return self._process_remove_numbers(text, params)
        elif step_type == RuleStep.TYPE_REMOVE_PUNCTUATION:
            return self._process_remove_punctuation(text, params)
        elif step_type == RuleStep.TYPE_TRIM_LINES:
            return self._process_trim_lines(text, params)
        elif step_type == RuleStep.TYPE_CUSTOM_PYTHON:
            return self._process_custom_python(text, params)
        
        return text
    
    def _process_regex_replace(self, text: str, params: Dict) -> str:
        """正则替换"""
        pattern = params.get("pattern", "")
        replacement = params.get("replacement", "")
        flags = params.get("flags", 0)
        
        if not pattern:
            return text
        
        try:
            return re.sub(pattern, replacement, text, flags=flags)
        except re.error:
            return text
    
    def _process_case_convert(self, text: str, params: Dict) -> str:
        """大小写转换"""
        case_type = params.get("case_type", RuleStep.CASE_UPPER)
        
        if case_type == RuleStep.CASE_UPPER:
            return text.upper()
        elif case_type == RuleStep.CASE_LOWER:
            return text.lower()
        elif case_type == RuleStep.CASE_TITLE:
            return text.title()
        
        return text
    
    def _process_merge_empty_lines(self, text: str, params: Dict) -> str:
        """合并空行"""
        lines = text.split('\n')
        merged = []
        empty_line_count = 0
        
        for line in lines:
            if line.strip() == '':
                empty_line_count += 1
                if empty_line_count <= 1:
                    merged.append(line)
            else:
                empty_line_count = 0
                merged.append(line)
        
        return '\n'.join(merged)
    
    def _process_remove_empty_lines(self, text: str, params: Dict) -> str:
        """移除空行"""
        lines = text.split('\n')
        non_empty_lines = [line for line in lines if line.strip() != '']
        return '\n'.join(non_empty_lines)
    
    def _process_full_width_to_half(self, text: str, params: Dict) -> str:
        """全角转半角"""
        result = []
        for char in text:
            code = ord(char)
            if code == 12288:  # 全角空格
                result.append(chr(32))
            elif 65281 <= code <= 65374:  # 全角字符（除空格）
                result.append(chr(code - 65248))
            else:
                result.append(char)
        return ''.join(result)
    
    def _process_half_width_to_full(self, text: str, params: Dict) -> str:
        """半角转全角"""
        result = []
        for char in text:
            code = ord(char)
            if code == 32:  # 半角空格
                result.append(chr(12288))
            elif 33 <= code <= 126:  # 半角字符（除空格）
                result.append(chr(code + 65248))
            else:
                result.append(char)
        return ''.join(result)
    
    def _process_remove_numbers(self, text: str, params: Dict) -> str:
        """移除数字"""
        return re.sub(r'\d+', '', text)
    
    def _process_remove_punctuation(self, text: str, params: Dict) -> str:
        """移除标点符号"""
        # 保留中文标点和英文标点的移除选项
        keep_chinese = params.get("keep_chinese", False)
        keep_english = params.get("keep_english", False)
        
        if keep_chinese and keep_english:
            return text
        elif not keep_chinese and not keep_english:
            # 移除所有标点
            return re.sub(r'[\p{P}]+', '', text, flags=re.UNICODE)
        elif keep_chinese:
            # 只移除英文标点
            return re.sub(r'[\p{P}&&[^\p{Han}]]+', '', text, flags=re.UNICODE)
        else:
            # 只移除中文标点
            return re.sub(r'[\p{P}&&\p{Han}]+', '', text, flags=re.UNICODE)
    
    def _process_trim_lines(self, text: str, params: Dict) -> str:
        """修剪行首尾空格"""
        lines = text.split('\n')
        trimmed_lines = [line.strip() for line in lines]
        return '\n'.join(trimmed_lines)
    
    def _process_custom_python(self, text: str, params: Dict) -> str:
        """自定义Python代码处理"""
        code = params.get("code", "")
        
        if not code:
            return text
        
        try:
            # 创建安全的执行环境
            local_vars = {"text": text}
            # 只允许访问安全的模块和函数
            safe_globals = {
                "__builtins__": {
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "len": len,
                    "range": range,
                    "enumerate": enumerate,
                    "zip": zip,
                    "map": map,
                    "filter": filter,
                    "sorted": sorted,
                    "reversed": reversed,
                    "list": list,
                    "dict": dict,
                    "set": set,
                    "tuple": tuple,
                    "abs": abs,
                    "round": round,
                    "min": min,
                    "max": max,
                    "sum": sum,
                    "any": any,
                    "all": all,
                    "chr": chr,
                    "ord": ord,
                    "hex": hex,
                    "oct": oct,
                    "bin": bin,
                    "print": lambda *args, **kwargs: None,  # 禁用print
                    "input": lambda *args, **kwargs: "",  # 禁用input
                }
            }
            exec(code, safe_globals, local_vars)
            return local_vars.get("text", text)
        except Exception as e:
            print(f"Custom Python code failed: {e}")
        
        return text
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self._id,
            "name": self._name,
            "description": self._description,
            "steps": [step.to_dict() for step in self._steps],
            "bind_types": self._bind_types
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleSet':
        """从字典创建"""
        steps = [RuleStep.from_dict(step_data) for step_data in data.get("steps", [])]
        return cls(
            set_id=data.get("id"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=steps,
            bind_types=data.get("bind_types", [])
        )

class PostProcessingManager(QObject):
    """后处理管理器"""
    
    # 信号
    ruleSetsChanged = Signal(list)
    currentSetChanged = Signal(str)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._rule_sets: List[RuleSet] = []
        self._current_set_id: Optional[str] = None
        self._config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "configs")
        self._config_file = os.path.join(self._config_dir, "post_processing_rules.json")
        
        # 确保配置目录存在
        os.makedirs(self._config_dir, exist_ok=True)
        
        # 加载配置
        self._load_config()
        
        # 如果没有规则集，创建一个默认的
        if not self._rule_sets:
            self._create_default_rule_sets()
    
    def _load_config(self):
        """加载配置"""
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._rule_sets = [RuleSet.from_dict(set_data) for set_data in data.get("rule_sets", [])]
                    self._current_set_id = data.get("current_set_id")
            except Exception as e:
                print(f"Failed to load post processing config: {e}")
    
    def _save_config(self):
        """保存配置"""
        try:
            data = {
                "rule_sets": [rule_set.to_dict() for rule_set in self._rule_sets],
                "current_set_id": self._current_set_id
            }
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save post processing config: {e}")
    
    def _create_default_rule_sets(self):
        """创建默认规则集"""
        # 创建全角转半角规则集
        full_to_half_steps = [
            RuleStep(
                name="全角转半角",
                step_type=RuleStep.TYPE_FULL_WIDTH_TO_HALF,
                enabled=True
            )
        ]
        
        full_to_half_set = RuleSet(
            name="全角转半角",
            description="将全角字符转换为半角字符",
            steps=full_to_half_steps,
            bind_types=["screenshot", "batch", "document"]
        )
        
        # 创建去序号规则集
        remove_numbering_steps = [
            RuleStep(
                name="移除数字序号",
                step_type=RuleStep.TYPE_REGEX_REPLACE,
                enabled=True,
                params={
                    "pattern": r'^\d+\.?\s*',
                    "replacement": "",
                    "flags": re.MULTILINE
                }
            )
        ]
        
        remove_numbering_set = RuleSet(
            name="去序号",
            description="移除行首的数字序号",
            steps=remove_numbering_steps,
            bind_types=["screenshot", "batch", "document"]
        )
        
        # 创建移除空行规则集
        remove_empty_lines_steps = [
            RuleStep(
                name="移除空行",
                step_type=RuleStep.TYPE_REMOVE_EMPTY_LINES,
                enabled=True
            )
        ]
        
        remove_empty_lines_set = RuleSet(
            name="移除空行",
            description="移除文本中的空行",
            steps=remove_empty_lines_steps,
            bind_types=["screenshot", "batch", "document"]
        )
        
        # 创建移除标点规则集
        remove_punctuation_steps = [
            RuleStep(
                name="移除标点",
                step_type=RuleStep.TYPE_REMOVE_PUNCTUATION,
                enabled=True,
                params={
                    "keep_chinese": False,
                    "keep_english": False
                }
            )
        ]
        
        remove_punctuation_set = RuleSet(
            name="移除标点",
            description="移除文本中的所有标点符号",
            steps=remove_punctuation_steps,
            bind_types=["screenshot", "batch", "document"]
        )
        
        # 创建移除数字规则集
        remove_numbers_steps = [
            RuleStep(
                name="移除数字",
                step_type=RuleStep.TYPE_REMOVE_NUMBERS,
                enabled=True
            )
        ]
        
        remove_numbers_set = RuleSet(
            name="移除数字",
            description="移除文本中的数字",
            steps=remove_numbers_steps,
            bind_types=["screenshot", "batch", "document"]
        )
        
        # 创建修剪行规则集
        trim_lines_steps = [
            RuleStep(
                name="修剪行",
                step_type=RuleStep.TYPE_TRIM_LINES,
                enabled=True
            )
        ]
        
        trim_lines_set = RuleSet(
            name="修剪行",
            description="修剪每行的前后空格",
            steps=trim_lines_steps,
            bind_types=["screenshot", "batch", "document"]
        )
        
        # 创建半角转全角规则集
        half_to_full_steps = [
            RuleStep(
                name="半角转全角",
                step_type=RuleStep.TYPE_HALF_WIDTH_TO_FULL,
                enabled=True
            )
        ]
        
        half_to_full_set = RuleSet(
            name="半角转全角",
            description="将半角字符转换为全角字符",
            steps=half_to_full_steps,
            bind_types=["screenshot", "batch", "document"]
        )
        
        # 创建全部大写规则集
        to_upper_steps = [
            RuleStep(
                name="全部大写",
                step_type=RuleStep.TYPE_CASE_CONVERT,
                enabled=True,
                params={"case_type": "upper"}
            )
        ]
        
        to_upper_set = RuleSet(
            name="全部大写",
            description="将文本转换为全部大写",
            steps=to_upper_steps,
            bind_types=["screenshot", "batch", "document"]
        )
        
        # 创建全部小写规则集
        to_lower_steps = [
            RuleStep(
                name="全部小写",
                step_type=RuleStep.TYPE_CASE_CONVERT,
                enabled=True,
                params={"case_type": "lower"}
            )
        ]
        
        to_lower_set = RuleSet(
            name="全部小写",
            description="将文本转换为全部小写",
            steps=to_lower_steps,
            bind_types=["screenshot", "batch", "document"]
        )
        
        # 创建首字母大写规则集
        to_title_steps = [
            RuleStep(
                name="首字母大写",
                step_type=RuleStep.TYPE_CASE_CONVERT,
                enabled=True,
                params={"case_type": "title"}
            )
        ]
        
        to_title_set = RuleSet(
            name="首字母大写",
            description="将文本转换为首字母大写",
            steps=to_title_steps,
            bind_types=["screenshot", "batch", "document"]
        )
        
        self._rule_sets.extend([
            full_to_half_set,
            remove_numbering_set,
            remove_empty_lines_set,
            remove_punctuation_set,
            remove_numbers_set,
            trim_lines_set,
            half_to_full_set,
            to_upper_set,
            to_lower_set,
            to_title_set
        ])
        self._save_config()
    
    @Property(list, notify=ruleSetsChanged)
    def ruleSets(self):
        return [rule_set.to_dict() for rule_set in self._rule_sets]
    
    @Property(str, notify=currentSetChanged)
    def currentSetId(self):
        return self._current_set_id or ""
    
    @currentSetId.setter
    def currentSetId(self, value: str):
        if self._current_set_id != value:
            self._current_set_id = value
            self._save_config()
            self.currentSetChanged.emit(value)
    
    @Slot(str, result=dict)
    def getRuleSet(self, set_id: str) -> Dict[str, Any]:
        """获取规则集"""
        for rule_set in self._rule_sets:
            if rule_set.id == set_id:
                return rule_set.to_dict()
        return {}
    
    @Slot(dict, result=str)
    def addRuleSet(self, set_data: Dict[str, Any]) -> str:
        """添加规则集"""
        rule_set = RuleSet.from_dict(set_data)
        self._rule_sets.append(rule_set)
        self._save_config()
        self.ruleSetsChanged.emit(self.ruleSets)
        return rule_set.id
    
    @Slot(str, dict)
    def updateRuleSet(self, set_id: str, set_data: Dict[str, Any]):
        """更新规则集"""
        for rule_set in self._rule_sets:
            if rule_set.id == set_id:
                rule_set.name = set_data.get("name", rule_set.name)
                rule_set.description = set_data.get("description", rule_set.description)
                rule_set.bindTypes = set_data.get("bind_types", rule_set.bindTypes)
                
                # 更新步骤
                steps_data = set_data.get("steps", [])
                new_steps = [RuleStep.from_dict(step_data) for step_data in steps_data]
                rule_set._steps = new_steps
                
                self._save_config()
                self.ruleSetsChanged.emit(self.ruleSets)
                break
    
    @Slot(str)
    def deleteRuleSet(self, set_id: str):
        """删除规则集"""
        self._rule_sets = [rule_set for rule_set in self._rule_sets if rule_set.id != set_id]
        
        # 如果删除的是当前规则集，清空当前规则集ID
        if self._current_set_id == set_id:
            self._current_set_id = None
            self.currentSetChanged.emit("")
        
        self._save_config()
        self.ruleSetsChanged.emit(self.ruleSets)
    
    @Slot(str, str, str, result=str)
    def addStepToSet(self, set_id: str, step_type: str, step_name: str) -> str:
        """向规则集添加步骤"""
        for rule_set in self._rule_sets:
            if rule_set.id == set_id:
                step = RuleStep(name=step_name, step_type=step_type)
                rule_set.add_step(step)
                self._save_config()
                self.ruleSetsChanged.emit(self.ruleSets)
                return step.id
        return ""
    
    @Slot(str, str)
    def removeStepFromSet(self, set_id: str, step_id: str):
        """从规则集移除步骤"""
        for rule_set in self._rule_sets:
            if rule_set.id == set_id:
                rule_set.remove_step(step_id)
                self._save_config()
                self.ruleSetsChanged.emit(self.ruleSets)
                break
    
    @Slot(str, int, int)
    def moveStepInSet(self, set_id: str, from_index: int, to_index: int):
        """移动规则集中的步骤"""
        for rule_set in self._rule_sets:
            if rule_set.id == set_id:
                rule_set.move_step(from_index, to_index)
                self._save_config()
                self.ruleSetsChanged.emit(self.ruleSets)
                break
    
    @Slot(str, str)
    def toggleStepInSet(self, set_id: str, step_id: str):
        """切换规则集中步骤的启用状态"""
        for rule_set in self._rule_sets:
            if rule_set.id == set_id:
                rule_set.toggle_step(step_id)
                self._save_config()
                self.ruleSetsChanged.emit(self.ruleSets)
                break
    
    @Slot(str, str, dict)
    def updateStepInSet(self, set_id: str, step_id: str, step_data: Dict[str, Any]):
        """更新规则集中的步骤"""
        for rule_set in self._rule_sets:
            if rule_set.id == set_id:
                for step in rule_set._steps:
                    if step.id == step_id:
                        if "name" in step_data:
                            step.name = step_data["name"]
                        if "type" in step_data:
                            step.type = step_data["type"]
                        if "enabled" in step_data:
                            step.enabled = step_data["enabled"]
                        if "params" in step_data:
                            step.params = step_data["params"]
                        
                        self._save_config()
                        self.ruleSetsChanged.emit(self.ruleSets)
                        break
                break
    
    @Slot(str, str, result=str)
    def processText(self, set_id: str, text: str) -> str:
        """使用规则集处理文本"""
        for rule_set in self._rule_sets:
            if rule_set.id == set_id:
                return rule_set.process_text(text)
        return text
    
    @Slot(str, str, result=list)
    def processTextWithPreview(self, set_id: str, text: str) -> List[Dict[str, Any]]:
        """处理文本并返回每个步骤的预览结果"""
        for rule_set in self._rule_sets:
            if rule_set.id == set_id:
                results = []
                current_text = text
                
                results.append({
                    "step_name": "原始文本",
                    "step_id": "original",
                    "result": current_text,
                    "enabled": True
                })
                
                for step in rule_set._steps:
                    step_result = current_text
                    
                    if step.enabled:
                        try:
                            step_result = rule_set._process_step(step, current_text)
                        except Exception as e:
                            step_result = f"Error: {e}"
                    
                    results.append({
                        "step_name": step.name,
                        "step_id": step.id,
                        "result": step_result,
                        "enabled": step.enabled
                    })
                    
                    if step.enabled:
                        current_text = step_result
                
                return results
        
        return [{"step_name": "原始文本", "step_id": "original", "result": text, "enabled": True}]
    
    @Slot(str, result=list)
    def getRuleSetsForType(self, ocr_type: str) -> List[Dict[str, Any]]:
        """获取指定OCR类型的规则集"""
        return [
            rule_set.to_dict() for rule_set in self._rule_sets
            if rule_set.is_bound_to_ocr_type(ocr_type)
        ]
    
    @Slot(str, str, result=str)
    def exportRuleSet(self, set_id: str, file_path: str) -> str:
        """导出规则集"""
        try:
            for rule_set in self._rule_sets:
                if rule_set.id == set_id:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(rule_set.to_dict(), f, ensure_ascii=False, indent=2)
                    return ""
            return "规则集不存在"
        except Exception as e:
            return str(e)
    
    @Slot(str, result=str)
    def importRuleSet(self, file_path: str) -> str:
        """导入规则集"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 生成新的ID
            data["id"] = str(uuid.uuid4())
            
            rule_set = RuleSet.from_dict(data)
            self._rule_sets.append(rule_set)
            self._save_config()
            self.ruleSetsChanged.emit(self.ruleSets)
            
            return ""
        except Exception as e:
            return str(e)

# 全局实例
PostProcessingManagerInstance = PostProcessingManager()