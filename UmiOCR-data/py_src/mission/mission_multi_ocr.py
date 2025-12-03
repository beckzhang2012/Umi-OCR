# ===============================================
# =============== 多引擎OCR任务管理器 ===============
# ===============================================

"""
多引擎OCR任务管理器，支持同时使用多个OCR引擎处理同一批图片，并提供结果对比功能。
"""

import os
import json
import time
from uuid import uuid4
from collections import defaultdict
from umi_log import logger
from .mission import Mission
from ..ocr.api import getApiOcr, getLocalOptions
from ..utils.utils import argdIntConvert


class MultiOCRResult:
    """多引擎OCR结果容器"""
    def __init__(self, image_path=None, image_bytes=None, image_base64=None):
        self.image_path = image_path
        self.image_bytes = image_bytes
        self.image_base64 = image_base64
        self.engine_results = {}  # {engine_key: result_dict}
        self.best_result = None
        self.confidence = 0.0
        self.process_time = 0.0

    def add_engine_result(self, engine_key, result):
        """添加单个引擎的识别结果"""
        self.engine_results[engine_key] = result
        if result.get('code') == 100:
            self.process_time += result.get('time', 0)

    def generate_best_result(self, strategy='vote'):
        """生成最佳结果，支持不同策略：
        - 'vote': 投票策略，选择出现频率最高的文本
        - 'confidence': 置信度策略，选择平均置信度最高的结果
        - 'merge': 合并策略，综合多个引擎的结果
        """
        if not self.engine_results:
            return

        valid_results = []
        for engine_key, result in self.engine_results.items():
            if result.get('code') == 100:
                valid_results.append((engine_key, result))

        if not valid_results:
            return

        if strategy == 'confidence':
            # 选择平均置信度最高的结果
            best_engine = None
            max_confidence = 0
            for engine_key, result in valid_results:
                confidence = result.get('score', 0)
                if confidence > max_confidence:
                    max_confidence = confidence
                    best_engine = engine_key
            
            if best_engine:
                self.best_result = self.engine_results[best_engine]['data']
                self.confidence = max_confidence

        elif strategy == 'vote':
            # 投票策略，统计每个文本块的出现频率
            text_votes = defaultdict(int)
            text_sources = defaultdict(list)
            
            for engine_key, result in valid_results:
                for block in result['data']:
                    text = block['text']
                    text_votes[text] += 1
                    text_sources[text].append(engine_key)
            
            # 选择得票最高的文本块
            if text_votes:
                sorted_texts = sorted(text_votes.items(), key=lambda x: x[1], reverse=True)
                best_text = sorted_texts[0][0]
                
                # 构建最佳结果
                self.best_result = []
                for engine_key, result in valid_results:
                    for block in result['data']:
                        if block['text'] == best_text:
                            self.best_result.append(block.copy())
                            self.confidence = block['score']
                            break

        elif strategy == 'merge':
            # 合并策略，综合所有引擎的结果
            merged_blocks = []
            all_blocks = []
            
            for engine_key, result in valid_results:
                all_blocks.extend(result['data'])
            
            # 简单合并：去重并按位置排序
            seen_texts = set()
            for block in sorted(all_blocks, key=lambda x: (x.get('box', [0, 0])[1], x.get('box', [0, 0])[0])):
                text = block['text']
                if text not in seen_texts and text.strip():
                    seen_texts.add(text)
                    merged_blocks.append(block)
            
            self.best_result = merged_blocks
            if merged_blocks:
                self.confidence = sum(block['score'] for block in merged_blocks) / len(merged_blocks)


