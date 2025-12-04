# 输出到jsonl文件

from .output import Output
import json
from ...utils.safe_file_ops import safe_write, ensure_directory_exists


class OutputJsonl(Output):
    def __init__(self, argd):
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.jsonl"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        # 确保目录存在
        ensure_directory_exists(self.outputPath)
        # 创建输出文件
        try:
            safe_write(self.outputPath, "", mode="w", encoding="utf-8", description="jsonl_output_init")
        except Exception as e:
            raise Exception(f"Failed to create jsonl file. {e}\n创建jsonl文件失败。")

    def print(self, res):  # 输出图片结果
        # 不忽略空白条目
        json_line = json.dumps(res, ensure_ascii=False) + "\n"
        safe_write(self.outputPath, json_line, mode="a", encoding="utf-8", description="jsonl_output_print")
