# 性能监控界面 (Performance Monitor)

Umi-OCR的可视化性能监控界面，帮助用户实时观察OCR运行状态并及时告警。

## 功能特性

### 1. 实时性能指标监控
- **CPU使用率**：实时显示CPU占用率
- **GPU使用率**：实时显示GPU占用率
- **内存使用率**：实时显示内存占用率
- **任务统计**：显示任务总数、成功数、失败数和失败率
- **自动刷新**：每秒更新一次性能数据

### 2. 阈值告警系统
- **自定义阈值**：可配置各指标的告警阈值
- **多种告警方式**：
  - 弹出提醒对话框
  - 写入umi_log日志文件
  - 系统通知推送
- **实时监控**：指标超过阈值时立即触发告警

### 3. 历史数据管理
- **24小时数据存储**：自动保存最近24小时的性能数据
- **时间段选择**：支持查看1小时、24小时、7天的历史数据
- **数据导出**：支持导出为JSON或CSV格式
- **离线分析**：导出的数据可用于后续分析和报告

### 4. 诊断功能
- **一键复制诊断包**：包含当前指标快照、日志段落和硬件信息
- **问题反馈**：方便用户快速反馈问题
- **技术支持**：帮助开发人员快速定位问题

## 技术架构

### 前端 (QML)
- **PerformanceMonitor.qml**：主界面文件
- **Example.qml**：使用示例
- **组件化设计**：MetricCard、StatCard、ChartPanel等可复用组件
- **响应式布局**：支持不同屏幕尺寸

### 后端 (Python)
- **PerformanceMonitor.py**：页面控制器
- **performance_collector.py**：性能指标收集器
- **PubSubService**：实时数据推送机制
- **多线程**：非阻塞的性能数据采集

## 快速开始

### 1. 集成到现有应用

```qml
// 在主应用中加载性能监控页面
Loader {
    anchors.fill: parent
    source: "TabPages/PerformanceMonitor/PerformanceMonitor.qml"
}
```

### 2. 独立运行示例

```qml
// 运行Example.qml
ApplicationWindow {
    visible: true
    width: 1200
    height: 800
    
    Loader {
        anchors.fill: parent
        source: "TabPages/PerformanceMonitor/Example.qml"
    }
}
```

### 3. 启动性能收集器

```python
from monitoring.performance_collector import PerformanceCollector

# 启动性能收集器
collector = PerformanceCollector()
collector.start()

# 停止性能收集器
collector.stop()
```

## API 参考

### Python 控制器方法

#### 阈值配置
```python
# 获取阈值
cpu_threshold = pyCtrl.getThreshold("cpu_usage")

# 设置阈值
pyCtrl.setThreshold("cpu_usage", 80)
```

#### 告警配置
```python
# 获取告警配置
popup_enabled = pyCtrl.getAlertConfig("enable_popup")

# 设置告警配置
pyCtrl.setAlertConfig("enable_popup", True)
```

#### 数据导出
```python
# 导出数据到文件
result = pyCtrl.exportToFile("all", "24h", fileUrl)
```

#### 诊断功能
```python
# 复制诊断包到剪贴板
success = pyCtrl.copyDiagnosticPackage()
```

### QML 回调方法

#### 更新指标
```qml
function updateMetrics(newMetrics) {
    // 处理新的性能指标数据
}
```

#### 显示告警
```qml
function showAlert(message, timestamp) {
    // 显示告警信息
}
```

## 配置说明

### 默认阈值
| 指标 | 默认值 | 范围 |
|------|--------|------|
| CPU使用率 | 80% | 0-100 |
| GPU使用率 | 90% | 0-100 |
| 内存使用率 | 85% | 0-100 |
| 失败率 | 10% | 0-100 |

### 告警配置
| 选项 | 默认值 | 说明 |
|------|--------|------|
| 弹出提醒 | true | 显示告警对话框 |
| 写入日志 | true | 写入umi_log.log |
| 系统通知 | false | 发送系统通知 |

## 数据格式

### JSON 导出格式
```json
{
    "timestamp": "2024-01-01 12:00:00",
    "metrics": {
        "cpu_usage": 45.5,
        "gpu_usage": 30.2,
        "memory_usage": 65.8,
        "task_throughput": 10,
        "failure_rate": 2.5,
        "total_tasks": 100,
        "success_tasks": 97,
        "failed_tasks": 3
    }
}
```

### CSV 导出格式
```csv
timestamp,cpu_usage,gpu_usage,memory_usage,task_throughput,failure_rate,total_tasks,success_tasks,failed_tasks
2024-01-01 12:00:00,45.5,30.2,65.8,10,2.5,100,97,3
```

## 性能优化

### 1. 懒加载机制
- 图表数据按需加载
- 历史数据分页显示
- 避免一次性加载大量数据

### 2. 线程安全
- 使用PubSubService进行线程间通信
- 主线程只负责UI渲染
- 数据采集在后台线程进行

### 3. 内存管理
- 限制历史数据存储时间（24小时）
- 定期清理过期数据
- 优化数据结构

## 故障排除

### 常见问题

#### 1. 性能数据不更新
- 检查PerformanceCollector是否已启动
- 确认PubSubService连接正常
- 查看日志文件是否有错误信息

#### 2. 告警不触发
- 检查阈值配置是否正确
- 确认告警配置已启用
- 验证指标数据是否超过阈值

#### 3. 导出失败
- 检查文件路径是否有效
- 确认有写入权限
- 验证数据格式是否正确

### 日志查看

日志文件位于：
```
UmiOCR-data/log/umi_log.log
```

查看性能监控相关日志：
```bash
grep "PerformanceMonitor" umi_log.log
```

## 开发指南

### 1. 添加新的性能指标

1. 在`performance_collector.py`中添加指标采集逻辑
2. 在`PerformanceMonitor.py`中更新数据处理
3. 在`PerformanceMonitor.qml`中添加UI组件
4. 更新阈值配置和告警逻辑

### 2. 自定义UI组件

1. 创建新的QML组件文件
2. 在`PerformanceMonitor.qml`中导入并使用
3. 确保组件支持响应式布局
4. 添加必要的属性和信号

### 3. 扩展告警方式

1. 在`PerformanceMonitor.py`中添加新的告警方法
2. 在QML中添加配置选项
3. 实现相应的通知逻辑
4. 更新文档和示例

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进性能监控界面。

## 联系方式

如有问题或建议，请通过以下方式联系：
- GitHub Issues
- 项目讨论区
- 开发者邮箱
