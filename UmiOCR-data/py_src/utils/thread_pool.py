# =====================================================
# =============== 全局线程池 异步任务接口 ===============
# =====================================================

from concurrent.futures import ThreadPoolExecutor

from umi_log import logger

# 全局线程池
GlobalThreadPool = ThreadPoolExecutor()


# 快捷接口：异步运行函数，返回Future对象
def threadRun(taskFunc, *args, **kwargs):
    try:
        future = GlobalThreadPool.submit(taskFunc, *args, **kwargs)
        return future
    except Exception:
        logger.error("异步运行发生错误。", exc_info=True, stack_info=True)
        return None
