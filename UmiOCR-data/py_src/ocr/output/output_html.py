# 输出HTML格式

from .output import Output
from .tools import getDataText
import os


class OutputHTML(Output):
    def __init__(self, argd):
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.html"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        # 创建输出文件
        try:
            with open(self.outputPath, "w", encoding="utf-8") as f:  # 覆盖创建文件
                html_header = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR识别结果 - {self.fileName}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; text-align: center; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 30px; }}
        .timestamp {{ color: #666; text-align: center; font-size: 14px; margin-bottom: 30px; }}
        .image-section {{ margin-bottom: 40px; padding: 20px; border: 1px solid #eee; border-radius: 8px; background-color: #fafafa; }}
        .image-title {{ font-size: 18px; font-weight: bold; color: #333; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #ddd; }}
        .image-preview {{ max-width: 100%; height: auto; border-radius: 4px; margin: 15px 0; box-shadow: 0 1px 5px rgba(0,0,0,0.1); }}
        .ocr-text {{ background-color: white; padding: 20px; border-radius: 4px; margin-top: 15px; line-height: 1.6; color: #333; }}
        .text-line {{ margin-bottom: 10px; padding: 5px 10px; border-radius: 3px; transition: background-color 0.2s; }}
        .text-line:hover {{ background-color: #f0f8ff; }}
        .error-message {{ color: #e74c3c; background-color: #fee; padding: 15px; border-radius: 4px; margin-top: 15px; }}
        .no-text {{ color: #999; font-style: italic; padding: 15px; background-color: #f9f9f9; border-radius: 4px; margin-top: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>OCR识别结果</h1>
        <div class="timestamp">{argd["startDatetime"]}</div>
'''
                f.write(html_header)
        except Exception as e:
            raise Exception(f"Failed to create HTML file. {e}\n创建HTML文件失败。")

    def print(self, res):  # 输出图片结果
        if not res["code"] == 100 and self.ignoreBlank:
            return  # 忽略空白图片
        
        name = res["fileName"]
        path = os.path.relpath(  # 从HTML文件到图片的相对路径
            res["path"], os.path.dirname(self.outputPath)
        )
        path = path.replace(" ", "%20")  # 空格转 %20
        
        html_content = f'''        <div class="image-section">
            <div class="image-title">{name}</div>
            <img class="image-preview" src="{path}" alt="{name}">
'''
        
        # 正文
        if res["code"] == 100:
            html_content += '            <div class="ocr-text">\n'
            texts = getDataText(res["data"]).split("\n")  # 获取拼接结果列表
            for t in texts:
                if t.strip():  # 只处理非空行
                    html_content += f'                <div class="text-line">{t}</div>\n'
            html_content += '            </div>\n'
        elif res["code"] == 101:
            html_content += '            <div class="no-text">该图片未识别到文字</div>\n'
        else:
            html_content += f'            <div class="error-message">[Error] OCR识别失败。Code: {res["code"]}, Msg: {res["data"]}</div>\n'
        
        html_content += '        </div>\n'
        
        with open(self.outputPath, "a", encoding="utf-8") as f:  # 追加写入本地文件
            f.write(html_content)

    def onEnd(self):  # 结束输出
        try:
            with open(self.outputPath, "a", encoding="utf-8") as f:
                html_footer = '''    </div>
</body>
</html>'''
                f.write(html_footer)
        except Exception as e:
            print(f"Failed to complete HTML file. {e}\n完成HTML文件失败。")