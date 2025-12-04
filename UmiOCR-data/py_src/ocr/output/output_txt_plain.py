# 纯文本（无格式）txt文件

from .output import Output
from .tools import getDataText
from ...utils.safe_file_ops import safe_write, ensure_directory_exists


class OutputTxtPlain(Output):
    def __init__(self, argd):
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.p.txt"  # 输出路径
        # 确保目录存在
        ensure_directory_exists(self.outputPath)
        # 创建输出文件
        try:
            safe_write(self.outputPath, "", mode="w", encoding="utf-8", description="txt_plain_output_init")
        except Exception as e:
            raise Exception(
                f"Failed to create plain txt file. {e}\n创建纯文本txt文件失败。"
            )

    def print(self, res):  # 输出图片结果
        if not res["code"] == 100:
            return  # 强制忽略空白图片
        textOut = ""
        if res["code"] == 100:
            textOut += getDataText(res["data"])  # 获取拼接结果
            if not textOut[-1] == "\n":  # 确保结尾有换行
                textOut += "\n"
        # 追加写入文件
        safe_write(self.outputPath, textOut, mode="a", encoding="utf-8", description="txt_plain_output_print")
