# 自适应推理调度器

CPU/GPU自适应推理调度器，为OCR任务提供智能的硬件资源管理和调度。

## 功能特性

### 1. 智能硬件检测
- 启动时自动检测系统中可用的GPU设备
- 支持多GPU场景，可配置GPU优先级
- 自动检测CPU核心数和系统内存
- 提供详细的硬件信息报告

### 2. 实时GPU监控
- 实时监控GPU占用率、温度、显存使用情况
- 支持GPU驱动错误检测
- 可配置阈值，超过阈值自动触发切换
- 提供GPU状态实时上报

### 3. 自适应后端切换
- GPU异常时自动切换到CPU模式
- GPU恢复后自动切回GPU模式
- 支持手动切换后端
- 记录切换原因和时间

### 4. 高性能CPU模式
- 多进程/多线程混合策略
- 可配置线程数和进程数
- 保持高吞吐率（≥GPU模式的85%）
- 动态负载均衡

### 5. 统一配置管理
- 支持配置文件加载和保存
- 可动态调整配置参数
- 提供默认配置和验证
- 支持测试模式

### 6. 状态管理和上报
- 统一的状态管理
- 支持UI状态格式化
- 性能指标统计
- 回调机制支持

### 7. 回归测试
- 模拟GPU异常和恢复流程
- 验证任务连续性和结果一致性
- 生成详细测试报告

## 模块结构

```
py_src/
├── adaptive_inference.py          # 主入口模块
├── platform/
│   └── hardware_detector.py       # 硬件检测模块
├── monitoring/
│   └── gpu_monitor.py             # GPU监控模块
├── scheduler/
│   └── adaptive_inference_scheduler.py  # 调度器核心
├── config/
│   └── adaptive_scheduler_config.py     # 配置管理
├── state/
│   └── adaptive_scheduler_state.py      # 状态管理
└── benchmark/
    └── adaptive_scheduler_test.py       # 回归测试
```

## 快速开始

### 1. 基本使用

```python
from adaptive_inference import adaptive_inference

# 初始化OCR API（示例）
class MockOCRAPI:
    def switch_backend(self, backend, config):
        print(f"切换到{backend}模式")
    
    def update_cpu_config(self, config):
        print(f"更新CPU配置: {config}")
    
    def run_ocr(self, image_data):
        return {
            "code": 100,
            "data": [{"text": "测试", "score": 0.95}],
            "backend": "GPU",
            "processing_time": 0.1
        }

ocr_api = MockOCRAPI()

# 启动自适应推理调度器
adaptive_inference.start(ocr_api, "test_ocr")

# 运行OCR任务
image_data = b"image_data"
result = adaptive_inference.run_ocr(image_data)
print("OCR结果:", result)

# 获取当前状态
state = adaptive_inference.get_ui_state()
print("当前状态:", state)

# 停止调度器
adaptive_inference.stop()
```

### 2. 配置管理

```python
from adaptive_inference import adaptive_inference

# 获取当前配置
config = adaptive_inference.get_config()
print("当前配置:", config)

# 更新配置
config_updates = {
    "gpu_thresholds": {
        "utilization_threshold": 90,
        "temperature_threshold": 85
    },
    "cpu": {
        "threads_per_worker": 8
    }
}
adaptive_inference.update_config(config_updates)

# 保存配置到文件
adaptive_inference.save_config("my_config.json")

# 从文件加载配置
adaptive_inference.load_config("my_config.json")
```

### 3. 回调函数

```python
from adaptive_inference import adaptive_inference

# 后端切换回调
def on_backend_switch(backend, reason):
    print(f"后端切换到{backend}，原因: {reason}")

# 状态更新回调
def on_status_update(status):
    print("状态更新:", status)

# 注册回调
adaptive_inference.register_backend_switch_callback(on_backend_switch)
adaptive_inference.register_status_update_callback(on_status_update)
```

### 4. 手动切换后端

