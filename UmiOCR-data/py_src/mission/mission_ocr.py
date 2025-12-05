# ===============================================
# =============== OCR - 任务管理器 ===============
# ===============================================

"""
一种任务管理器为全局单例，不同标签页要执行同一种任务，要访问对应的任务管理器。
任务管理器中有一个引擎API实例，所有任务均使用该API。
标签页可以向任务管理器提交一组任务队列，其中包含了每一项任务的信息，及总体的参数和回调。
"""

import os
import threading
import time
from typing import List, Dict, Optional

from imports.umi_log import logger
from .mission import Mission
from ..ocr.tbpu import getParser, IgnoreArea
from ..ocr.api import getApiOcr, getLocalOptions
from ..utils.utils import argdIntConvert
from ..image_slicer import get_global_slicer, SliceInfo
from ..memory_pool import get_memory_pool, BufferType
from ..scheduler import get_task_scheduler, TaskType, TaskPriority
from ..monitoring import get_performance_monitor, MetricType

# 合法文件后缀
ImageSuf = [
    ".jpg",
    ".jpe",
    ".jpeg",
    ".jfif",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
]


class __MissionOcrClass(Mission):
    def __init__(self):
        super().__init__()
        self._apiKey = ""  # 当前api类型
        self._api = None  # 当前引擎api对象

    # ========================= 【重载】 =========================

    # msnInfo: { 回调函数"onXX", 参数"argd":{"tbpu.xx", "ocr.xx"} }
    # msnList: [ { "path", "bytes", "base64" } ]
    def addMissionList(self, msnInfo, msnList):  # 添加任务列表
        # 实例化 tbpu 文本后处理模块
        msnInfo["tbpu"] = []
        argd = msnInfo["argd"]
        # 忽略区域
        if "tbpu.ignoreArea" in argd:
            iArea = argd["tbpu.ignoreArea"]
            if isinstance(iArea, list) and len(iArea) > 0:
                msnInfo["tbpu"].append(IgnoreArea(iArea))
        # 获取排版解析器对象
        if "tbpu.parser" in argd:
            msnInfo["tbpu"].append(getParser(argd["tbpu.parser"]))
        # 检查任务合法性
        for i in range(len(msnList) - 1, -1, -1):
            if "path" in msnList[i]:
                p = msnList[i]["path"]
                if os.path.splitext(p)[-1].lower() not in ImageSuf:
                    logger.warning(f"添加OCR任务时，第{i}项的路径path不是图片：{p}")
                    del msnList[i]
            elif "bytes" not in msnList[i] and "base64" not in msnList[i]:
                logger.warning(f"添加OCR任务时，第{i}项不含 path、bytes、base64")
                del msnList[i]
        return super().addMissionList(msnInfo, msnList)

    def msnPreTask(self, msnInfo):  # 用于更新api和参数
        # 检查API对象
        if not self._api:
            return "[Error] MissionOCR: API object is None."
        # 检查参数更新
        startInfo = self._dictShortKey(msnInfo["argd"])
        # 恢复int类型
        argdIntConvert(startInfo)
        msg = self._api.start(startInfo)
        if msg.startswith("[Error]"):
            logger.error(f"OCR引擎启动失败： {msg}")
            return msg  # 更新失败，结束该队列
        else:
            return ""  # 更新成功 TODO: continue

    def msnTask(self, msnInfo, msn):  # 执行msn
        # 检查是否需要切片处理
        slicing_enabled = msnInfo.get("argd", {}).get("slicing.enable", True)
        
        if slicing_enabled:
            return self._msnTaskWithSlicing(msnInfo, msn)
        else:
            return self._msnTaskWithoutSlicing(msnInfo, msn)
    
    def _msnTaskWithoutSlicing(self, msnInfo, msn):
        """不使用切片的任务执行"""
        if "path" in msn:
            res = self._api.runPath(msn["path"])
            res["path"] = msn["path"]  # 结果字典中补充参数
        elif "bytes" in msn:
            res = self._api.runBytes(msn["bytes"])
        elif "base64" in msn:
            res = self._api.runBase64(msn["base64"])
        else:
            res = {
                "code": 901,
                "data": f"[Error] Unknown task type.\n【异常】未知的任务类型。\n{str(msn)[:100]}",
            }
        # 任务成功时的后处理
        if res["code"] == 100:
            # 计算平均置信度
            score, num = 0, 0
            for r in res["data"]:
                score += r["score"]
                num += 1
            if num > 0:
                score /= num
            res["score"] = score
            # 执行 tbpu
            if msnInfo["tbpu"]:
                for tbpu in msnInfo["tbpu"]:
                    res["data"] = tbpu.run(res["data"])
                    # 如果忽略区域等处理将所有文本删除，则结束tbpu
                    if not res["data"]:
                        res["code"] = 101
                        res["data"] = ""
                        break
        return res
    
    def _msnTaskWithSlicing(self, msnInfo, msn):
        """使用切片的任务执行"""
        slicer = get_global_slicer()
        monitor = get_performance_monitor()
        batch_id = monitor.start_batch(task_count=1)
        
        try:
            # 读取图片并获取尺寸
            if "path" in msn:
                # 先获取图片尺寸
                width, height = self._get_image_size(msn["path"])
                if not width or not height:
                    return self._msnTaskWithoutSlicing(msnInfo, msn)
                    
                # 计算切片
                slice_infos = slicer.calculate_slices(width, height)
                
                if len(slice_infos) > 1:
                    logger.debug(f"图片 {msn['path']} 将被分割为 {len(slice_infos)} 个切片")
                    monitor.record_task_metric(
                        task_id=f"msn_{id(msnInfo)}",
                        metric_type=MetricType.TASK_THROUGHPUT,
                        value=len(slice_infos),
                        unit="切片",
                        metadata={"image_size": f"{width}x{height}"}
                    )
                    return self._process_image_with_slices(msnInfo, msn, slice_infos, batch_id=batch_id)
                else:
                    return self._msnTaskWithoutSlicing(msnInfo, msn)
                    
            elif "bytes" in msn or "base64" in msn:
                # 对于字节数据，先解码获取尺寸
                image = self._decode_image(msn)
                if not image:
                    return self._msnTaskWithoutSlicing(msnInfo, msn)
                    
                width, height = self._get_image_dimensions(image)
                if not width or not height:
                    return self._msnTaskWithoutSlicing(msnInfo, msn)
                    
                # 计算切片
                slice_infos = slicer.calculate_slices(width, height)
                
                if len(slice_infos) > 1:
                    logger.debug(f"图片将被分割为 {len(slice_infos)} 个切片")
                    monitor.record_task_metric(
                        task_id=f"msn_{id(msnInfo)}",
                        metric_type=MetricType.TASK_THROUGHPUT,
                        value=len(slice_infos),
                        unit="切片",
                        metadata={"image_size": f"{width}x{height}"}
                    )
                    return self._process_image_with_slices(msnInfo, msn, slice_infos, image, batch_id=batch_id)
                else:
                    return self._msnTaskWithoutSlicing(msnInfo, msn)
                    
            else:
                return self._msnTaskWithoutSlicing(msnInfo, msn)
                
        except Exception as e:
            logger.error(f"切片处理失败: {e}", exc_info=True)
            # 切片处理失败时，回退到普通处理
            return self._msnTaskWithoutSlicing(msnInfo, msn)
    
    def _get_image_size(self, path: str) -> tuple[int, int]:
        """获取图片尺寸"""
        try:
            from PIL import Image
            with Image.open(path) as img:
                return img.size
        except Exception:
            try:
                from PySide2.QtGui import QImage
                img = QImage(path)
                if img.isNull():
                    return 0, 0
                return img.width(), img.height()
            except Exception:
                return 0, 0
    
    def _decode_image(self, msn: dict):
        """解码图片数据"""
        try:
            if "bytes" in msn:
                from PySide2.QtGui import QImage
                img = QImage.fromData(msn["bytes"])
                return img if not img.isNull() else None
            elif "base64" in msn:
                import base64
                from PySide2.QtGui import QImage
                img_data = base64.b64decode(msn["base64"])
                img = QImage.fromData(img_data)
                return img if not img.isNull() else None
        except Exception:
            return None
        return None
    
    def _get_image_dimensions(self, image) -> tuple[int, int]:
        """获取图片尺寸"""
        try:
            if hasattr(image, 'width') and hasattr(image, 'height'):
                return image.width(), image.height()
            elif hasattr(image, 'size'):
                return image.size
        except Exception:
            pass
        return 0, 0
    
    def _process_image_with_slices(self, msnInfo, msn, slice_infos: List[SliceInfo], image=None, batch_id=None):
        """并行处理图片切片"""
        slicer = get_global_slicer()
        results = []
        errors = []
        lock = threading.Lock()
        memory_pool = get_memory_pool()
        monitor = get_performance_monitor()
        
        # 处理函数
        def process_slice(slice_info: SliceInfo):
            buffer_info = None
            start_time = time.time()
            task_id = f"slice_{id(msnInfo)}_{slice_info.slice_index}"
            try:
                # 切片图片
                if image:
                    # 尝试使用内存池缓冲区
                    buffer_info = memory_pool.allocate_buffer(
                        BufferType.CPU_IMAGE, 
                        (slice_info.width, slice_info.height), 
                        buffer_owner=f"slice_processing_{slice_info.slice_index}"
                    )
                    
                    if buffer_info:
                        try:
                            slice_img = slicer.slice_image(image, slice_info)
                            buffer_info.buffer.paste(slice_img)
                            slice_img = buffer_info.buffer
                        except Exception:
                            # 如果使用内存池失败，回退到常规方式
                            memory_pool.release_buffer(buffer_info)
                            buffer_info = None
                            slice_img = slicer.slice_image(image, slice_info)
                    else:
                        slice_img = slicer.slice_image(image, slice_info)
                else:
                    # 从路径重新加载并切片
                    from PIL import Image
                    with Image.open(msn["path"]) as img:
                        # 尝试使用内存池缓冲区
                        buffer_info = memory_pool.allocate_buffer(
                            BufferType.CPU_IMAGE, 
                            (slice_info.width, slice_info.height), 
                            buffer_owner=f"slice_processing_{slice_info.slice_index}"
                        )
                        
                        if buffer_info:
                            try:
                                slice_img = slicer.slice_image(img, slice_info)
                                buffer_info.buffer.paste(slice_img)
                                slice_img = buffer_info.buffer
                            except Exception:
                                # 如果使用内存池失败，回退到常规方式
                                memory_pool.release_buffer(buffer_info)
                                buffer_info = None
                                slice_img = slicer.slice_image(img, slice_info)
                        else:
                            slice_img = slicer.slice_image(img, slice_info)
                
                # 转换为字节数据
                slice_bytes = self._image_to_bytes(slice_img)
                if not slice_bytes:
                    with lock:
                        errors.append(f"切片 {slice_info.slice_index} 转换失败")
                    return
                
                # 执行OCR
                res = self._api.runBytes(slice_bytes)
                
                with lock:
                    results.append((slice_info, res))
                    
            except Exception as e:
                with lock:
                    errors.append(f"切片 {slice_info.slice_index} 处理失败: {e}")
                # 记录错误
                monitor.record_task_metric(
                    task_id=task_id,
                    metric_type=MetricType.ERROR_RATE,
                    value=1.0,
                    unit="",
                    metadata={"error": str(e)}
                )
            finally:
                # 释放内存池缓冲区
                if buffer_info:
                    memory_pool.release_buffer(buffer_info)
                # 记录处理时间
                processing_time = time.time() - start_time
                monitor.record_task_metric(
                    task_id=task_id,
                    metric_type=MetricType.PROCESSING_TIME,
                    value=processing_time,
                    unit="秒",
                    metadata={
                        "slice_index": slice_info.slice_index,
                        "batch_id": batch_id,
                        "slice_region": f"{slice_info.x},{slice_info.y},{slice_info.width},{slice_info.height}"
                    }
                )
        
        # 使用任务调度器并行处理所有切片
        scheduler = get_task_scheduler()
        task_ids = []
        
        for slice_info in slice_infos:
            # 根据切片尺寸确定任务类型
            slice_size = (slice_info.width, slice_info.height)
            
            # 提交任务到调度器
            task_id = scheduler.submit_task(
                process_slice, 
                slice_info,
                image_size=slice_size,
                task_type=TaskType.OCR_SMALL,  # 切片任务视为小图任务
                priority=TaskPriority.MEDIUM
            )
            task_ids.append(task_id)
        
        # 等待所有任务完成
        start_wait_time = time.time()
        while True:
            all_completed = True
            for task_id in task_ids:
                task_info = scheduler.get_task_info(task_id)
                if task_info and not task_info.is_completed:
                    all_completed = False
                    break
            if all_completed:
                break
            time.sleep(0.01)  # 短暂等待后重试
        wait_time = time.time() - start_wait_time
        
        # 记录等待时间
        monitor.record_task_metric(
            task_id=f"msn_{id(msnInfo)}",
            metric_type=MetricType.WAITING_TIME,
            value=wait_time,
            unit="秒",
            metadata={"task_count": len(task_ids)}
        )
        
        # 处理结果
        if errors:
            logger.warning(f"部分切片处理失败: {errors}")
            
        if not results:
            return {
                "code": 902,
                "data": f"[Error] All slices processing failed.\n【异常】所有切片处理失败。"
            }
        
        # 合并结果
        slice_results = [res for _, res in results]
        merged_result = slicer.merge_results(slice_results, slice_infos)
        
        # 补充原始图片信息
        if "path" in msn:
            merged_result["path"] = msn["path"]
            
        # 执行 tbpu
        if merged_result["code"] == 100 and msnInfo["tbpu"]:
            for tbpu in msnInfo["tbpu"]:
                merged_result["data"] = tbpu.run(merged_result["data"])
                # 如果忽略区域等处理将所有文本删除，则结束tbpu
                if not merged_result["data"]:
                    merged_result["code"] = 101
                    merged_result["data"] = ""
                    break
        
        # 结束批次
        if batch_id:
            monitor.end_batch(batch_id)
        
        return merged_result
    
    def _image_to_bytes(self, image) -> Optional[bytes]:
        """将图片转换为字节数据"""
        try:
            if hasattr(image, 'tobytes'):  # PIL.Image
                import io
                # 尝试从内存池获取缓冲区
                memory_pool = get_memory_pool()
                width, height = image.size
                buffer_size = (width * height * 3,)  # RGB 图片的字节数
                
                buffer_info = memory_pool.allocate_buffer(
                    BufferType.CPU_BYTES, 
                    buffer_size, 
                    buffer_owner="image_to_bytes"
                )
                
                if buffer_info:
                    # 使用内存池缓冲区
                    try:
                        buffer = io.BytesIO(buffer_info.buffer)
                        image.save(buffer, format='PNG')
                        result = buffer.getvalue()
                        memory_pool.release_buffer(buffer_info)
                        return result
                    except Exception:
                        # 如果使用内存池失败，回退到常规方式
                        memory_pool.release_buffer(buffer_info)
                
                # 常规方式
                buf = io.BytesIO()
                image.save(buf, format='PNG')
                return buf.getvalue()
            elif hasattr(image, 'save'):  # QImage
                from PySide2.QtCore import QByteArray, QBuffer
                ba = QByteArray()
                buffer = QBuffer(ba)
                buffer.open(QBuffer.WriteOnly)
                image.save(buffer, 'PNG')
                return bytes(ba)
        except Exception:
            pass
        return None

    # ========================= 【qml接口】 =========================

    def getStatus(self):  # 返回当前状态
        return {
            "apiKey": self._apiKey,
            "missionListsLength": self.getMissionListsLength(),
        }

    def setApi(self, apiKey, info):  # 设置api
        # 成功返回 [Success] ，失败返回 [Error] 开头的字符串
        self._apiKey = apiKey
        info = self._dictShortKey(info)
        # 如果api对象已启动，则先停止
        if self._api:
            self._api.stop()
        # 获取新api对象
        res = getApiOcr(apiKey, info)
        # 失败
        if isinstance(res, str):
            self._apiKey = ""
            self._api = None
            return res
        # 成功
        else:
            self._api = res
            return "[Success]"

    # 将字典中配置项的长key转为短key
    # 如： ocr.win32_PaddleOCR-json.path → path
    def _dictShortKey(self, d):
        newD = {}
        key1 = "ocr."
        key2 = key1 + self._apiKey + "."
        for k in d:
            if k.startswith(key2):
                newD[k[len(key2) :]] = d[k]
            elif k.startswith(key1):
                newD[k[len(key1) :]] = d[k]
        return newD

    # ========================= 【qml接口】 =========================

    def getLocalOptions(self):
        if self._apiKey:
            return getLocalOptions(self._apiKey)
        else:
            return {}


# 全局 OCR任务管理器
MissionOCR = __MissionOcrClass()
