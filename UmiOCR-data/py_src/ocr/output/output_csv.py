# 输出到csv表格文件

import csv

from umi_log import logger
from .output import Output
from .tools import getDataText
from ...utils.file_writer import file_writer


class OutputCsv(Output):
    def __init__(self, argd):
        self.encodings = [  # 保存编码优先级
            "ansi",  # Windows系统本地编码。在linux和macos下会抛出异常
            "ascii",  # 纯英
            "gbk",  # 简中
            "big5",  # 繁中
            "shift_jis",  # 日文
            "euc-kr",  # 韩文
            "utf-8",
        ]
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.csv"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        self.writeLists = []  # 输出内容列表
        self.writeText = ""  # 输出内容字符串
        # 覆盖创建临时文件
        if not file_writer.create_file(self.outputPath):
            raise Exception(f"Failed to create csv file.\n创建csv文件失败。")

    def print(self, res):  # 输出图片结果
        if not res["code"] == 100 and self.ignoreBlank:
            return  # 忽略空白图片
        name = res["fileName"]
        path = res["path"]
        if res["code"] == 100:
            textOut = getDataText(res["data"])  # 获取拼接结果
        elif res["code"] == 101:
            textOut = ""
        else:
            textOut = f'[Error] OCR failed. Code: {res["code"]}, Msg: {res["data"]} .\n'
        self.writeLists.append([name, textOut, path])
        self.writeText += textOut

    def onEnd(self):  # 结束时保存。
        # 顺序测试编码优先级列表，获取保存编码
        encoding = "utf-8"
        for e in self.encodings:
            try:
                self.writeText.encode(e)
                encoding = e
                break
            # except UnicodeEncodeError:
            except Exception:
                pass
        logger.info(f"csv encoding: {encoding}")
        # 创建文件、输出
        headers = ["Name", "OCR", "Path"]  # 表头
        try:
            # 使用增强型文件写入工具写入CSV内容
            content = ''
            # 写入表头
            content += ','.join(headers) + '\n'
            # 写入内容
            for writeList in self.writeLists:
                # CSV转义：处理包含逗号、引号的字段
                escaped = []
                for item in writeList:
                    if ',' in item or '
