# 输出到txt文件

from .output import Output
from .tools import getDataText
from ...utils.safe_file_ops import safe_write, ensure_directory_exists


class OutputTxt(Output):
    def __init__(self, argd):
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.txt"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        # 确保目录存在
        ensure_directory_exists(self.outputPath)
        # 创建输出文件
        try:
            safe_write(self.outputPath, f'{argd["startDatetime"]}\n\n', mode="w", encoding="utf-8", description="txt_output_init")
        except Exception as e:
            raise Exception(f"Failed to create txt file. {e}\n创建txt文件失败。")

    def print(self, res):  # 输出图片结果
        if not res["code"] == 100 and self.ignoreBlank:
            return  # 忽略空白图片
        textOut = f'≦ {res["fileName"]} ≧\n'
        if res["code"] == 100:
            textOut += getDataText(res["data"])  # 获取拼接结果
            textOut += "\n"  # 结尾额外加换行
        elif res["code"] == 101:
            pass
        else:
            textOut += f'[Error] OCR failed. Code: {res["code"]}, Msg: {res["data"]}\n【异常】OCR识别失败。\n'
        textOut += "\n"  # 多空一行
        # 追加写入文件
        safe_write(self.outputPath, textOut, mode="a", encoding="utf-8", description="txt_output_print")
