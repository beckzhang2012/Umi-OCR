# 单独txt文件

import os
from .output import Output
from .tools import getDataText
from ...utils.safe_file_ops import safe_write, ensure_directory_exists


class OutputTxtIndividual(Output):
    def __init__(self, argd):
        super().__init__(argd)
        # 是否输出到原目录
        self.outputSource = argd["outputDirType"] == "source"

    def openOutputFile(self):
        pass  # 覆盖父类方法

    def print(self, res):  # 输出图片结果
        if not res["code"] == 100 and self.ignoreBlank:
            return  # 忽略空白图片
        textOut = ""
        if res["code"] == 100:
            textOut += getDataText(res["data"])  # 获取拼接结果
        elif res["code"] == 101:
            pass
        else:
            textOut += f'[Error] OCR failed. Code: {res["code"]}, Msg: {res["data"]}\n【异常】OCR识别失败。\n'
        # 输出文件
        if self.outputSource:  # 输出到原始路径
            p, _ = os.path.splitext(res["path"])  # 原路径去除扩展名
            path = p + ".txt"
        else:  # 输出到指定路径
            f, _ = os.path.splitext(res["fileName"])  # 原文件名去除扩展名
            path = f"{self.dir}/{f}.txt"
        
        # 确保目录存在
        ensure_directory_exists(path)
        
        # 写入文件
        safe_write(path, textOut, mode="w", encoding="utf-8", description="txt_individual_output")