class __MissionMultiOcrClass(Mission):
    def __init__(self):
        super().__init__()
        self._engine_instances = {}  # {engine_key: api_instance}
        self._engine_configs = {}  # {engine_key: config_dict}
        self._comparison_strategy = 'confidence'  # 默认策略

    def set_engines(self, engine_configs):
        """设置要使用的OCR引擎列表
        engine_configs: [{"key": engine_key, "config": config_dict}, ...]
        """
        # 清理旧引擎实例
        for engine_key, api in self._engine_instances.items():
            if api:
                api.stop()
        
        self._engine_instances.clear()
        self._engine_configs.clear()
        
        # 初始化新引擎实例
        errors = []
        for config in engine_configs:
            engine_key = config.get('key')
            engine_config = config.get('config', {})
            
            if not engine_key:
                continue
            
            # 创建引擎实例
            api_instance = getApiOcr(engine_key, engine_config)
            if isinstance(api_instance, str):
                # 创建失败
                errors.append(f"引擎 {engine_key} 初始化失败: {api_instance}")
                logger.error(f"多引擎OCR: 引擎 {engine_key} 初始化失败: {api_instance}")
            else:
                self._engine_instances[engine_key] = api_instance
                self._engine_configs[engine_key] = engine_config
                logger.info(f"多引擎OCR: 引擎 {engine_key} 初始化成功")
        
        return errors

    def set_comparison_strategy(self, strategy):
        """设置结果对比策略
        strategy: 'vote' | 'confidence' | 'merge'
        """
        valid_strategies = ['vote', 'confidence', 'merge']
        if strategy in valid_strategies:
            self._comparison_strategy = strategy
            return True
        return False

    def get_available_engines(self):
        """获取当前可用的引擎列表"""
        return list(self._engine_instances.keys())

    def msnPreTask(self, msnInfo):
        """任务前处理，更新所有引擎的参数"""
        if not self._engine_instances:
            return "[Error] 多引擎OCR: 没有可用的OCR引擎"
        
        argd = msnInfo.get('argd', {})
        errors = []
        
        for engine_key, api in self._engine_instances.items():
            # 为每个引擎准备参数
            engine_argd = self._prepare_engine_argd(engine_key, argd)
            
            # 更新引擎参数
            msg = api.start(engine_argd)
            if msg.startswith("[Error]"):
                errors.append(f"引擎 {engine_key} 参数更新失败: {msg}")
                logger.error(f"多引擎OCR: 引擎 {engine_key} 参数更新失败: {msg}")
        
        if errors:
            return f"[Error] 多引擎OCR: 部分引擎参数更新失败: {'; '.join(errors)}"
        
        return ""

    def msnTask(self, msnInfo, msn):
        """执行多引擎OCR任务"""
        if not self._engine_instances:
            return {
                "code": 901,
                "data": "[Error] 多引擎OCR: 没有可用的OCR引擎",
                "time": 0
            }
        
        start_time = time.time()
        multi_result = MultiOCRResult(
            image_path=msn.get('path'),
            image_bytes=msn.get('bytes'),
            image_base64=msn.get('base64')
        )
        
        # 并行执行所有引擎的OCR任务
        # 注意：这里使用同步执行，实际可以考虑异步并行
        for engine_key, api in self._engine_instances.items():
            try:
                if 'path' in msn:
                    res = api.runPath(msn['path'])
                elif 'bytes' in msn:
                    res = api.runBytes(msn['bytes'])
                elif 'base64' in msn:
                    res = api.runBase64(msn['base64'])
                else:
                    res = {
                        "code": 901,
                        "data": "[Error] Unknown task type",
                        "time": 0
                    }
                
                # 计算平均置信度
                if res.get('code') == 100:
                    score, num = 0, 0
                    for r in res['data']:
                        score += r['score']
                        num += 1
                    if num > 0:
                        res['score'] = score / num
                
                multi_result.add_engine_result(engine_key, res)
                
            except Exception as e:
                logger.error(f"多引擎OCR: 引擎 {engine_key} 执行失败", exc_info=True)
                multi_result.add_engine_result(engine_key, {
                    "code": 902,
                    "data": f"[Error] 引擎执行失败: {str(e)}",
                    "time": 0
                })
        
        # 生成最佳结果
        multi_result.generate_best_result(self._comparison_strategy)
        
        # 计算总处理时间
        total_time = time.time() - start_time
        
        # 构造最终结果
        final_result = {
            "code": 100,
            "data": multi_result.best_result,
            "score": multi_result.confidence,
            "time": total_time,
            "multi_engine_results": multi_result.engine_results,
            "best_strategy": self._comparison_strategy,
            "image_path": multi_result.image_path
        }
        
        return final_result

    def _prepare_engine_argd(self, engine_key, global_argd):
        """为特定引擎准备参数"""
        engine_argd = {}
        
        # 提取引擎特定的参数
        key_prefix = f"ocr.{engine_key}."
        for k, v in global_argd.items():
            if k.startswith(key_prefix):
                engine_argd[k[len(key_prefix):]] = v
            elif k.startswith("ocr.") and k != key_prefix[:-1]:
                # 其他OCR通用参数
                engine_argd[k[4:]] = v
        
        # 恢复int类型
        argdIntConvert(engine_argd)
        
        return engine_argd

    def get_engine_config(self, engine_key):
        """获取引擎配置"""
        return self._engine_configs.get(engine_key, {})

    def get_comparison_strategy(self):
        """获取当前对比策略"""
        return self._comparison_strategy

    def cleanup(self):
        """清理资源"""
        for engine_key, api in self._engine_instances.items():
            if api:
                api.stop()
        self._engine_instances.clear()
        self._engine_configs.clear()


# 全局多引擎OCR任务管理器
MissionMultiOCR = __MissionMultiOcrClass()