```python
from adaptive_inference import adaptive_inference

# 切换到CPU模式
adaptive_inference.switch_backend("CPU", "手动切换")

# 切换到GPU模式
adaptive_inference.switch_backend("GPU", "手动切换")
```

## API参考

### AdaptiveInferenceScheduler类

#### 方法

- `start(ocr_api: Any, api_name: str = "default")`
  启动自适应推理调度器
  - `ocr_api`: OCR API实例
  - `api_name`: API名称

- `stop()`
  停止自适应推理调度器

- `run_ocr(image_data: Any, **kwargs) -> Dict`
  运行OCR任务
  - `image_data`: 图像数据
  - 返回: OCR结果

- `get_state() -> Dict`
  获取当前状态

- `get_ui_state() -> Dict`
  获取用于UI显示的状态

- `get_performance_summary() -> Dict`
  获取性能摘要

- `get_hardware_summary() -> Dict`
  获取硬件摘要

- `get_current_backend() -> str`
  获取当前后端类型（"GPU"或"CPU"）

- `get_switch_reason() -> str`
  获取最后一次切换原因

- `is_gpu_available() -> bool`
  检查GPU是否可用

- `is_running() -> bool`
  检查调度器是否正在运行

- `get_config() -> AdaptiveSchedulerConfig`
  获取当前配置

- `update_config(config_updates: Dict)`
  更新配置
  - `config_updates`: 配置更新字典

- `save_config(config_file: Optional[str] = None)`
  保存配置到文件

- `load_config(config_file: Optional[str] = None)`
  从文件加载配置

- `register_backend_switch_callback(callback: Callable[[str, str], None])`
  注册后端切换回调
  - `callback`: 回调函数，参数为(backend, reason)

- `register_status_update_callback(callback: Callable[[Dict], None])`
  注册状态更新回调
  - `callback`: 回调函数，参数为状态字典

- `switch_backend(backend_type: str, reason: str = "手动切换")`
  手动切换后端
  - `backend_type`: 后端类型（"GPU"或"CPU"）
  - `reason`: 切换原因

- `reset_state()`
  重置状态

- `get_gpu_status() -> Dict`
  获取GPU状态

### 便捷函数

- `start_adaptive_inference(ocr_api: Any, api_name: str = "default")`
  启动自适应推理

- `stop_adaptive_inference()`
  停止自适应推理

- `run_ocr_task(image_data: Any, **kwargs) -> Dict`
  运行OCR任务

- `get_adaptive_inference_state() -> Dict`
  获取自适应推理状态

- `get_adaptive_inference_ui_state() -> Dict`
  获取自适应推理UI状态

- `update_adaptive_inference_config(config_updates: Dict)`
  更新自适应推理配置

- `switch_adaptive_inference_backend(backend_type: str)`
  切换自适应推理后端

## 配置说明

### 默认配置

```python
AdaptiveSchedulerConfig(
    enabled=True,
    backend="auto",
    status_update_interval=5,
    
    gpu_thresholds=GPUThresholdConfig(
        utilization_threshold=85,
        temperature_threshold=90,
        memory_threshold=90,
        threshold_duration=10,
        retry_interval=60,
        recovery_check_interval=30
    ),
    
    cpu=CPUConfig(
        enable_multiprocessing=True,
        enable_multithreading=True,
        max_workers=None,
        threads_per_worker=4,
        queue_size=100,
        batch_size=8
    ),
    
    gpu=GPUConfig(
        enabled=True,
        device_ids=[0],
        priority_order=[0],
        memory_allocation=0.8,
        enable_half_precision=True
    ),
    
    log_level="INFO",
    log_backend_switches=True,
    log_performance_metrics=True,
    
    enable_test_mode=False,
    test_gpu_exception_probability=0.0
)
```

### 配置文件格式

配置文件使用JSON格式，示例：

