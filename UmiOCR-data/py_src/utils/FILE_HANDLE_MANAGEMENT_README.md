# 文件句柄管理系统

## 概述

这是一个用于Umi-OCR项目的文件句柄管理和监控系统，旨在解决高并发导出时偶发的"输出文件句柄未释放"导致程序退出的问题。

## 核心功能

### 1. 文件句柄池监控
- 实时监控所有文件句柄的创建和销毁
- 跟踪每个句柄的访问时间和使用模式
- 提供句柄使用统计信息

### 2. 安全文件操作
- 使用增强的`with`语句确保文件句柄正确释放
- 自动处理文件写入异常
- 实现失败重试机制

### 3. 待写内容缓存
- 当文件句柄不可用时，自动将待写内容缓存到内存队列
- 定期重试缓存中的写入操作
- 支持最大重试次数和重试延迟配置

### 4. UI通知系统
- 在文件句柄资源紧张时显示警告
- 当系统恢复正常时显示恢复通知
- 提供待写任务数量的实时信息

### 5. 后台监控线程
- 定期扫描未关闭的文件句柄
- 检测长时间未访问的句柄
- 自动触发句柄清理

## 架构设计

```
┌───────────────────────────────────────────────────────────┐
│                    应用层 (OCR输出模块)                    │
└───────────────────────────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────┐
│                安全文件操作层 (safe_file_ops.py)           │
│  - safe_open() 安全文件打开上下文管理器                   │
│  - safe_write() 安全文件写入函数                           │
│  - safe_read() 安全文件读取函数                            │
│  - ensure_directory_exists() 目录创建保障                  │
└───────────────────────────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────┐
│              文件句柄管理层 (file_handle_manager.py)       │
│  - 句柄注册与注销                                         │
│  - 待写内容队列管理                                       │
│  - 自动重试机制                                           │
│  - 后台监控线程                                           │
└───────────────────────────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────┐
│                UI通知层 (ui_notifier.py)                  │
│  - 句柄警告通知                                           │
│  - 恢复通知                                               │
│  - 状态信息显示                                           │
└───────────────────────────────────────────────────────────┘
```

## 集成方法

### 1. 自动初始化

系统会在首次导入时自动初始化：

```python
from utils import init_file_handles  # 自动初始化
```

### 2. 手动初始化

也可以手动初始化：

```python
from utils.init_file_handles import init_file_handle_system

init_file_handle_system()
```

### 3. 修改现有代码

将所有文件操作替换为安全版本：

**原代码：**
```python
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
```

**替换为：**
```python
from utils.safe_file_ops import safe_write

safe_write(file_path, content, mode='w', encoding='utf-8', description='my_output')
```

或者使用上下文管理器：

```python
from utils.safe_file_ops import safe_open

with safe_open(file_path, 'w', encoding='utf-8', description='my_output') as f:
    f.write(content)
```

## 配置参数

### 文件句柄管理器配置

在`file_handle_manager.py`中可以调整以下参数：

- `_max_retries`: 最大重试次数（默认：3）
- `_retry_delay`: 重试延迟（默认：0.1秒）
- 监控间隔：在`start_monitoring(interval=5)`中设置（默认：5秒）

### UI通知器配置

在`ui_notifier.py`中可以调整以下参数：
- 自动通知间隔：在`start_auto_notification(interval=10)`中设置（默认：10秒）

## 监控和调试

### 获取统计信息

```python
from utils.file_handle_manager import file_handle_manager

stats = file_handle_manager.get_stats()
print("文件句柄统计:")
print(f"  总句柄数: {stats['total_handles']}")
print(f"  活跃句柄数: {stats['active_handles']}")
print(f"  待写任务数: {stats['pending_writes']}")
print(f"  写入成功数: {stats['write_successes']}")
print(f"  写入失败数: {stats['write_failures']}")
```

### 获取活跃句柄信息

```python
active_handles = file_handle_manager.get_active_handles()
for handle in active_handles:
    print(f"路径: {handle['path']}, 模式: {handle['mode']}, 描述: {handle['description']}")
```

### 查看日志

系统使用`umi_log`模块记录详细日志，包括：
- 句柄创建和销毁事件
- 写入失败和重试事件
- 系统警告和错误

## 回归测试

### 运行高并发测试

```bash
python -m tests.test_high_concurrency_export
```

测试脚本会：
1. 创建临时测试目录
2. 同时运行多个输出模块的高并发测试
3. 模拟截图OCR导出场景
4. 验证系统稳定性
5. 生成测试报告

### 测试覆盖

- TXT输出模块测试（200任务，15线程）
- CSV输出模块测试（150任务，10线程）
- JSONL输出模块测试（180任务，12线程）
- 综合稳定性测试

## 故障排查

### 常见问题

1. **句柄泄漏**
   - 检查是否所有文件操作都使用了`safe_open`或`safe_write`
   - 查看活跃句柄列表，定位未关闭的句柄
   - 检查是否有长时间未访问的句柄

2. **写入失败**
   - 查看日志中的错误信息
   - 检查待写队列状态
   - 确认磁盘空间和权限

3. **性能问题**
   - 调整监控间隔（增大间隔减少性能开销）
   - 调整重试延迟和最大重试次数
   - 优化文件写入频率

### 日志分析

关键日志级别：
- `DEBUG`: 详细的句柄创建、销毁和监控信息
- `INFO`: 系统状态和统计信息
- `WARNING`: 句柄资源紧张、写入重试等警告
- `ERROR`: 文件操作失败、系统错误等

## 部署建议

1. **生产环境配置**
   - 监控间隔：5-10秒
   - 最大重试次数：3-5次
   - 重试延迟：0.1-0.5秒

2. **性能优化**
   - 对于频繁写入的场景，考虑批量写入
   - 合理设置待写队列警告阈值
   - 定期清理临时文件

3. **监控建议**
   - 定期检查句柄统计信息
   - 设置句柄数量告警阈值
   - 监控待写队列长度

## 未来改进

1. **更智能的重试策略**
   - 基于文件类型和系统负载调整重试参数
   - 实现指数退避算法

2. **更完善的UI集成**
   - 实现托盘通知
   - 添加状态栏指示器
   - 提供句柄监控界面

3. **性能优化**
   - 实现句柄池复用
   - 优化高并发场景下的性能

4. **扩展功能**
   - 支持网络文件系统
   - 添加文件系统健康检查
   - 实现文件写入优先级管理

## 许可证

MIT License
