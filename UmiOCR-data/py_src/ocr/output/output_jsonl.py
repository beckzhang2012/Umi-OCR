# 输出到jsonl文件

from .output import Output
from ...utils.file_writer import file_writer

import json


class OutputJsonl(Output):
    def __init__(self, argd):
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.jsonl"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        # 创建输出文件
        if not file_writer.create_file(self.outputPath):
            raise Exception(f"Failed to create jsonl file.\n创建jsonl文件失败。")

    def print(self, res):  # 输出图片结果
        # 不忽略空白条目
        content = json.dumps(res, ensure_ascii=False) + "\n"
        file_writer.write_file(self.outputPath, content, mode='a', encoding='utf-8')
        
        # 尝试处理缓存队列
        if file_writer.get_queue_size() > 0:
            file_writer.process_queue()
