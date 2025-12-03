from .output import Output
from .tools import getDataText
import os
import re


class OutputMdTable(Output):
    def __init__(self, argd):
        super().__init__(argd)
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.md"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        self.includeConfidence = argd.get("includeConfidence", False)  # 是否包含置信度

        # 初始化Markdown文件
        self.initMdFile()

    def initMdFile(self):
        """初始化Markdown文件"""
        md_content = "# OCR识别结果\n\n"

        # 确保输出目录存在
        os.makedirs(self.dir, exist_ok=True)

        # 写入Markdown文件
        with open(self.outputPath, "w", encoding="utf-8") as f:
            f.write(md_content)

    def print(self, res):  # 输出图片信息
        if not res["code"] == 100 and self.ignoreBlank:
            return  # 忽略空白图片

        # 读取Markdown文件
        with open(self.outputPath, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 图片路径
        image_path = res["path"]
        md_content += f"## 图片：{os.path.basename(image_path)}\n\n"

        # 识别结果
        if res["code"] == 100:
            text = getDataText(res["data"])

            # 尝试检测表格结构并转换为Markdown表格
            table_text = self.detect_and_convert_table(text)
            md_content += table_text + "\n\n"

            # 如果没有检测到表格，输出原始文本
            if table_text == text:
                md_content += "\n"
        elif res["code"] == 101:
            md_content += "无文字\n\n"
        else:
            md_content += f"错误原因：{res['data']}\n\n"

        # 保存Markdown文件
        with open(self.outputPath, "w", encoding="utf-8") as f:
            f.write(md_content)

    def detect_and_convert_table(self, text):
        """尝试检测文本中的表格结构并转换为Markdown表格"""
        lines = text.strip().split("\n")
        if not lines:
            return text

        # 尝试检测表格分隔符（如：---、===、或多个空格/制表符分隔）
        table_detected = False
        table_lines = []
        separator_index = -1

        for i, line in enumerate(lines):
            stripped_line = line.strip()

            # 检查是否是表格分隔符行（如：---或===）
            if re.match(r"^[\-=\s\|+]+$", stripped_line):
                # 检查分隔符行是否有合理的列数
                if "|" in stripped_line:
                    columns = stripped_line.split("|")
                    if len(columns) >= 2:
                        table_detected = True
                        separator_index = i
                        break

        # 如果没有检测到分隔符行，尝试使用空格/制表符分隔的方法
        if not table_detected:
            # 检查所有行是否有相似的结构（使用相同数量的分隔符）
            max_columns = 0
            common_columns = 0

            for line in lines:
                # 检查使用制表符分隔的列数
                tab_columns = len(line.split("\t"))
                if tab_columns > max_columns:
                    max_columns = tab_columns

                # 检查使用多个空格分隔的列数
                space_columns = len(re.split(r"\s{2,}", line.strip()))
                if space_columns > max_columns:
                    max_columns = space_columns

            # 如果所有行都有相同数量的列，且列数大于1，则认为是表格
            if max_columns >= 2:
                table_detected = True

        # 如果检测到表格结构，将其转换为Markdown表格
        if table_detected:
            if separator_index != -1:
                # 使用分隔符行的方法
                table_lines = lines[separator_index - 1:separator_index + 2]
                if len(table_lines) < 3:
                    table_lines = lines[:separator_index + 2]

                # 转换为Markdown表格
                md_table = ""
                for i, line in enumerate(table_lines):
                    if i == 1:
                        # 分隔符行
                        columns = line.split("|")
                        separator_line = "|"
                        for col in columns[1:-1]:
                            separator_line += "---|"
                        md_table += separator_line + "\n"
                    else:
                        # 内容行
                        md_table += line + "\n"

                # 添加剩余的行
                if separator_index + 2 < len(lines):
                    for line in lines[separator_index + 2:]:
                        md_table += line + "\n"

                return md_table
            else:
                # 使用空格/制表符分隔的方法
                md_table = "|"

                # 确定使用哪种分隔符
                use_tab = False
                max_tab_columns = 0
                for line in lines:
                    tab_columns = len(line.split("\t"))
                    if tab_columns > max_tab_columns:
                        max_tab_columns = tab_columns
                        if max_tab_columns >= 2:
                            use_tab = True

                # 转换为Markdown表格
                for i, line in enumerate(lines):
                    if use_tab:
                        columns = line.split("\t")
                    else:
                        columns = re.split(r"\s{2,}", line.strip())

                    # 内容行
                    content_line = "|"
                    for col in columns:
                        content_line += f" {col} |"

                    if i == 0:
                        # 表头行
                        md_table += content_line + "\n"
                        # 分隔符行
                        separator_line = "|"
                        for _ in columns:
                            separator_line += "---|"
                        md_table += separator_line + "\n"
                    else:
                        # 数据行
                        md_table += content_line + "\n"

                return md_table

        # 如果没有检测到表格结构，返回原始文本
        return text

    def onEnd(self):  # 结束输出。
        pass

