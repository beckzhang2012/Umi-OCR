# ===============================================
# =============== 统计标签页 ===============
# ===============================================

import os
import time
import json
import collections
from datetime import datetime, timedelta

from umi_log import logger
from .page import Page  # 页基类

class Statistics(Page):
    def __init__(self, *args):
        super().__init__(*args)
        self.statistics_data = {}  # 统计数据缓存
        self.records_dir = "./records"  # 识别记录目录
        
        # 确保记录目录存在
        if not os.path.exists(self.records_dir):
            os.makedirs(self.records_dir)
    
    # ========================= 【qml调用python方法】 =========================
    
    # 获取统计数据
    def getStatisticsData(self):
        self._calculateStatistics()
        return self.statistics_data
    
    # 导出统计数据为JSON格式
    def exportToJSON(self, path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.statistics_data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f"导出JSON失败：{e}")
            return False
    
    # 导出统计数据为CSV格式
    def exportToCSV(self, path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                # 写入总统计
                f.write("总统计,值\n")
                f.write(f"总识别次数,{self.statistics_data['total_count']}\n")
                f.write(f"今日识别次数,{self.statistics_data['today_count']}\n")
                f.write(f"本周识别次数,{self.statistics_data['week_count']}\n")
                f.write(f"本月识别次数,{self.statistics_data['month_count']}\n")
                f.write(f"识别成功率,{self.statistics_data['success_rate']:.2%}\n")
                f.write(f"平均置信度,{self.statistics_data['avg_confidence']:.2f}\n")
                f.write(f"平均识别速度,{self.statistics_data['avg_speed']:.2f} 秒\n")
                
                # 写入词汇统计
                f.write("\n词汇统计,频率\n")
                for word, count in self.statistics_data['word_statistics'][:20]:
                    f.write(f"{word},{count}\n")
                
                # 写入时间趋势
                f.write("\n时间趋势,识别次数\n")
                for date_str, count in self.statistics_data['time_trend']:
                    f.write(f"{date_str},{count}\n")
            return True
        except Exception as e:
            logger.error(f"导出CSV失败：{e}")
            return False
    
    # ========================= 【统计数据计算方法】 =========================
    
    # 计算所有统计数据
    def _calculateStatistics(self):
        # 获取所有识别记录
        records = self._getAllRecords()
        
        # 计算总统计
        total_count = len(records)
        today_count = len(self._getRecordsByDate(records, datetime.today()))
        week_count = len(self._getRecordsByWeek(records, datetime.today()))
        month_count = len(self._getRecordsByMonth(records, datetime.today()))
        
        # 计算成功率和平均置信度
        success_count = 0
        total_confidence = 0.0
        total_time = 0.0
        
        for record in records:
            if record.get('code') == 100:
                success_count += 1
                total_confidence += record.get('score', 0)
                
            # 计算识别时间
            if 'start_time' in record and 'end_time' in record:
                total_time += record['end_time'] - record['start_time']
        
        success_rate = success_count / total_count if total_count > 0 else 0.0
        avg_confidence = total_confidence / success_count if success_count > 0 else 0.0
        avg_speed = total_time / total_count if total_count > 0 else 0.0
        
        # 计算词汇统计
        word_statistics = self._calculateWordStatistics(records)
        
        # 计算时间趋势
        time_trend = self._calculateTimeTrend(records)
        
        # 保存统计数据
        self.statistics_data = {
            'total_count': total_count,
            'today_count': today_count,
            'week_count': week_count,
            'month_count': month_count,
            'success_rate': success_rate,
            'avg_confidence': avg_confidence,
            'avg_speed': avg_speed,
            'word_statistics': word_statistics,
            'time_trend': time_trend,
        }
    
    # 获取所有识别记录
    def _getAllRecords(self):
        records = []
        
        # 遍历记录目录下的所有JSON文件
        for filename in os.listdir(self.records_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.records_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_records = json.load(f)
                        if isinstance(file_records, list):
                            records.extend(file_records)
                        else:
                            records.append(file_records)
                except Exception as e:
                    logger.error(f"读取记录文件失败：{file_path} - {e}")
        
        return records
    
    # 获取指定日期的记录
    def _getRecordsByDate(self, records, date):
        target_date_str = date.strftime('%Y-%m-%d')
        return [
            record for record in records 
            if 'date' in record and record['date'].startswith(target_date_str)
        ]
    
    # 获取指定周的记录
    def _getRecordsByWeek(self, records, date):
        # 找到本周的第一天（周一）
        start_of_week = date - timedelta(days=date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        return [
            record for record in records 
            if 'date' in record 
            and start_of_week <= datetime.strptime(record['date'], '%Y-%m-%d %H:%M:%S') <= end_of_week
        ]
    
    # 获取指定月的记录
    def _getRecordsByMonth(self, records, date):
        target_year = date.year
        target_month = date.month
        
        return [
            record for record in records 
            if 'date' in record 
            and datetime.strptime(record['date'], '%Y-%m-%d %H:%M:%S').year == target_year
            and datetime.strptime(record['date'], '%Y-%m-%d %H:%M:%S').month == target_month
        ]
    
    # 计算词汇统计
    def _calculateWordStatistics(self, records, min_length=2):
        word_counter = collections.Counter()
        
        for record in records:
            if record.get('code') == 100 and 'data' in record:
                for item in record['data']:
                    if 'text' in item:
                        text = item['text'].strip()
                        if len(text) >= min_length:
                            word_counter[text] += 1
        
        # 返回前20个高频词汇
        return word_counter.most_common(20)
    
    # 计算时间趋势
    def _calculateTimeTrend(self, records, days=30):
        trend = []
        
        # 生成最近30天的日期列表
        end_date = datetime.today()
        start_date = end_date - timedelta(days=days-1)
        
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            
            # 计算当天的识别次数
            count = 0
            for record in records:
                if 'date' in record and record['date'].startswith(date_str):
                    count += 1
            
            trend.append((date_str, count))
        
        return trend