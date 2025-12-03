from .output import Output
from .tools import getDataText
import os
import base64
from bs4 import BeautifulSoup


class OutputHtml(Output):
    def __init__(self, argd):
        super().__init__(argd)
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.html"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        self.includeImages = argd.get("includeImages", True)  # 是否包含图片
        self.textHighlight = argd.get("textHighlight", False)  # 是否高亮文字

        # 初始化HTML文件
        self.initHtmlFile()

    def initHtmlFile(self):
        """初始化HTML文件"""
        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR识别结果</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Microsoft YaHei', 'SimSun', Arial, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: #ffffff;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        h1 {
            text-align: center;
            color: #333333;
            margin-bottom: 30px;
            font-size: 28px;
        }

        .result-item {
            margin-bottom: 40px;
            padding: 20px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background-color: #fafafa;
        }

        .result-item h2 {
            color: #2196f3;
            margin-bottom: 15px;
            font-size: 20px;
        }

        .image-container {
            margin-bottom: 20px;
            text-align: center;
        }

        .image-container img {
            max-width: 100%;
            height: auto;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }

        .text-container {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
            font-size: 16px;
            line-height: 1.8;
        }

        .highlight {
            background-color: #ffff00;
            padding: 2px 4px;
            border-radius: 3px;
        }

        .error-message {
            color: #f44336;
            font-weight: bold;
        }

        .no-text {
            color: #ff9800;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>OCR识别结果</h1>
        <div id="results">
        </div>
    </div>
</body>
</html>
        """

        # 确保输出目录存在
        os.makedirs(self.dir, exist_ok=True)

        # 写入HTML文件
        with open(self.outputPath, "w", encoding="utf-8") as f:
            f.write(html_content)

    def print(self, res):  # 输出图片信息
        if not res["code"] == 100 and self.ignoreBlank:
            return  # 忽略空白图片

        # 读取HTML文件
        with open(self.outputPath, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")

        # 创建结果项
        result_item = soup.new_tag("div", **{"class": "result-item"})

        # 图片路径
        image_path = res["path"]
        h2 = soup.new_tag("h2")
        h2.string = f"图片：{os.path.basename(image_path)}"
        result_item.append(h2)

        # 图片预览
        if self.includeImages and os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")

            image_container = soup.new_tag("div", **{"class": "image-container"})
            img = soup.new_tag("img", **{"src": f"data:image/png;base64,{image_data}", "alt": os.path.basename(image_path)})
            image_container.append(img)
            result_item.append(image_container)

        # 识别结果
        text_container = soup.new_tag("div", **{"class": "text-container"})

        if res["code"] == 100:
            text = getDataText(res["data"])
            if self.textHighlight:
                # 简单的文字高亮（这里可以根据需要扩展更复杂的高亮逻辑）
                text = text.replace(" ", "<span class=\"highlight\"> </span>")
            text_container.append(BeautifulSoup(text, "html.parser"))
        elif res["code"] == 101:
            no_text = soup.new_tag("span", **{"class": "no-text"})
            no_text.string = "无文字"
            text_container.append(no_text)
        else:
            error_message = soup.new_tag("span", **{"class": "error-message"})
            error_message.string = f"错误原因：{res['data']}"
            text_container.append(error_message)

        result_item.append(text_container)

        # 将结果项添加到HTML中
        results_div = soup.find("div", id="results")
        results_div.append(result_item)

        # 保存HTML文件
        with open(self.outputPath, "w", encoding="utf-8") as f:
            f.write(str(soup))

    def onEnd(self):  # 结束输出。
        pass

