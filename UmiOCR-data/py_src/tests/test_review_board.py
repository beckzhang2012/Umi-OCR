import os
import sys
import tempfile
import unittest

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from tag_pages.ReviewBoard import ReviewBoard

class TestReviewBoard(unittest.TestCase):
    def setUp(self):
        """在每个测试方法前执行"""
        # 创建临时目录用于存储测试数据
        self.temp_dir = tempfile.TemporaryDirectory()
        # 创建ReviewBoard实例，指定临时数据文件
        self.board = ReviewBoard()
        # 重写数据文件路径到临时目录
        self.board.data_file = os.path.join(self.temp_dir.name, "review_board.json")
        # 清空记录
        self.board.records = []
        self.board._save_records()
    
    def tearDown(self):
        """在每个测试方法后执行"""
        # 关闭临时目录
        self.temp_dir.cleanup()
    
    def test_add_record(self):
        """测试添加记录"""
        print("测试添加记录...")
        record = {
            "source": "test.jpg",
            "text": "测试文本",
            "confidence": 0.95
        }
        record_id = self.board.addRecord(record)
        self.assertIsNotNone(record_id)
        self.assertEqual(len(self.board.records), 1)
        self.assertEqual(self.board.records[0]["id"], record_id)
        self.assertEqual(self.board.records[0]["source"], "test.jpg")
        self.assertEqual(self.board.records[0]["status"], "未处理")
        print("测试添加记录通过")
    
    def test_get_records(self):
        """测试获取记录"""
        print("测试获取记录...")
        # 添加测试记录
        self.board.addRecord({"source": "test1.jpg", "text": "文本1", "confidence": 0.9})
        self.board.addRecord({"source": "test2.jpg", "text": "文本2", "confidence": 0.8})
        self.board.addRecord({"source": "test3.jpg", "text": "文本3", "confidence": 0.7})
        
        # 测试获取所有记录
        records = self.board.getRecords()
        self.assertEqual(len(records), 3)
        
        # 测试按状态筛选
        self.board.updateRecord(records[0]["id"], {"status": "已校对"})
        filtered = self.board.getRecords({"status": "已校对"})
        self.assertEqual(len(filtered), 1)
        
        # 测试搜索
        search_result = self.board.getRecords({"search": "文本2"})
        self.assertEqual(len(search_result), 1)
        self.assertEqual(search_result[0]["source"], "test2.jpg")
        
        # 测试排序
        sorted_by_confidence = self.board.getRecords(sort_by="confidence", sort_order="asc")
        self.assertEqual(sorted_by_confidence[0]["confidence"], 0.7)
        print("测试获取记录通过")
    
    def test_update_record(self):
        """测试更新记录"""
        print("测试更新记录...")
        record_id = self.board.addRecord({"source": "test.jpg", "text": "文本", "confidence": 0.9})
        
        # 更新记录
        success = self.board.updateRecord(record_id, {
            "status": "已完成",
            "assignee": "张三",
            "tags": ["重要"],
            "notes": "这是一条备注"
        })
        self.assertTrue(success)
        
        # 验证更新
        record = next(r for r in self.board.records if r["id"] == record_id)
        self.assertEqual(record["status"], "已完成")
        self.assertEqual(record["assignee"], "张三")
        self.assertEqual(record["tags"], ["重要"])
        self.assertEqual(record["notes"], "这是一条备注")
        print("测试更新记录通过")
    
    def test_batch_update(self):
        """测试批量更新"""
        print("测试批量更新...")
        # 添加测试记录
        record1_id = self.board.addRecord({"source": "test1.jpg", "text": "文本1", "confidence": 0.9})
        record2_id = self.board.addRecord({"source": "test2.jpg", "text": "文本2", "confidence": 0.8})
        
        # 批量更新
        self.board.batchUpdate([record1_id, record2_id], {
            "status": "待修改",
            "assignee": "李四"
        })
        
        # 验证更新
        record1 = next(r for r in self.board.records if r["id"] == record1_id)
        record2 = next(r for r in self.board.records if r["id"] == record2_id)
        self.assertEqual(record1["status"], "待修改")
        self.assertEqual(record1["assignee"], "李四")
        self.assertEqual(record2["status"], "待修改")
        self.assertEqual(record2["assignee"], "李四")
        print("测试批量更新通过")
    
    def test_delete_record(self):
        """测试删除记录"""
        print("测试删除记录...")
        record_id = self.board.addRecord({"source": "test.jpg", "text": "文本", "confidence": 0.9})
        self.assertEqual(len(self.board.records), 1)
        
        # 删除记录
        self.board.deleteRecord(record_id)
        self.assertEqual(len(self.board.records), 0)
        print("测试删除记录通过")
    
    def test_batch_delete(self):
        """测试批量删除"""
        print("测试批量删除...")
        # 添加测试记录
        record1_id = self.board.addRecord({"source": "test1.jpg", "text": "文本1", "confidence": 0.9})
        record2_id = self.board.addRecord({"source": "test2.jpg", "text": "文本2", "confidence": 0.8})
        record3_id = self.board.addRecord({"source": "test3.jpg", "text": "文本3", "confidence": 0.7})
        
        self.assertEqual(len(self.board.records), 3)
        
        # 批量删除
        self.board.batchDelete([record1_id, record3_id])
        self.assertEqual(len(self.board.records), 1)
        self.assertEqual(self.board.records[0]["id"], record2_id)
        print("测试批量删除通过")
    
    def test_export_records(self):
        """测试导出记录"""
        print("测试导出记录...")
        # 添加测试记录
        record1_id = self.board.addRecord({"source": "test1.jpg", "text": "文本1", "confidence": 0.9})
        record2_id = self.board.addRecord({"source": "test2.jpg", "text": "文本2", "confidence": 0.8})
        
        # 测试Markdown导出
        md_export = self.board.exportRecords([record1_id, record2_id], "markdown")
        self.assertIn("# OCR审阅看板报告", md_export)
        self.assertIn("文本1", md_export)
        self.assertIn("文本2", md_export)
        
        # 测试HTML导出
        html_export = self.board.exportRecords([record1_id, record2_id], "html")
        self.assertIn("<html>", html_export)
        self.assertIn("文本1", html_export)
        self.assertIn("文本2", html_export)
        print("测试导出记录通过")

if __name__ == '__main__':
    # 运行所有测试
    unittest.main()