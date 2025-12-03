#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计功能控制器
处理OCR识别数据的统计分析、趋势图生成和数据导出
"""

import json
import csv
import os
import re
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

class Statistics:
    """统计功能控制器类"""
    
    def __init__(self):
        """初始化统计控制器"""
        self.recent_results = []  # 存储最近的OCR识别结果
        self.ocr_dir = ""  # OCR结果存储目录
        self._init_ocr_dir()
    
    def _init_ocr_dir(self):
        """初始化OCR结果存储目录"""
        # 从配置中获取OCR结果目录，这里暂时使用默认路径
        self.ocr_dir = os.path.join(os.path.expanduser("~"), "UmiOCR", "output")
        if not os.path.exists(self.ocr_dir):
            os.makedirs(self.ocr_dir)
    
    def load_recent_results(self, days: int = 30) -> List[Dict]:
        """加载最近指定天数的OCR识别结果"""
        results = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 按日期遍历JSONL文件
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            file_path = os.path.join(self.ocr_dir, f"ocr_results_{date_str}.jsonl")
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            result = json.loads(line.strip())
                            # 验证结果包含必要字段
                            if all(key in result for key in ['timestamp', 'success', 'confidence', 'text']):
                                results.append(result)
                        except json.JSONDecodeError:
                            continue
            
            current_date += timedelta(days=1)
        
        self.recent_results = results
        return results
    
    def calculate_overall_stats(self) -> Dict[str, Any]:
        """计算总体统计数据"""
        if not self.recent_results:
            return self._empty_stats()
        
        total_count = len(self.recent_results)
        success_count = sum(1 for r in self.recent_results if r['success'])
        failure_count = total_count - success_count
        
        # 计算置信度（仅成功的结果）
        success_results = [r for r in self.recent_results if r['success']]
        avg_confidence = sum(r['confidence'] for r in success_results) / len(success_results) if success_results else 0
        
        # 计算今日、本周、本月统计
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        today_count = sum(1 for r in self.recent_results if datetime.fromtimestamp(r['timestamp']).date() == today)
        week_count = sum(1 for r in self.recent_results if week_start <= datetime.fromtimestamp(r['timestamp']).date() <= today)
        month_count = sum(1 for r in self.recent_results if month_start <= datetime.fromtimestamp(r['timestamp']).date() <= today)
        
        # 计算识别速度（假设平均每张图片处理时间）
        if total_count > 1:
            timestamps = sorted(r['timestamp'] for r in self.recent_results)
            total_time = timestamps[-1] - timestamps[0]
            avg_speed = total_time / total_count if total_time > 0 else 0
        else:
            avg_speed = 0
        
        return {
            'total_count': total_count,
            'success_count': success_count,
            'failure_count': failure_count,
            'success_rate': success_count / total_count * 100 if total_count > 0 else 0,
            'avg_confidence': avg_confidence,
            'today_count': today_count,
            'week_count': week_count,
            'month_count': month_count,
            'avg_speed': avg_speed  # 平均处理时间（秒）
        }
    
    def calculate_word_frequency(self, min_length: int = 2, top_n: int = 20) -> List[Tuple[str, int]]:
        """计算词汇频率统计"""
        if not self.recent_results:
            return []
        
        word_counter = Counter()
        
        for result in self.recent_results:
            if result['success'] and result['text']:
                # 使用正则表达式提取中文词汇
                words = re.findall(r'[\u4e00-\u9fff]+', result['text'])
                for word in words:
                    if len(word) >= min_length:
                        word_counter[word] += 1
        
        return word_counter.most_common(top_n)
    
    def calculate_trend_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """计算时间趋势数据"""
        trend_data = []
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # 初始化趋势数据
        current_date = start_date
        while current_date <= end_date:
            trend_data.append({
                'date': current_date.strftime("%Y-%m-%d"),
                'count': 0,
                'success_count': 0,
                'avg_confidence': 0
            })
            current_date += timedelta(days=1)
        
        # 填充趋势数据
        for result in self.recent_results:
            result_date = datetime.fromtimestamp(result['timestamp']).date()
            if start_date <= result_date <= end_date:
                index = (result_date - start_date).days
                if 0 <= index < len(trend_data):
                    trend_data[index]['count'] += 1
                    if result['success']:
                        trend_data[index]['success_count'] += 1
                        # 累积置信度用于计算平均值
                        if 'total_confidence' not in trend_data[index]:
                            trend_data[index]['total_confidence'] = 0
                        trend_data[index]['total_confidence'] += result['confidence']
        
        # 计算每日平均置信度
        for day_data in trend_data:
            if day_data['success_count'] > 0:
                day_data['avg_confidence'] = day_data['total_confidence'] / day_data['success_count']
            else:
                day_data['avg_confidence'] = 0
            # 移除临时字段
            day_data.pop('total_confidence', None)
        
        return trend_data
    
    def export_to_json(self, file_path: str) -> bool:
        """导出统计数据为JSON格式"""
        try:
            stats = {
                'export_time': datetime.now().isoformat(),
                'overall_stats': self.calculate_overall_stats(),
                'word_frequency': self.calculate_word_frequency(),
                'trend_data': self.calculate_trend_data()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"导出JSON失败: {e}")
            return False
    
    def export_to_csv(self, file_path: str) -> bool:
        """导出统计数据为CSV格式"""
        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                
                # 写入总体统计
                writer.writerow(['总体统计'])
                overall_stats = self.calculate_overall_stats()
                for key, value in overall_stats.items():
                    writer.writerow([key, value])
                writer.writerow([])
                
                # 写入词汇频率
                writer.writerow(['词汇频率', '频率'])
                word_freq = self.calculate_word_frequency()
                for word, freq in word_freq:
                    writer.writerow([word, freq])
                writer.writerow([])
                
                # 写入趋势数据
                writer.writerow(['日期', '识别次数', '成功次数', '平均置信度'])
                trend_data = self.calculate_trend_data()
                for day in trend_data:
                    writer.writerow([
                        day['date'],
                        day['count'],
                        day['success_count'],
                        day['avg_confidence']
                    ])
            
            return True
        except Exception as e:
            print(f"导出CSV失败: {e}")
            return False
    
    def _empty_stats(self) -> Dict[str, Any]:
        """返回空统计数据"""
        return {
            'total_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'success_rate': 0,
            'avg_confidence': 0,
            'today_count': 0,
            'week_count': 0,
            'month_count': 0,
            'avg_speed': 0
        }
    
    # ==================== QML调用方法 ==================== #
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """获取总体统计数据（供QML调用）"""
        self.load_recent_results()
        return self.calculate_overall_stats()
    
    def get_word_frequency(self, min_length: int = 2, top_n: int = 20) -> List[Tuple[str, int]]:
        """获取词汇频率统计（供QML调用）"""
        if not self.recent_results:
            self.load_recent_results()
        return self.calculate_word_frequency(min_length, top_n)
    
    def get_trend_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """获取时间趋势数据（供QML调用）"""
        if not self.recent_results:
            self.load_recent_results()
        return self.calculate_trend_data(days)
    
    def export_data(self, file_path: str, format_type: str = 'json') -> bool:
        """导出统计数据（供QML调用）"""
        if format_type.lower() == 'json':
            return self.export_to_json(file_path)
        elif format_type.lower() == 'csv':
            return self.export_to_csv(file_path)
        else:
            return False