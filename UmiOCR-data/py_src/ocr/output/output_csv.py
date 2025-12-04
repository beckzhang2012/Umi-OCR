# 输出到csv表格文件

import csv
import io
from umi_log import logger
from .output import Output
from .tools import getDataText
from ...utils.safe_file_ops import safe_write, ensure_directory_exists


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
        # 确保目录存在
        ensure_directory_exists(self.outputPath)
        # 创建输出文件
        try:
            safe_write(self.outputPath, "", mode="w", encoding="utf-8", description="csv_output_init")
        except Exception as e:
            raise Exception(f"Failed to create csv file. {e}\n创建csv文件失败。")

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
            # 使用内存缓冲区构建CSV内容
            output = io.StringIO(newline='')
            writer = csv.writer(output)
            writer.writerow(headers)  # 写入CSV表头
            for writeList in self.writeLists:
                writer.writerow(writeList)  # 写入CSV内容
            
            # 获取CSV内容并写入文件
            csv_content = output.getvalue()
            output.close()
            
            safe_write(self.outputPath, csv_content, mode="w", encoding=encoding, description="csv_output_onend")
        except Exception as e:
            raise Exception(f"Failed to write csv file. {e}\n写入csv文件失败。")
