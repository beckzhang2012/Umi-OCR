# 纯文本（无格式）txt文件

from .output import Output
from .tools import getDataText
from ...utils.file_writer import file_writer


class OutputTxtPlain(Output):
    def __init__(self, argd):
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.p.txt"  # 输出路径
        # 创建输出文件
        if not file_writer.create_file(self.outputPath):
            raise Exception(
                f"Failed to create plain txt file.\n创建纯文本txt文件失败。"
            )

    def print(self, res):  # 输出图片结果
        if not res["code"] == 100:
            return  # 强制忽略空白图片
        textOut = ""
        if res["code"] == 100:
            textOut += getDataText(res["data"])  # 获取拼接结果
            if not textOut[-1] == "\n":  # 确保结尾有换行
                textOut += "\n"
        # 使用增强型文件写入工具追加写入
        file_writer.write_file(self.outputPath, textOut, mode='a', encoding='utf-8')
        # 尝试处理缓存队列
        if file_writer.get_queue_size() > 0:
            file_writer.process_queue()
