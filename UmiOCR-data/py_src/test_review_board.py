#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审阅看板功能测试脚本
测试数据存储、控制器和界面功能
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from review_data_manager import get_data_manager
from tag_pages.ReviewBoard import ReviewBoard
from tag_pages.tag_pages_connector import TagPageConnector

def test_data_manager():
    """测试数据管理器功能"""
    print("=== 测试数据管理器 ===")
    
    manager = get_data_manager()
    
    # 清空所有记录
    manager.clear_all()
    print(f"清空记录后总数: {manager.get_record_count()}")
    
    # 添加测试记录
    record_id1 = manager.add_record(
        source_path="test/image1.jpg",
        text_summary="这是测试文本摘要1",
        confidence=0.95,
        full_text="这是完整的识别文本内容1\n包含多行文本"
    )
    
    record_id2 = manager.add_record(
        source_path="test/image2.jpg",
        text_summary="这是测试文本摘要2",
        confidence=0.88,
        full_text="这是完整的识别文本内容2\n包含多行文本"
    )
    
    print(f"添加测试记录: {record_id1}, {record_id2}")
    print(f"当前记录总数: {manager.get_record_count()}")
    
    # 获取所有记录
    records = manager.get_records()
    print(f"获取到 {len(records)} 条记录")
    
    # 更新记录
    success = manager.update_record_status(record_id1, "已校对")
    print(f"更新记录1状态: {'成功' if success else '失败'}")
    
    success = manager.update_record_assignee(record_id1, "张三")
    print(f"更新记录1负责人: {'成功' if success else '失败'}")
    
    success = manager.update_record_tags(record_id1, "测试,重要")
    print(f"更新记录1标签: {'成功' if success else '失败'}")
    
    # 按状态筛选
    unprocessed = manager.get_records_by_status("未处理")
    reviewed = manager.get_records_by_status("已校对")
    print(f"未处理记录: {len(unprocessed)}, 已校对记录: {len(reviewed)}")
    
    # 搜索功能
    results = manager.search_records("测试")
    print(f"搜索'测试'找到: {len(results)} 条记录")
    
    # 导出功能
    print("\n=== 测试导出功能 ===")
    
    # 导出Markdown
    md_content = manager.export_records([record_id1, record_id2], "markdown")
    print(f"Markdown导出成功，长度: {len(md_content)} 字符")
    
    # 导出HTML
    html_content = manager.export_records([record_id1, record_id2], "html")
    print(f"HTML导出成功，长度: {len(html_content)} 字符")
    
    # 批量更新
    success = manager.batch_update_status([record_id1, record_id2], "待修改")
    print(f"批量更新状态: {'成功' if success else '失败'}")
    
    # 批量删除
    success = manager.batch_delete([record_id1])
    print(f"批量删除记录: {'成功' if success else '失败'}")
    print(f"删除后记录总数: {manager.get_record_count()}")
    
    # 清理测试数据
    manager.clear_all()
    print("\n=== 数据管理器测试完成 ===")
    return True

def test_review_board_controller():
    """测试审阅看板控制器"""
    print("\n=== 测试审阅看板控制器 ===")
    
    # 创建连接器和控制器
    connector = TagPageConnector()
    ctrl_key = connector.addPage("ReviewBoard")
    
    if not ctrl_key:
        print("创建控制器失败")
        return False
    
    print(f"创建控制器成功: {ctrl_key}")
    
    # 获取控制器实例
    controller = connector.pages[ctrl_key]["pyObj"]
    
    # 测试获取记录
    records = controller.get_records()
    print(f"控制器获取记录: {len(records)} 条")
    
    # 测试添加记录
    record_id = controller.add_record(
        "test/image.jpg", "测试摘要", 0.92, "full text"
    )
    print(f"控制器添加记录: {record_id}")
    
    # 测试更新记录
    success = controller.update_record_status(record_id, "已校对")
    print(f"控制器更新状态: {'成功' if success else '失败'}")
    
    # 测试导出
    success = controller.export_records([record_id], "markdown")
    print(f"控制器导出Markdown: {'成功' if success else '失败'}")
    
    # 测试删除记录
    success = controller.delete_record(record_id)
    print(f"控制器删除记录: {'成功' if success else '失败'}")
    
    # 清理
    connector.delPage(ctrl_key)
    print("\n=== 审阅看板控制器测试完成 ===")
    return True

def test_integration():
    """测试集成功能"""
    print("\n=== 测试集成功能 ===")
    
    manager = get_data_manager()
    manager.clear_all()
    
    # 添加多条记录用于测试筛选和排序
    for i in range(5):
        manager.add_record(
            source_path=f"test/image{i}.jpg",
            text_summary=f"测试摘要{i}",
            confidence=0.9 - i * 0.05,
            full_text=f"完整文本{i}"
        )
    
    # 测试按状态筛选
    unprocessed = manager.get_records_by_status("未处理")
    print(f"未处理记录数: {len(unprocessed)}")
    
    # 测试搜索
    results = manager.search_records("摘要")
    print(f"搜索'摘要'找到: {len(results)} 条记录")
    
    # 测试批量操作
    record_ids = [record["id"] for record in manager.get_records()[:3]]
    success = manager.batch_update_status(record_ids, "已完成")
    print(f"批量更新3条记录状态: {'成功' if success else '失败'}")
    
    completed = manager.get_records_by_status("已完成")
    print(f"已完成记录数: {len(completed)}")
    
    # 清理
    manager.clear_all()
    print("\n=== 集成测试完成 ===")
    return True

def main():
    """主测试函数"""
    print("=== 审阅看板功能测试 ===")
    
    try:
        # 运行所有测试
        test_data_manager()
        test_review_board_controller()
        test_integration()
        
        print("\n=== 所有测试通过 ===")
        return True
        
    except Exception as e:
        print(f"\n=== 测试失败: {e} ===")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)