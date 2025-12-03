# 输出HTML格式，支持图片预览、文字高亮、保留排版样式

from .output import Output
from .tools import getDataText
import os
import base64

class OutputHTML(Output):
    def __init__(self, argd):
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.html"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        self.includeImages = argd.get("includeImages", True)  # 是否包含图片
        self.imageFormat = argd.get("imageFormat", "relative")  # 图片格式：relative/absolute/base64
        self.results = []  # 存储所有结果，用于生成HTML
        
        # 创建输出文件
        try:
            with open(self.outputPath, "w", encoding="utf-8") as f:
                # 写入HTML头部
                f.write(self._generateHTMLHeader())
        except Exception as e:
            raise Exception(f"Failed to create HTML file. {e}\n创建HTML文件失败。")

    def _generateHTMLHeader(self):
        """生成HTML头部"""
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR识别结果 - {self.fileName}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #ddd; }}
        .header h1 {{ margin: 0; color: #333; }}
        .header p {{ margin: 5px 0 0 0; color: #666; }}
        .result-item {{ background-color: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .result-item h2 {{ margin-top: 0; color: #333; font-size: 18px; }}
        .image-container {{ margin: 15px 0; text-align: center; }}
        .image-container img {{ max-width: 100%; height: auto; border-radius: 4px; border: 1px solid #eee; }}
        .text-container {{ margin: 15px 0; line-height: 1.6; color: #333; }}
        .text-block {{ margin-bottom: 10px; padding: 8px 12px; background-color: #f9f9f9; border-radius: 4px; border-left: 3px solid #4CAF50; }}
        .error-message {{ color: #f44336; background-color: #ffebee; padding: 10px; border-radius: 4px; }}
        .no-text {{ color: #999; font-style: italic; }}
        .stats {{ margin-top: 30px; padding: 15px; background-color: white; border-radius: 8px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>OCR识别结果</h1>
            <p>{self.fileName}</p>
        </div>
        <div class="results">
"""

    def _generateHTMLFooter(self, total, success, error):
        """生成HTML底部"""
        return f"""
        </div>
        <div class="stats">
            <p>总计: {total} 张图片 | 成功: {success} 张 | 失败: {error} 张</p>
        </div>
    </div>
</body>
</html>
"""

    def _getImageSrc(self, res):
        """获取图片的src属性值"""
        if not self.includeImages:
            return ""
            
        if self.imageFormat == "absolute":
            return res["path"]
        elif self.imageFormat == "base64":
            try:
                with open(res["path"], "rb") as f:
                    image_data = base64.b64encode(f.read()).decode("utf-8")
                    ext = os.path.splitext(res["path"])[1][1:].lower()
                    return f"data:image/{ext};base64,{image_data}"
            except Exception:
                return ""
        else:  # relative
            return os.path.relpath(res["path"], os.path.dirname(self.outputPath)).replace("\\", "/")

    def print(self, res):  # 输出图片结果
        self.results.append(res)
        
        if not res["code"] == 100 and self.ignoreBlank:
            return  # 忽略空白图片
            
        image_src = self._getImageSrc(res)
        
        # 生成单个结果的HTML
        result_html = f"""
            <div class="result-item">
                <h2>{res['fileName']}</h2>
        """
        
        # 添加图片
        if image_src:
            result_html += f"""
                <div class="image-container">
                    <img src="{image_src}" alt="{res['fileName']}">
                </div>
            """
        
        # 添加文本内容
        if res["code"] == 100:
            text_blocks = getDataText(res["data"]).split("\n")
            result_html += "<div class=\"text-container\">"
            for block in text_blocks:
                if block.strip():
                    result_html += f"<div class=\"text-block\">{block}</div>"
            result_html += "</div>"
        elif res["code"] == 101:
            result_html += "<div class=\"no-text\">无文字</div>"
        else:
            result_html += f"<div class=\"error-message\">[Error] OCR识别失败。Code: {res['code']}, Msg: {res['data']}</div>"
        
        result_html += "</div>"
        
        # 追加到文件
        with open(self.outputPath, "a", encoding="utf-8") as f:
            f.write(result_html)

    def onEnd(self):  # 结束输出
        # 统计结果
        total = len(self.results)
        success = sum(1 for res in self.results if res["code"] == 100)
        error = sum(1 for res in self.results if res["code"] != 100 and res["code"] != 101)
        
        # 写入HTML底部
        with open(self.outputPath, "a", encoding="utf-8") as f:
            f.write(self._generateHTMLFooter(total, success, error))
