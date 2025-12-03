# ===============================================
# =============== 多引擎OCR结果对比器 ===============
# ===============================================

"""
多引擎OCR结果对比器，用于分析和展示不同OCR引擎之间的识别差异。
"""

import difflib
import json
from collections import defaultdict
from umi_log import logger


class TextBlock:
    """文本块数据结构"""
    def __init__(self, text, score=0.0, box=None, engine_key=None):
        self.text = text.strip()
        self.score = score
        self.box = box or [0, 0, 0, 0]
        self.engine_key = engine_key
        self.position = self._calculate_position()

    def _calculate_position(self):
        """计算文本块的位置坐标"""
        if self.box:
            # 使用文本块的中心坐标作为位置
            x1, y1, x2, y2 = self.box
            return ((x1 + x2) / 2, (y1 + y2) / 2)
        return (0, 0)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "text": self.text,
            "score": self.score,
            "box": self.box,
            "engine_key": self.engine_key,
            "position": self.position
        }


class MultiOCRComparator:
    """多引擎OCR结果对比器"""
    def __init__(self):
        self.similarity_threshold = 0.8  # 文本相似度阈值
        self.position_threshold = 50     # 位置相似度阈值（像素）

    def set_thresholds(self, similarity_threshold=0.8, position_threshold=50):
        """设置相似度阈值"""
        self.similarity_threshold = similarity_threshold
        self.position_threshold = position_threshold

    def compare_results(self, multi_engine_results):
        """对比多个引擎的识别结果
        multi_engine_results: {engine_key: result_dict}
        """
        if not multi_engine_results or len(multi_engine_results) < 2:
            return {
                "success": False,
                "message": "至少需要两个引擎的结果才能进行对比",
                "data": None
            }

        try:
            # 提取所有文本块
            all_blocks = self._extract_all_blocks(multi_engine_results)
            
            # 按位置聚类文本块
            clusters = self._cluster_blocks_by_position(all_blocks)
            
            # 分析每个聚类的差异
            comparison_result = self._analyze_cluster_differences(clusters)
            
            # 生成统计信息
            statistics = self._generate_statistics(multi_engine_results, comparison_result)
            
            return {
                "success": True,
                "message": "对比完成",
                "data": {
                    "clusters": comparison_result,
                    "statistics": statistics,
                    "engines": list(multi_engine_results.keys())
                }
            }
        
        except Exception as e:
            logger.error("多引擎OCR对比失败", exc_info=True)
            return {
                "success": False,
                "message": f"对比失败: {str(e)}",
                "data": None
            }

    def _extract_all_blocks(self, multi_engine_results):
        """提取所有引擎的文本块"""
        all_blocks = []
        
        for engine_key, result in multi_engine_results.items():
            if result.get('code') == 100 and result.get('data'):
                for block in result['data']:
                    text_block = TextBlock(
                        text=block.get('text', ''),
                        score=block.get('score', 0.0),
                        box=block.get('box', []),
                        engine_key=engine_key
                    )
                    if text_block.text:
                        all_blocks.append(text_block)
        
        return all_blocks

    def _cluster_blocks_by_position(self, all_blocks):
        """按位置聚类文本块"""
        clusters = []
        
        for block in all_blocks:
            # 尝试将文本块加入现有聚类
            added = False
            for cluster in clusters:
                # 计算与聚类中心的距离
                cluster_center = cluster['center']
                distance = self._calculate_distance(block.position, cluster_center)
                
                if distance <= self.position_threshold:
                    cluster['blocks'].append(block)
                    # 更新聚类中心
                    cluster['center'] = self._calculate_new_center(cluster['blocks'])
                    added = True
                    break
            
            # 如果没有加入任何聚类，则创建新聚类
            if not added:
                clusters.append({
                    'center': block.position,
                    'blocks': [block]
                })
        
        return clusters

    def _calculate_distance(self, pos1, pos2):
        """计算两个位置之间的距离"""
        x1, y1 = pos1
        x2, y2 = pos2
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5

    def _calculate_new_center(self, blocks):
        """计算聚类的新中心"""
        if not blocks:
            return (0, 0)
        
        total_x = sum(block.position[0] for block in blocks)
        total_y = sum(block.position[1] for block in blocks)
        
        return (total_x / len(blocks), total_y / len(blocks))

    def _analyze_cluster_differences(self, clusters):
        """分析每个聚类的差异"""
        comparison_result = []
        
        for i, cluster in enumerate(clusters):
            blocks = cluster['blocks']
            
            # 按引擎分组文本块
            blocks_by_engine = defaultdict(list)
            for block in blocks:
                blocks_by_engine[block.engine_key].append(block)
            
            # 获取所有唯一文本
            unique_texts = self._get_unique_texts(blocks)
            
            # 分析差异类型
            difference_type = self._determine_difference_type(unique_texts, blocks_by_engine)
            
            # 计算文本相似度
            similarity_matrix = self._calculate_similarity_matrix(unique_texts)
            
            # 选择参考文本（置信度最高或出现频率最高）
            reference_text = self._select_reference_text(blocks)
            
            cluster_result = {
                "cluster_id": i,
                "center": cluster['center'],
                "blocks": [block.to_dict() for block in blocks],
                "blocks_by_engine": {k: [b.to_dict() for b in v] for k, v in blocks_by_engine.items()},
                "unique_texts": unique_texts,
                "difference_type": difference_type,
                "similarity_matrix": similarity_matrix,
                "reference_text": reference_text,
                "has_difference": len(unique_texts) > 1
            }
            
            comparison_result.append(cluster_result)
        
        return comparison_result

    def _get_unique_texts(self, blocks):
        """获取唯一文本列表"""
        texts = set()
        for block in blocks:
            texts.add(block.text)
        return sorted(list(texts), key=lambda x: (-len(x), x))

    def _determine_difference_type(self, unique_texts, blocks_by_engine):
        """确定差异类型"""
        if len(unique_texts) == 1:
            return "一致"
        
        # 检查是否有引擎未识别到该区域
        if len(blocks_by_engine) < len(self._get_all_engines(blocks_by_engine)):
            return "部分引擎未识别"
        
        # 检查文本差异程度
        similarity = self._calculate_average_similarity(unique_texts)
        if similarity > 0.9:
            return "轻微差异"
        elif similarity > 0.7:
            return "中等差异"
        else:
            return "显著差异"

    def _calculate_similarity_matrix(self, texts):
        """计算文本相似度矩阵"""
        matrix = []
        for i in range(len(texts)):
            row = []
            for j in range(len(texts)):
                if i == j:
                    row.append(1.0)
                else:
                    similarity = difflib.SequenceMatcher(None, texts[i], texts[j]).ratio()
                    row.append(similarity)
            matrix.append(row)
        return matrix

    def _calculate_average_similarity(self, texts):
        """计算平均相似度"""
        if len(texts) < 2:
            return 1.0
        
        total_similarity = 0
        count = 0
        
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                similarity = difflib.SequenceMatcher(None, texts[i], texts[j]).ratio()
                total_similarity += similarity
                count += 1
        
        return total_similarity / count if count > 0 else 1.0

    def _select_reference_text(self, blocks):
        """选择参考文本"""
        if not blocks:
            return ""
        
        # 按置信度排序，选择置信度最高的文本
        sorted_blocks = sorted(blocks, key=lambda x: (-x.score, -len(x.text)))
        return sorted_blocks[0].text

    def _get_all_engines(self, blocks_by_engine):
        """获取所有引擎列表"""
        return list(blocks_by_engine.keys())

    def _generate_statistics(self, multi_engine_results, comparison_result):
        """生成统计信息"""
        engines = list(multi_engine_results.keys())
        total_clusters = len(comparison_result)
        
        # 计算有差异的聚类数量
        clusters_with_differences = sum(1 for cluster in comparison_result if cluster['has_difference'])
        
        # 计算每个引擎的平均置信度
        engine_confidences = {}
        for engine_key, result in multi_engine_results.items():
            if result.get('code') == 100 and result.get('score') is not None:
                engine_confidences[engine_key] = result['score']
        
        # 计算处理时间
        engine_times = {}
        for engine_key, result in multi_engine_results.items():
            engine_times[engine_key] = result.get('time', 0)
        
        # 计算每个引擎识别的文本块数量
        block_counts = {}
        for engine_key in engines:
            count = 0
            for cluster in comparison_result:
                if engine_key in cluster['blocks_by_engine']:
                    count += len(cluster['blocks_by_engine'][engine_key])
            block_counts[engine_key] = count
        
        return {
            "total_engines": len(engines),
            "total_clusters": total_clusters,
            "clusters_with_differences": clusters_with_differences,
            "difference_rate": clusters_with_differences / total_clusters if total_clusters > 0 else 0,
            "engine_confidences": engine_confidences,
            "engine_times": engine_times,
            "block_counts": block_counts
        }

    def generate_diff_report(self, comparison_result, format="json"):
        """生成差异报告"""
        if format == "json":
            return json.dumps(comparison_result, ensure_ascii=False, indent=2)
        elif format == "text":
            return self._generate_text_report(comparison_result)
        elif format == "html":
            return self._generate_html_report(comparison_result)
        else:
            return f"不支持的报告格式: {format}"

    def _generate_text_report(self, comparison_result):
        """生成文本格式的差异报告"""
        report = []
        report.append("多引擎OCR识别结果对比报告")
        report.append("=" * 50)
        report.append("")
        
        for i, cluster in enumerate(comparison_result):
            report.append(f"聚类 {i + 1}:")
            report.append(f"  中心位置: ({cluster['center'][0]:.1f}, {cluster['center'][1]:.1f})")
            report.append(f"  差异类型: {cluster['difference_type']}")
            report.append(f"  参考文本: {cluster['reference_text']}")
            report.append(f"  识别结果:")
            
            for engine_key, blocks in cluster['blocks_by_engine'].items():
                if blocks:
                    text = blocks[0]['text']
                    score = blocks[0]['score']
                    report.append(f"    {engine_key}: {text} (置信度: {score:.2f})")
                else:
                    report.append(f"    {engine_key}: [未识别]")
            
            if cluster['has_difference']:
                report.append(f"  差异详情:")
                for text in cluster['unique_texts']:
                    report.append(f"    - {text}")
            
            report.append("")
        
        return "\n".join(report)

    def _generate_html_report(self, comparison_result):
        """生成HTML格式的差异报告"""
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html lang=\"zh-CN\">")
        html.append("<head>")
        html.append("<meta charset=\"UTF-8\">")
        html.append("<title>多引擎OCR识别结果对比报告</title>")
        html.append("<style>")
        html.append("body { font-family: Arial, sans-serif; margin: 20px; }")
        html.append(".cluster { border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 15px 0; }")
        html.append(".cluster-header { font-weight: bold; font-size: 18px; margin-bottom: 10px; color: #333; }")
        html.append(".cluster-info { margin-bottom: 10px; color: #666; }")
        html.append(".engine-result { margin: 8px 0; padding: 8px; border-left: 3px solid #4CAF50; background-color: #f9f9f9; }")
        html.append(".engine-name { font-weight: bold; color: #4CAF50; }")
        html.append(".text-diff { background-color: #fff3cd; padding: 5px; border-radius: 3px; }")
        html.append(".confidence { color: #007bff; font-size: 12px; }")
        html.append(".difference { color: #dc3545; font-weight: bold; }")
        html.append("</style>")
        html.append("</head>")
        html.append("<body>")
        html.append("<h1>多引擎OCR识别结果对比报告</h1>")
        
        for i, cluster in enumerate(comparison_result):
            html.append(f"<div class=\"cluster\">")
            html.append(f"<div class=\"cluster-header\">聚类 {i + 1}</div>")
            html.append(f"<div class=\"cluster-info\">")
            html.append(f"中心位置: ({cluster['center'][0]:.1f}, {cluster['center'][1]:.1f}) | ")
            html.append(f"差异类型: <span class=\"{'difference' if cluster['has_difference'] else ''}\">{cluster['difference_type']}</span> | ")
            html.append(f"参考文本: {cluster['reference_text']}")
            html.append("</div>")
            html.append("<div>")
            
            for engine_key, blocks in cluster['blocks_by_engine'].items():
                if blocks:
                    text = blocks[0]['text']
                    score = blocks[0]['score']
                    is_diff = text != cluster['reference_text']
                    html.append(f"<div class=\"engine-result\">")
                    html.append(f"<span class=\"engine-name\">{engine_key}</span>: ")
                    html.append(f"<span class=\"{'text-diff' if is_diff else ''}\">{text}</span>")
                    html.append(f" <span class=\"confidence\">(置信度: {score:.2f})</span>")
                    html.append("</div>")
                else:
                    html.append(f"<div class=\"engine-result\">")
                    html.append(f"<span class=\"engine-name\">{engine_key}</span>: [未识别]")
                    html.append("</div>")
            
            html.append("</div>")
            html.append("</div>")
        
        html.append("</body>")
        html.append("</html>")
        
        return "\n".join(html)


# 全局多引擎OCR对比器
MultiOCRComparatorInstance = MultiOCRComparator()
