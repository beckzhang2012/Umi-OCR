#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据管理器功能测试脚本
仅测试review_data_manager模块的核心功能
"""

import sys
import os
import json

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from review_data_manager import ReviewDataManager

def test_basic_operations():
    """测试基本CRUD操作"""
    print("=== 测试基本CRUD操作 ===")
    
    # 创建临时数据目录
    test_dir = os.path.join(os.path.dirname(__file__), "test_review_data")
    
    try:
        # 初始化数据管理器
        manager = ReviewDataManager(test_dir)
        
        # 1. 测试清空记录
        manager.clear_all()
        assert manager.get_record_count() == 0, "清空记录失败"
        print("✓ 清空记录功能正常")
        
        # 2. 测试添加记录
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
        
        assert manager.get_record_count() == 2, "添加记录失败"
        print("✓ 添加记录功能正常")
        
        # 3. 测试获取记录
        records = manager.get_records()
        assert len(records) == 2, "获取记录失败"
        assert records[0]["id"] == record_id2, "记录顺序不正确（最新记录应在前面）"
        print("✓ 获取记录功能正常")
        
        # 4. 测试按ID获取记录
        record = manager.get_record(record_id1)
        assert record is not None, "按ID获取记录失败"
        assert record["source_path"] == "test/image1.jpg", "记录内容不正确"
        print("✓ 按ID获取记录功能正常")
        
        # 5. 测试更新记录状态
        success = manager.update_record_status(record_id1, "已校对")
        assert success, "更新状态失败"
        record = manager.get_record(record_id1)
        assert record["status"] == "已校对", "状态更新不正确"
        print("✓ 更新记录状态功能正常")
        
        # 6. 测试更新负责人
        success = manager.update_record_assignee(record_id1, "张三")
        assert success, "更新负责人失败"
        record = manager.get_record(record_id1)
        assert record["assignee"] == "张三", "负责人更新不正确"
        print("✓ 更新负责人功能正常")
        
        # 7. 测试更新标签
        success = manager.update_record_tags(record_id1, "测试,重要,紧急")
        assert success, "更新标签失败"
        record = manager.get_record(record_id1)
        assert "测试" in record["tags"] and "重要" in record["tags"] and "紧急" in record["tags"], "标签更新不正确"
        print("✓ 更新标签功能正常")
        
        # 8. 测试更新备注
        success = manager.update_record_note(record_id1, "这是一个重要的测试记录")
        assert success, "更新备注失败"
        record = manager.get_record(record_id1)
        assert record["note"] == "这是一个重要的测试记录", "备注更新不正确"
        print("✓ 更新备注功能正常")
        
        # 9. 测试删除记录
        success = manager.delete_record(record_id1)
        assert success, "删除记录失败"
        assert manager.get_record_count() == 1, "删除后记录数不正确"
        assert manager.get_record(record_id1) is None, "删除后记录仍存在"
        print("✓ 删除记录功能正常")
        
        print("\n=== 基本CRUD操作测试通过 ===")
        return True
        
    except Exception as e:
        print(f"\n✗ 基本CRUD操作测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试数据
        if os.path.exists(test_dir):
            import shutil
            shutil.rmtree(test_dir)

def test_batch_operations():
    """测试批量操作"""
    print("\n=== 测试批量操作 ===")
    
    test_dir = os.path.join(os.path.dirname(__file__), "test_review_data_batch")
    
    try:
        manager = ReviewDataManager(test_dir)
        manager.clear_all()
        
        # 添加多条测试记录
        record_ids = []
        for i in range(5):
            record_id = manager.add_record(
                source_path=f"test/image{i}.jpg",
                text_summary=f"测试摘要{i}",
                confidence=0.9 - i * 0.05,
                full_text=f"完整文本{i}"
            )
            record_ids.append(record_id)
        
        assert manager.get_record_count() == 5, "添加测试记录失败"
        
        # 1. 测试批量更新状态
        success = manager.batch_update_status(record_ids[:3], "已完成")
        assert success, "批量更新状态失败"
        
        completed_count = len(manager.get_records_by_status("已完成"))
        assert completed_count == 3, "批量更新状态结果不正确"
        print("✓ 批量更新状态功能正常")
        
        # 2. 测试批量删除
        success = manager.batch_delete(record_ids[:2])
        assert success, "批量删除失败"
        assert manager.get_record_count() == 3, "批量删除后记录数不正确"
        print("✓ 批量删除功能正常")
        
        print("\n=== 批量操作测试通过 ===")
        return True
        
    except Exception as e:
        print(f"\n✗ 批量操作测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            import shutil
            shutil.rmtree(test_dir)

def test_search_and_filter():
    """测试搜索和筛选功能"""
    print("\n=== 测试搜索和筛选功能 ===")
    
    test_dir = os.path.join(os.path.dirname(__file__), "test_review_data_search")
    
    try:
        manager = ReviewDataManager(test_dir)
        manager.clear_all()
        
        # 添加测试记录
        manager.add_record(
            source_path="test/image1.jpg",
            text_summary="这是中文测试文本",
            confidence=0.95,
            full_text="完整的中文测试内容"
        )
        
        manager.add_record(
            source_path="test/image2.jpg",
            text_summary="This is English test",
            confidence=0.90,
            full_text="Complete English test content"
        )
        
        manager.add_record(
            source_path="docs/report.pdf",
            text_summary="这是文档摘要",
            confidence=0.85,
            full_text="完整的文档内容"
        )
        
        # 1. 测试按状态筛选
        unprocessed = manager.get_records_by_status("未处理")
        assert len(unprocessed) == 3, "按状态筛选失败"
        print("✓ 按状态筛选功能正常")
        
        # 2. 测试文本搜索
        results = manager.search_records("中文")
        assert len(results) == 1, "中文搜索失败"
        
        results = manager.search_records("English")
        assert len(results) == 1, "英文搜索失败"
        
        results = manager.search_records("test")
        assert len(results) == 2, "test搜索失败"
        
        results = manager.search_records("文档")
        assert len(results) == 1, "文档搜索失败"
        
        print("✓ 文本搜索功能正常")
        
        print("\n=== 搜索和筛选测试通过 ===")
        return True
        
    except Exception as e:
        print(f"\n✗ 搜索和筛选测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            import shutil
            shutil.rmtree(test_dir)

def test_export_functions():
    """测试导出功能"""
    print("\n=== 测试导出功能 ===")
    
    test_dir = os.path.join(os.path.dirname(__file__), "test_review_data_export")
    
    try:
        manager = ReviewDataManager(test_dir)
        manager.clear_all()
        
        # 添加测试记录
        record_id = manager.add_record(
            source_path="test/image.jpg",
            text_summary="这是测试文本摘要",
            confidence=0.95,
            full_text="这是完整的识别文本内容\n包含多行文本\n第三行文本"
        )
        
        # 更新记录信息以测试完整导出
        manager.update_record_status(record_id, "已校对")
        manager.update_record_assignee(record_id, "张三")
        manager.update_record_tags(record_id, "测试,重要")
        manager.update_record_note(record_id, "这是一个测试备注")
        
        # 1. 测试Markdown导出
        md_content = manager.export_records([record_id], "markdown")
        assert len(md_content) > 0, "Markdown导出内容为空"
        assert "# OCR审阅报告" in md_content, "Markdown格式不正确"
        assert "测试文本摘要" in md_content, "Markdown内容不正确"
        assert "张三" in md_content, "负责人信息未导出"
        assert "测试" in md_content and "重要" in md_content, "标签信息未导出"
        print("✓ Markdown导出功能正常")
        
        # 2. 测试HTML导出
        html_content = manager.export_records([record_id], "html")
        assert len(html_content) > 0, "HTML导出内容为空"
        assert "<html" in html_content.lower(), "HTML格式不正确"
        assert "测试文本摘要" in html_content, "HTML内容不正确"
        assert "张三" in html_content, "负责人信息未导出"
        print("✓ HTML导出功能正常")
        
        # 3. 测试批量导出
        record_id2 = manager.add_record(
            source_path="test/image2.jpg",
            text_summary="第二个测试摘要",
            confidence=0.88
        )
        
        md_content = manager.export_records([record_id, record_id2], "markdown")
        assert md_content.count("## 记录") == 2, "批量导出记录数不正确"
        print("✓ 批量导出功能正常")
        
        print("\n=== 导出功能测试通过 ===")
        return True
        
    except Exception as e:
        print(f"\n✗ 导出功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            import shutil
            shutil.rmtree(test_dir)

def main():
    """主测试函数"""
    print("=== 数据管理器功能测试 ===")
    
    tests = [
        test_basic_operations,
        test_batch_operations,
        test_search_and_filter,
        test_export_functions
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    if all_passed:
        print("\n" + "="*50)
        print("🎉 所有测试通过！数据管理器功能正常。")
        print("="*50)
        return True
    else:
        print("\n" + "="*50)
        print("❌ 部分测试失败，请检查代码。")
        print("="*50)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)