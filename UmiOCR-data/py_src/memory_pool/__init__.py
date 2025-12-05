# ===============================================
# =============== 内存池与纹理缓存系统 ===============
# ===============================================

"""
可复用的内存池与纹理缓存系统，避免重复申请/释放 GPU/CPU buffer，
使平均内存申请次数下降 50%。
"""

from .memory_pool import (
    MemoryPool,
    PoolConfig,
    BufferType,
    BufferInfo,
    get_memory_pool,
    set_memory_pool_config,
    global_memory_pool
)

__all__ = [
    'MemoryPool',
    'PoolConfig',
    'BufferType',
    'BufferInfo',
    'get_memory_pool',
    'set_memory_pool_config',
    'global_memory_pool'
]

__version__ = '1.0.0'
