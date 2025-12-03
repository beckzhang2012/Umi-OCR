# ========================================# =============== 统计页面 ===============# ========================================import osimport jsonimport datetimeimport csvfrom collections import Counterfrom PySide2.QtCore import Signal, Slotfrom umi_log import loggerfrom .page import Page  # 页基类from ..event_bus.pubsub_service import PubSubService  # 发布/订阅管理器class Statistics(Page):    # 定义信号    statisticsUpdated = Signal()    def __init__(self, *args):        super().__init__(*args)        # 统计数据        self.statistics = {            "total_count": 0,            "today_count": 0,            "week_count": 0,            "month_count": 0,            "success_rate": 0.0,            "avg_confidence": 0.0        }        # 趋势数据        self.trend_data = []        # 词汇统计数据        self.vocabulary_statistics = []        # 识别记录存储目录        self.records_dir = os.path.join(os.path.expanduser("~"), "UmiOCR", "ScreenshotOCR", "records")    # ========================= 【加载统计数据】 =========================    @Slot()    def loadStatistics(self):
        """加载统计数据"""
        try:
            # 定义所有记录目录
            records_dirs = [
                os.path.join(os.path.expanduser("~"), "UmiOCR", "ScreenshotOCR", "records"),
                os.path.join(os.path.expanduser("~"), "UmiOCR", "BatchOCR", "records")
            ]
            # 解析所有记录文件
            all_records = []
            for records_dir in records_dirs:
                if not os.path.exists(records_dir):
                    continue
                # 获取所有记录文件
                record_files = [f for f in os.listdir(records_dir) if f.endswith(".json")]
                for file_name in record_files:
                    file_path = os.path.join(records_dir, file_name)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            records = json.load(f)
                            all_records.extend(records)
                    except Exception as e:
                        logger.error(f"加载记录文件 {file_path} 失败: {e}")
            # 计算统计数据
            self.calculateStatistics(all_records)
            # 计算趋势数据
            self.calculateTrendData(all_records)
            # 发送统计更新信号
            self.statisticsUpdated.emit()
        except Exception as e:
            logger.error(f"加载统计数据失败: {e}")    # ========================= 【计算统计数据】 =========================    def calculateStatistics(self, records):        """计算统计数据"""        if not records:            self.statistics = {                "total_count": 0,                "today_count": 0,                "week_count": 0,                "month_count": 0,                "success_rate": 0.0,                "avg_confidence": 0.0            }            return        total_count = len(records)        today = datetime.date.today()        week_ago = today - datetime.timedelta(days=7)        month_ago = today - datetime.timedelta(days=30)        today_count = 0        week_count = 0        month_count = 0        success_count = 0        total_confidence = 0.0        for record in records:            try:                # 获取记录日期                record_date = datetime.datetime.fromisoformat(record["timestamp"]).date()                # 统计今日、本周、本月识别次数                if record_date == today:                    today_count += 1                if record_date >= week_ago:                    week_count += 1                if record_date >= month_ago:                    month_count += 1                # 统计成功次数和置信度                if record["code"] == 100:                    success_count += 1                    total_confidence += record.get("score", 0.0)            except Exception as e:                logger.error(f"解析记录失败: {e}")        # 计算成功率和平均置信度        success_rate = success_count / total_count if total_count > 0 else 0.0        avg_confidence = total_confidence / success_count if success_count > 0 else 0.0        # 更新统计数据        self.statistics = {            "total_count": total_count,            "today_count": today_count,            "week_count": week_count,            "month_count": month_count,            "success_rate": success_rate,            "avg_confidence": avg_confidence        }    # ========================= 【计算趋势数据】 =========================    def calculateTrendData(self, records):        """计算最近30天的识别次数趋势"""        if not records:            self.trend_data = []            return        today = datetime.date.today()        # 初始化最近30天的数据        trend_data = []        for i in range(30):            date = today - datetime.timedelta(days=i)            trend_data.append({                "date": date.isoformat(),                "count": 0            })        # 统计每天的识别次数        date_count = Counter()        for record in records:            try:                record_date = datetime.datetime.fromisoformat(record["timestamp"]).date()                date_count[record_date] += 1            except Exception as e:                logger.error(f"解析记录日期失败: {e}")        # 更新趋势数据        for item in trend_data:            item_date = datetime.date.fromisoformat(item["date"])            item["count"] = date_count.get(item_date, 0)        # 按日期升序排序        self.trend_data = sorted(trend_data, key=lambda x: x["date"])    # ========================= 【刷新词汇统计】 =========================    @Slot(int)    def refreshVocabularyStatistics(self, min_word_length=2):
        """刷新词汇统计"""
        try:
            # 定义所有记录目录
            records_dirs = [
                os.path.join(os.path.expanduser("~"), "UmiOCR", "ScreenshotOCR", "records"),
                os.path.join(os.path.expanduser("~"), "UmiOCR", "BatchOCR", "records")
            ]
            # 解析所有记录文件并提取文本
            all_text = ""
            for records_dir in records_dirs:
                if not os.path.exists(records_dir):
                    continue
                # 获取所有记录文件
                record_files = [f for f in os.listdir(records_dir) if f.endswith(".json")]
                for file_name in record_files:
                    file_path = os.path.join(records_dir, file_name)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            records = json.load(f)
                            for record in records:
                                if record["code"] == 100 and "data" in record:
                                    for item in record["data"]:
                                        all_text += item.get("text", "") + " "
                    except Exception as e:
                        logger.error(f"加载记录文件 {file_path} 失败: {e}")
            # 分词（简单的空格和标点分割）
            words = []
            import re
            # 使用正则表达式分割单词，保留中文、英文和数字
            word_pattern = re.compile(r'[\u4e00-\u9fa5a-zA-Z0-9]+')
            words = word_pattern.findall(all_text)
            # 过滤长度小于min_word_length的单词
            words = [word for word in words if len(word) >= min_word_length]
            # 统计词频
            word_count = Counter(words)
            # 计算总词数
            total_words = len(words)
            # 生成词汇统计数据
            self.vocabulary_statistics = []
            for word, count in word_count.most_common(20):  # 取前20个最常用词汇
                frequency = (count / total_words) * 100 if total_words > 0 else 0.0
                self.vocabulary_statistics.append({
                    "word": word,
                    "count": count,
                    "frequency": f"{frequency:.2f}%"
                })
            # 发送统计更新信号
            self.statisticsUpdated.emit()
        except Exception as e:
            logger.error(f"刷新词汇统计失败: {e}")    # ========================= 【导出统计数据】 =========================    @Slot(str)    def exportStatistics(self, format_type="json"):        """导出统计数据"""        try:            # 生成导出文件路径            export_dir = os.path.join(os.path.expanduser("~"), "UmiOCR", "ScreenshotOCR", "exports")            if not os.path.exists(export_dir):                os.makedirs(export_dir)            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")            if format_type == "json":                file_path = os.path.join(export_dir, f"statistics_{timestamp}.json")                # 准备导出数据                export_data = {                    "statistics": self.statistics,                    "trend_data": self.trend_data,                    "vocabulary_statistics": self.vocabulary_statistics,                    "export_time": datetime.datetime.now().isoformat()                }                # 写入JSON文件                with open(file_path, "w", encoding="utf-8") as f:                    json.dump(export_data, f, ensure_ascii=False, indent=2)            elif format_type == "csv":                file_path = os.path.join(export_dir, f"statistics_{timestamp}.csv")                # 写入CSV文件                with open(file_path, "w", encoding="utf-8", newline="") as f:                    writer = csv.writer(f)                    # 写入统计数据                    writer.writerow(["统计项", "数值"])                    writer.writerow(["总识别次数", self.statistics["total_count"]])                    writer.writerow(["今日识别次数", self.statistics["today_count"]])                    writer.writerow(["本周识别次数", self.statistics["week_count"]])                    writer.writerow(["本月识别次数", self.statistics["month_count"]])                    writer.writerow(["识别成功率", f"{self.statistics['success_rate'] * 100:.1f}%"])                    writer.writerow(["平均置信度", f"{self.statistics['avg_confidence'] * 100:.1f}%"])                    writer.writerow([])                    # 写入趋势数据                    writer.writerow(["日期", "识别次数"])                    for item in self.trend_data:                        writer.writerow([item["date"], item["count"]])                    writer.writerow([])                    # 写入词汇统计数据                    writer.writerow(["词汇", "出现次数", "频率"])                    for item in self.vocabulary_statistics:                        writer.writerow([item["word"], item["count"], item["frequency"]])            else:                logger.error(f"不支持的导出格式: {format_type}")                return            # 发送导出成功信号            self.callQml("showMessage", qsTr("导出成功"), qsTr(f"统计数据已导出到: {file_path}"))        except Exception as e:            logger.error(f"导出统计数据失败: {e}")            self.callQml("showMessage", qsTr("导出失败"), str(e))    # ========================= 【保存识别记录】 =========================    def saveOCRRecord(self, record, task_type="ScreenshotOCR"):        """保存OCR识别记录"""
        try:
            # 根据任务类型确定记录目录
            records_dir = os.path.join(os.path.expanduser("~"), "UmiOCR", task_type, "records")
            # 确保记录目录存在
            if not os.path.exists(records_dir):
                os.makedirs(records_dir)
            # 获取今天的日期作为文件名
            today = datetime.date.today().isoformat()
            file_path = os.path.join(records_dir, f"{today}.json")
            # 添加时间戳
            record["timestamp"] = datetime.datetime.now().isoformat()
            # 读取现有记录
            records = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        records = json.load(f)
                except Exception as e:
                    logger.error(f"读取记录文件 {file_path} 失败: {e}")
                    records = []
            # 添加新记录
            records.append(record)
            # 保存记录
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存OCR记录失败: {e}")    # ========================= 【订阅OCR完成事件】 =========================    def subscribeOCRCompleteEvent(self):        """订阅OCR完成事件"""
        PubSubService.subscribe("<<ScreenshotOcrEnd>>", self.onOCRComplete)
        PubSubService.subscribe("<<BatchOcrEnd>>", self.onBatchOCRComplete)    def unsubscribeOCRCompleteEvent(self):        """取消订阅OCR完成事件"""
        PubSubService.unsubscribe("<<ScreenshotOcrEnd>>", self.onOCRComplete)
        PubSubService.unsubscribe("<<BatchOcrEnd>>", self.onBatchOCRComplete)    def onOCRComplete(self, results):        """OCR完成事件处理"""
        for result in results:
            self.saveOCRRecord(result, "ScreenshotOCR")
        # 重新加载统计数据
        self.loadStatistics()
        self.refreshVocabularyStatistics(2)  # 默认最小词汇长度为2    def onBatchOCRComplete(self, results):        """批量OCR完成事件处理"""
        for result in results:
            self.saveOCRRecord(result, "BatchOCR")
        # 重新加载统计数据
        self.loadStatistics()
        self.refreshVocabularyStatistics(2)  # 默认最小词汇长度为2    # ========================= 【页面生命周期】 =========================    def onPageShow(self):        """页面显示时调用"""        self.subscribeOCRCompleteEvent()        self.loadStatistics()        self.refreshVocabularyStatistics(2)    def onPageHide(self):        """页面隐藏时调用"""        self.unsubscribeOCRCompleteEvent()