```json
{
    "enabled": true,
    "backend": "auto",
    "gpu_thresholds": {
        "utilization_threshold": 85,
        "temperature_threshold": 90,
        "memory_threshold": 90,
        "threshold_duration": 10,
        "retry_interval": 60,
        "recovery_check_interval": 30
    },
    "cpu": {
        "enable_multiprocessing": true,
        "enable_multithreading": true,
        "max_workers": null,
        "threads_per_worker": 4,
        "queue_size": 100,
        "batch_size": 8
    },
    "gpu": {
        "enabled": true,
        "device_ids": [0],
        "priority_order": [0],
        "memory_allocation": 0.8,
        "enable_half_precision": true
    }
}
```

## 回归测试

### 运行测试

```python
from benchmark.adaptive_scheduler_test import AdaptiveSchedulerTester

# 创建测试器
tester = AdaptiveSchedulerTester()

# 运行完整测试（60秒）
tester.run_full_test(test_duration=60)

# 生成测试报告
tester.generate_test_report("test_report.json")
```

### 测试内容

测试脚本会模拟以下场景：
1. 调度器启动和初始化
2. 正常OCR任务流
3. GPU异常（高占用、高温度、驱动错误）
4. 自动切换到CPU模式
5. GPU恢复
6. 自动切回GPU模式
7. 任务连续性验证
8. 性能指标统计

### 测试报告

测试报告包含以下信息：
- 测试时间和持续时间
- 后端切换记录
- OCR任务统计
- 性能指标
- 测试结果分析

## 集成示例

### 与现有OCR系统集成

```python
from adaptive_inference import adaptive_inference
from your_ocr_module import YourOCRAPI

# 初始化现有OCR API
your_ocr_api = YourOCRAPI()

# 包装现有API以支持自适应调度
class OCRAPIWrapper:
    def __init__(self, ocr_api):
        self.ocr_api = ocr_api
        self.current_backend = "GPU"
    
    def switch_backend(self, backend, config):
        """切换后端"""
        self.current_backend = backend
        # 这里添加实际的后端切换逻辑
        if backend == "GPU":
            self.ocr_api.enable_gpu()
        else:
            self.ocr_api.disable_gpu()
            self.ocr_api.set_threads(config.get('threads_per_worker', 4))
    
    def update_cpu_config(self, config):
        """更新CPU配置"""
        if self.current_backend == "CPU":
            self.ocr_api.set_threads(config.get('threads_per_worker', 4))
    
    def run_ocr(self, image_data):
        """运行OCR"""
        start_time = time.time()
        result = self.ocr_api.recognize(image_data)
        processing_time = time.time() - start_time
        
        return {
            "code": 100,
            "data": result,
            "backend": self.current_backend,
            "processing_time": processing_time
        }

# 创建包装后的API
wrapped_api = OCRAPIWrapper(your_ocr_api)

# 启动自适应调度器
adaptive_inference.start(wrapped_api, "your_ocr_api")

# 使用自适应调度器运行OCR
result = adaptive_inference.run_ocr(image_data)
```

## 注意事项

1. **依赖要求**：
   - Python 3.7+
   - psutil（用于系统监控）
   - pynvml（用于NVIDIA GPU监控，可选）

2. **GPU支持**：
   - 目前支持NVIDIA GPU（通过pynvml）
   - AMD GPU支持需要额外配置

3. **性能调优**：
   - 根据实际硬件配置调整线程数和进程数
   - 监控系统负载，避免资源耗尽
   - 调整批处理大小以优化性能

4. **错误处理**：
   - 所有方法都会抛出异常，建议使用try-catch处理
   - 调度器会自动记录错误日志
   - 定期检查GPU和CPU状态

## 故障排除

### 常见问题

1. **GPU检测失败**
   - 确保已安装GPU驱动
   - 确保已安装pynvml库
   - 检查GPU是否被其他进程占用

2. **切换不及时**
   - 调整阈值持续时间配置
   - 检查监控间隔设置
   - 确保系统负载正常

3. **CPU性能不足**
   - 增加线程数或进程数
   - 调整批处理大小
   - 关闭不必要的后台进程

4. **配置不生效**
   - 确保配置文件格式正确
   - 检查配置项名称是否正确
   - 尝试动态更新配置

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至开发者邮箱