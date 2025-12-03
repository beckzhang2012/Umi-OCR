# 输出Markdown表格格式

from .output import Output
from .tools import getDataText
import os


class OutputMDTable(Output):
    def __init__(self, argd):
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}_table.md"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        # 创建输出文件
        try:
            with open(self.outputPath, "w", encoding="utf-8") as f:  # 覆盖创建文件
                f.write(f'> OCR识别结果表格\n> {argd["startDatetime"]}\n\n')
        except Exception as e:
            raise Exception(f"Failed to create Markdown table file. {e}\n创建Markdown表格文件失败。")

    def _detect_table_structure(self, texts):
        """检测文本中的表格结构"""
        if not texts:
            return False, []
        
        # 检查是否有类似表格的行结构
        table_lines = []
        for line in texts:
            # 检查是否包含表格分隔符（|）或具有明显的列对齐特征
            if '|' in line:
                table_lines.append(line)
            # 检查是否有重复的分隔线（如---|---|---）
            elif line.strip() and all(c in '-: ' for c in line.strip()):
                table_lines.append(line)
        
        # 如果有足够多的行包含表格特征，则认为是表格
        return len(table_lines) >= 2, table_lines

    def print(self, res):  # 输出图片结果
        if not res["code"] == 100 and self.ignoreBlank:
            return  # 忽略空白图片
        
        name = res["fileName"]
        path = os.path.relpath(  # 从md文件到图片的相对路径
            res["path"], os.path.dirname(self.outputPath)
        )
        path = path.replace(" ", "%20")  # 空格转 %20
        
        textOut = f'''---
## {name}

![{name}]({path})

'''  
        
        # 正文
        if res["code"] == 100:
            texts = getDataText(res["data"]).split("\n")  # 获取拼接结果列表
            
            # 尝试检测表格结构
            is_table, table_lines = self._detect_table_structure(texts)
            
            if is_table:
                textOut += "### 表格识别结果\n\n"
                for line in table_lines:
                    textOut += f"{line}\n"
                textOut += "\n"
            else:
                # 非表格内容，尝试转换为简单表格
                textOut += "### 文本识别结果\n\n"
                textOut += "| 行号 | 内容 |\n"
                textOut += "|------|------|\n"
                for i, t in enumerate(texts, 1):
                    if t.strip():
                        # 转义Markdown特殊字符
                        t = t.replace("|", "\|")
                        t = t.replace("_", "\_")
                        t = t.replace("*", "\*")
                        textOut += f"| {i} | {t} |\n"
        elif res["code"] == 101:
            textOut += "### 无文字\n\n该图片未识别到文字。\n"
        else:
            textOut += f"### 识别失败\n\n[Error] OCR识别失败。Code: {res['code']}, Msg: {res['data']}\n"
        
        with open(self.outputPath, "a", encoding="utf-8") as f:  # 追加写入本地文件
            f.write(textOut)