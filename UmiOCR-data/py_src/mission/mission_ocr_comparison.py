# ===============================================
# =============== OCR 多引擎对比 ===============
# ===============================================

import json
import os
from umi_log import logger
from .mission_ocr import MissionOCR
from ..ocr.api import getApiOcr, getLocalOptions
from ..utils.utils import argdIntConvert


class MissionOCRComparison:
    def __init__(self):
        self._api_instances = {}  # 引擎API实例字典
        self._comparison_schemes = []  # 多引擎方案列表
        self._current_scheme = None  # 当前使用的方案
        self._config_path = os.path.join(os.path.dirname(__file__), "..", "..", "comparison_config.json")
        self.load_config()

    def load_config(self):
        """加载多引擎对比配置"""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self._comparison_schemes = config.get("schemes", [])
                    self._current_scheme = config.get("current_scheme", None)
            except Exception as e:
                logger.error(f"加载多引擎对比配置失败：{e}")

    def save_config(self):
        """保存多引擎对比配置"""
        try:
            config = {
                "schemes": self._comparison_schemes,
                "current_scheme": self._current_scheme
            }
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存多引擎对比配置失败：{e}")

    def add_comparison_scheme(self, name, api_keys):
        """添加多引擎方案"""
        # 检查API密钥是否有效
        valid_api_keys = []
        for key in api_keys:
            if self._get_api_instance(key):
                valid_api_keys.append(key)
            else:
                logger.warning(f"多引擎方案 {name} 中的API密钥 {key} 无效")

        if not valid_api_keys:
            return "[Error] 方案中没有有效的API密钥"

        # 创建方案
        scheme = {
            "name": name,
            "api_keys": valid_api_keys,
            "description": f"包含 {', '.join(valid_api_keys)} 三个OCR引擎的对比方案"
        }

        # 添加到方案列表
        self._comparison_schemes.append(scheme)
        self.save_config()

        return scheme

    def delete_comparison_scheme(self, name):
        """删除多引擎方案"""
        for i, scheme in enumerate(self._comparison_schemes):
            if scheme["name"] == name:
                del self._comparison_schemes[i]
                if self._current_scheme == name:
                    self._current_scheme = None
                self.save_config()
                return True
        return False

    def get_comparison_schemes(self):
        """获取所有多引擎方案"""
        return self._comparison_schemes

    def set_current_scheme(self, name):
        """设置当前使用的多引擎方案"""
        for scheme in self._comparison_schemes:
            if scheme["name"] == name:
                self._current_scheme = name
                self.save_config()
                return True
        return False

    def get_current_scheme(self):
        """获取当前使用的多引擎方案"""
        if not self._current_scheme:
            return None
        for scheme in self._comparison_schemes:
            if scheme["name"] == self._current_scheme:
                return scheme
        return None

    def _get_api_instance(self, api_key):
        """获取或创建OCR引擎API实例"""
        if api_key in self._api_instances:
            return self._api_instances[api_key]

        # 创建新的API实例
        api_instance = getApiOcr(api_key, {})
        if isinstance(api_instance, str) and api_instance.startswith("[Error]"):
            logger.error(f"创建OCR引擎实例 {api_key} 失败：{api_instance}")
            return None

        self._api_instances[api_key] = api_instance
        return api_instance

    def run_comparison(self, img_data, argd, api_keys=None):
        """运行多引擎对比"""
        # 确定要使用的引擎列表
        if api_keys:
            # 使用指定的引擎列表
            engines = api_keys
        else:
            # 使用当前方案中的引擎列表
            current_scheme = self.get_current_scheme()
            if not current_scheme:
                return "[Error] 没有选择当前方案"
            engines = current_scheme["api_keys"]

        # 检查引擎数量是否符合要求（最多3个）
        if len(engines) > 3:
            return "[Error] 多引擎对比最多支持3个引擎"

        # 运行所有引擎的OCR
        results = {}
        for engine in engines:
            api_instance = self._get_api_instance(engine)
            if not api_instance:
                results[engine] = {
                    "code": 902,
                    "data": f"[Error] 无法获取OCR引擎实例 {engine}"
                }
                continue

            # 启动引擎
            start_info = self._dict_short_key(argd)
            argdIntConvert(start_info)
            msg = api_instance.start(start_info)
            if msg.startswith("[Error]"):
                results[engine] = {
                    "code": 903,
                    "data": f"[Error] OCR引擎启动失败 {engine}: {msg}"
                }
                continue

            # 运行OCR
            if "path" in img_data:
                res = api_instance.runPath(img_data["path"])
                res["path"] = img_data["path"]
            elif "bytes" in img_data:
                res = api_instance.runBytes(img_data["bytes"])
            elif "base64" in img_data:
                res = api_instance.runBase64(img_data["base64"])
            else:
                res = {
                    "code": 901,
                    "data": "[Error] Unknown task type.\n【异常】未知的任务类型。"
                }

            results[engine] = res

        # 比较结果并生成对比报告
        comparison_report = self._generate_comparison_report(results)

        return {
            "individual_results": results,
            "comparison_report": comparison_report
        }

    def _dict_short_key(self, argd):
        """将 argd 中的长键转换为短键（用于OCR引擎参数）"""
        short_argd = {}
        for k in argd:
            if k.startswith("ocr."):
                key1 = k[4:]
                short_argd[key1] = argd[k]
        return short_argd

    def _generate_comparison_report(self, results):
        """生成多引擎对比报告"""
        report = {
            "total_engines": len(results),
            "successful_engines": 0,
            "failed_engines": 0,
            "text_comparison": [],
            "best_result": None
        }

        successful_results = {}
        for engine, res in results.items():
            if res["code"] == 100:
                report["successful_engines"] += 1
                successful_results[engine] = res
            else:
                report["failed_engines"] += 1

        # 只有当至少有两个引擎成功时才进行比较
        if report["successful_engines"] >= 2:
            # 提取所有成功引擎的文本结果
            engine_texts = {}
            for engine, res in successful_results.items():
                text = ""
                for r in res["data"]:
                    text += r["text"] + r.get("end", "")
                engine_texts[engine] = text

            # 比较文本结果，找出差异
            all_texts = list(engine_texts.values())
            report["text_comparison"] = self._compare_texts(all_texts, list(engine_texts.keys()))

            # 自动合成最佳结果
            report["best_result"] = self._synthesize_best_result(successful_results)

        return report

    def _compare_texts(self, texts, engine_names):
        """比较多个文本结果，找出差异"""
        # 这里简化实现，只比较文本是否完全相同
        comparison = []
        base_text = texts[0]
        base_engine = engine_names[0]

        for i in range(1, len(texts)):
            current_text = texts[i]
            current_engine = engine_names[i]

            if current_text == base_text:
                comparison.append(f"{current_engine} 与 {base_engine} 结果相同")
            else:
                comparison.append(f"{current_engine} 与 {base_engine} 结果不同")

        return comparison

    def _synthesize_best_result(self, successful_results):
        """自动合成最佳结果"""
        # 这里简化实现，选择置信度最高的结果
        best_engine = None
        best_confidence = 0
        best_result = None

        for engine, res in successful_results.items():
            # 计算平均置信度
            score, num = 0, 0
            for r in res["data"]:
                score += r["score"]
                num += 1
            average_confidence = score / num if num > 0 else 0

            if average_confidence > best_confidence:
                best_confidence = average_confidence
                best_engine = engine
                best_result = res

        return {
            "engine": best_engine,
            "confidence": best_confidence,
            "result": best_result
        }


# 全局 OCR多引擎对比管理器
MissionOCRComparison = MissionOCRComparison()
