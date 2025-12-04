# OCR输出器的基类。按指定的格式，将传入的文本输出到指定地方。

from .tools import getDataText
from ...platform import Platform
from ...utils.file_writer import SafeFileWriter
import os


class Output:
    def __init__(self, argd):
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.txt"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        self._writer = None  # 安全文件写入器

    def _get_writer(self, mode: str = "w") -> SafeFileWriter:
        """获取安全文件写入器"""
        if not self._writer:
            self._writer = SafeFileWriter(self.outputPath, mode, encoding="utf-8")
        return self._writer

    def print(self, res):  # 输出图片信息
        if not res["code"] == 100 and self.ignoreBlank:
            return  # 忽略空白图片
        textOut = f"图片路径：{res['path']}\n代码：{res['code']}\n"
        if res["code"] == 100:
            textOut += getDataText(res["data"])  # 获取拼接结果
        elif res["code"] == 101:
            textOut += "无文字"
        else:
            textOut += f"错误原因：{res['data']}"
        print(textOut)

    def openOutputFile(self):  # 打开输出文件
        if self.outputPath and os.path.exists(self.outputPath):
            Platform.startfile(self.outputPath)

    def onEnd(self):  # 结束输出。
        if self._writer:
            self._writer.close()
            self._writer = None

    def __del__(self):
        """析构函数"""
        self.onEnd()
