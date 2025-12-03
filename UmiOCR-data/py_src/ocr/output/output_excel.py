# 输出Excel格式（.xlsx）

from .output import Output
from .tools import getDataText
import os
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter


class OutputExcel(Output):
    def __init__(self, argd):
        self.dir = argd["outputDir"]  # 输出路径（文件夹）
        self.fileName = argd["outputFileName"]  # 文件名
        self.outputPath = f"{self.dir}/{self.fileName}.xlsx"  # 输出路径
        self.ignoreBlank = argd["ignoreBlank"]  # 忽略空白文件
        self.argd = argd  # 保存参数
        
        # 创建工作簿和工作表
        try:
            self.wb = openpyxl.Workbook()
            self.ws = self.wb.active
            self.ws.title = "OCR识别结果"
            
            # 设置表头
            headers = [
                "序号", "图片文件名", "图片路径", "识别状态", 
                "识别文字", "置信度", "识别时间"
            ]
            
            # 设置表头样式
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            thin_border = Border(left=Side(style='thin'), 
                               right=Side(style='thin'), 
                               top=Side(style='thin'), 
                               bottom=Side(style='thin'))
            
            # 写入表头
            for col_num, header in enumerate(headers, 1):
                cell = self.ws.cell(row=1, column=col_num, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border
            
            # 设置列宽
            column_widths = [8, 30, 40, 12, 50, 10, 20]
            for i, width in enumerate(column_widths, 1):
                self.ws.column_dimensions[get_column_letter(i)].width = width
            
            self.row_num = 2  # 从第二行开始写入数据
            
        except Exception as e:
            raise Exception(f"Failed to create Excel file. {e}\n创建Excel文件失败。")

    def print(self, res):  # 输出图片结果
        if not res["code"] == 100 and self.ignoreBlank:
            return  # 忽略空白图片
        
        # 准备数据
        row_data = []
        
        # 序号
        row_data.append(self.row_num - 1)
        
        # 图片文件名
        row_data.append(res["fileName"])
        
        # 图片路径
        row_data.append(res["path"])
        
        # 识别状态
        if res["code"] == 100:
            row_data.append("成功")
        elif res["code"] == 101:
            row_data.append("无文字")
        else:
            row_data.append(f"失败({res['code']})")
        
        # 识别文字
        if res["code"] == 100:
            row_data.append(getDataText(res["data"]))
        elif res["code"] == 101:
            row_data.append("")
        else:
            row_data.append(res["data"])
        
        # 置信度（如果有）
        confidence = ""
        if res["code"] == 100 and "data" in res:
            # 尝试从OCR结果中提取置信度
            if isinstance(res["data"], list) and res["data"]:
                first_item = res["data"][0]
                if isinstance(first_item, dict) and "score" in first_item:
                    confidence = f"{first_item['score']:.2f}"
        row_data.append(confidence)
        
        # 识别时间
        if "timestamp" in res:
            from datetime import datetime
            row_data.append(datetime.fromtimestamp(res["timestamp"]).strftime("%Y-%m-%d %H:%M:%S"))
        else:
            row_data.append("")
        
        # 设置数据单元格样式
        data_alignment = Alignment(vertical="top", wrap_text=True)
        thin_border = Border(left=Side(style='thin'), 
                           right=Side(style='thin'), 
                           top=Side(style='thin'), 
                           bottom=Side(style='thin'))
        
        # 写入数据
        for col_num, value in enumerate(row_data, 1):
            cell = self.ws.cell(row=self.row_num, column=col_num, value=value)
            cell.alignment = data_alignment
            cell.border = thin_border
        
        self.row_num += 1

    def onEnd(self):  # 结束输出
        try:
            # 冻结首行
            self.ws.freeze_panes = "A2"
            
            # 保存工作簿
            self.wb.save(self.outputPath)
            print(f"Excel文件已保存：{self.outputPath}")
        except Exception as e:
            raise Exception(f"Failed to save Excel file. {e}\n保存Excel文件失败。")