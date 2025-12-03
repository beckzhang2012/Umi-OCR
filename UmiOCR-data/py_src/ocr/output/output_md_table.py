# 输出Markdown表格格式，自动检测识别结果中的表格结构并转换为Markdown表格

from .output import Output
from .tools import getDataText
import os
import re

class OutputMDTable(Output):
    def __init__(self, argd):
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}_table.md"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        self.includeImages = argd.get("includeImages", True)  # 是否包含图片
        
        # 创建输出文件
        try:
            with open(self.outputPath, "w", encoding="utf-8") as f:  # 覆盖创建文件
                f.write(f'> {argd["startDatetime"]}\n\n')
                f.write(f'# OCR识别结果 - {self.fileName}\n\n')
        except Exception as e:
            raise Exception(f"Failed to create Markdown table file. {e}\n创建Markdown表格文件失败。")

    def _detectTable(self, text):
        """检测文本中的表格结构"""
        lines = text.split("\n")
        if len(lines) < 2:
            return None
            
        # 检测表格分隔符（如：---、===、***等）
        separator_pattern = re.compile(r'^[\s]*[-=*|+#]+[\s]*$')
        
        for i, line in enumerate(lines[1:-1]):
            if separator_pattern.match(line):
                # 找到分隔符，检查上下行是否有内容
                header_line = lines[i].strip()
                data_line = lines[i+2].strip() if i+2 < len(lines) else ""
                
                if header_line and data_line:
                    # 检查是否有列分隔符
                    header_cols = header_line.split("|")
                    data_cols = data_line.split("|")
                    
                    if len(header_cols) >= 2 and len(data_cols) >= 2:
                        # 可能是表格，返回表格的起始和结束行
                        start_line = i
                        end_line = i + 2
                        
                        # 扩展表格范围，找到所有连续的数据行
                        for j in range(i+3, len(lines)):
                            if lines[j].strip() and "|" in lines[j]:
                                end_line = j
                            else:
                                break
                        
                        return (start_line, end_line)
        
        return None

    def _convertToMarkdownTable(self, lines, start_line, end_line):
        """将检测到的表格转换为标准Markdown表格"""
        table_lines = lines[start_line:end_line+1]
        
        # 提取表头和数据
        header_line = table_lines[0].strip()
        separator_line = table_lines[1].strip()
        data_lines = table_lines[2:]
        
        # 清理表头和数据
        header_cols = [col.strip() for col in header_line.split("|") if col.strip()]
        
        # 生成标准Markdown表格
        md_table = []
        md_table.append("| " + " | ".join(header_cols) + " |")
        md_table.append("| " + " | ".join(["---"] * len(header_cols)) + " |")
        
        for line in data_lines:
            cols = [col.strip() for col in line.split("|") if col.strip()]
            # 确保列数一致
            if len(cols) < len(header_cols):
                cols.extend([""] * (len(header_cols) - len(cols)))
            elif len(cols) > len(header_cols):
                cols = cols[:len(header_cols)]
            md_table.append("| " + " | ".join(cols) + " |")
        
        return md_table

    def _processText(self, text):
        """处理文本，检测并转换表格"""
        lines = text.split("\n")
        processed_lines = []
        i = 0
        
        while i < len(lines):
            # 尝试检测表格
            table_range = self._detectTable("\n".join(lines[i:]))
            
            if table_range:
                start_line, end_line = table_range
                # 转换表格
                md_table = self._convertToMarkdownTable(lines[i:], start_line, end_line)
                processed_lines.extend(md_table)
                # 跳过已处理的行
                i += end_line + 1
            else:
                # 普通文本，直接添加
                processed_lines.append(lines[i])
                i += 1
        
        return "\n".join(processed_lines)

    def print(self, res):  # 输出图片结果
        if not res["code"] == 100 and self.ignoreBlank:
            return  # 忽略空白图片
            
        name = res["fileName"]
        path = os.path.relpath(  # 从md文件到图片的相对路径
            res["path"], os.path.dirname(self.outputPath)
        )
        path = path.replace(" ", "%20")  # 空格转 %20
        
        textOut = f"""
---
## {name}
"""
        
        # 添加图片
        if self.includeImages:
            textOut += f"""
![{name}]({path})
[{name}]({path})

"""
        
        # 正文
        if res["code"] == 100:
            raw_text = getDataText(res["data"])
            # 处理文本，检测并转换表格
            processed_text = self._processText(raw_text)
            
            # 将处理后的文本格式化为Markdown
            lines = processed_text.split("\n")
            for t in lines:
                if t.strip():
                    # 检查是否是表格行
                    if t.startswith("| ") and t.endswith(" |"):
                        textOut += f"{t}\n"
                    else:
                        textOut += f"> {t}  \n"
        elif res["code"] == 101:
            textOut += "> 无文字  \n"
        else:
            textOut += f'> [Error] OCR failed. Code: {res["code"]}, Msg: {res["data"]}  \n> 【异常】OCR识别失败。  \n'
        
        # 追加写入本地文件
        with open(self.outputPath, "a", encoding="utf-8") as f:
            f.write(textOut)
