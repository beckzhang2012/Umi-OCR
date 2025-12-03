# 输出Excel格式（.xlsx），每张图片的识别结果占一行，包含图片路径、识别文字、置信度等列

from .output import Output
from .tools import getDataText
import os
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from umi_log import logger

class OutputExcel(Output):
    def __init__(self, argd):
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.xlsx"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        self.includeConfidence = argd.get("includeConfidence", True)  # 是否包含置信度信息
        self.writeRows = []  # 存储所有行数据
        
        # 创建Excel工作簿和工作表
        try:
            self.workbook = openpyxl.Workbook()
            self.worksheet = self.workbook.active
            self.worksheet.title = "OCR识别结果"
            
            # 设置表头
            headers = ["文件名", "图片路径", "识别文字"]
            if self.includeConfidence:
                headers.extend(["平均置信度", "最低置信度", "最高置信度"])
            
            self.worksheet.append(headers)
            
            # 设置表头样式
            header_font = Font(bold=True, color="FFFFFF")
            header_alignment = Alignment(horizontal="center", vertical="center")
            header_border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin")
            )
            
            for cell in self.worksheet[1]:
                cell.font = header_font
                cell.alignment = header_alignment
                cell.border = header_border
                cell.fill = openpyxl.styles.PatternFill(start_color="4CAF50", end_color="4CAF50", fill_type="solid")
                
        except Exception as e:
            raise Exception(f"Failed to create Excel file. {e}\n创建Excel文件失败。")

    def _calculateConfidence(self, data):
        """计算置信度统计信息"""
        if not data or not self.includeConfidence:
            return (None, None, None)
            
        confidences = []
        for tb in data:
            if "confidence" in tb:
                try:
                    conf = float(tb["confidence"])
                    confidences.append(conf)
                except (ValueError, TypeError):
                    pass
            
        if not confidences:
            return (None, None, None)
            
        avg_conf = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)
        
        return (avg_conf, min_conf, max_conf)

    def print(self, res):  # 输出图片结果
        if not res["code"] == 100 and self.ignoreBlank:
            return  # 忽略空白图片
            
        name = res["fileName"]
        path = res["path"]
        
        if res["code"] == 100:
            textOut = getDataText(res["data"])
            avg_conf, min_conf, max_conf = self._calculateConfidence(res["data"])
        elif res["code"] == 101:
            textOut = ""
            avg_conf, min_conf, max_conf = (None, None, None)
        else:
            textOut = f'[Error] OCR failed. Code: {res["code"]}, Msg: {res["data"]} .'
            avg_conf, min_conf, max_conf = (None, None, None)
        
        # 构建行数据
        row = [name, path, textOut]
        if self.includeConfidence:
            row.extend([avg_conf, min_conf, max_conf])
        
        self.writeRows.append(row)

    def onEnd(self):  # 结束时保存
        try:
            # 写入数据行
            data_alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            data_border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin")
            )
            
            for row in self.writeRows:
                self.worksheet.append(row)
                
            # 设置数据行样式和列宽
            for row in self.worksheet.iter_rows(min_row=2, max_row=self.worksheet.max_row):
                for cell in row:
                    cell.alignment = data_alignment
                    cell.border = data_border
                    
                    # 格式化置信度为百分比
                    if cell.column in [4, 5, 6] and cell.value is not None:
                        try:
                            cell.value = f"{cell.value:.2%}"
                        except (ValueError, TypeError):
                            pass
            
            # 调整列宽
            self.worksheet.column_dimensions["A"].width = 20  # 文件名
            self.worksheet.column_dimensions["B"].width = 40  # 图片路径
            self.worksheet.column_dimensions["C"].width = 60  # 识别文字
            if self.includeConfidence:
                self.worksheet.column_dimensions["D"].width = 12  # 平均置信度
                self.worksheet.column_dimensions["E"].width = 12  # 最低置信度
                self.worksheet.column_dimensions["F"].width = 12  # 最高置信度
            
            # 保存工作簿
            self.workbook.save(self.outputPath)
            logger.info(f"Excel file saved successfully: {self.outputPath}")
            
        except Exception as e:
            raise Exception(f"Failed to write Excel file. {e}\n写入Excel文件失败。")
        finally:
            # 关闭工作簿
            self.workbook.close()
