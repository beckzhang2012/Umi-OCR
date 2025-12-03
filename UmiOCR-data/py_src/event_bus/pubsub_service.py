#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Umi-OCR 发布订阅服务模块
"""

import sys
from typing import Dict, List, Callable


class _PubSubServiceClass:
    """发布订阅服务类"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, topic: str, callback: Callable):
        """订阅主题"""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        
        if callback not in self._subscribers[topic]:
            self._subscribers[topic].append(callback)
    
    def unsubscribe(self, topic: str, callback: Callable):
        """取消订阅主题"""
        if topic in self._subscribers:
            if callback in self._subscribers[topic]:
                self._subscribers[topic].remove(callback)
            
            if not self._subscribers[topic]:
                del self._subscribers[topic]
    
    def publish(self, topic: str, *args, **kwargs):
        """发布主题"""
        if topic in self._subscribers:
            for callback in self._subscribers[topic]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"Error in pubsub callback for topic {topic}: {e}")
    
    def get_topics(self) -> List[str]:
        """获取所有主题"""
        return list(self._subscribers.keys())
    
    def get_subscribers(self, topic: str) -> List[Callable]:
        """获取主题的所有订阅者"""
        return self._subscribers.get(topic, [])


# 全局发布订阅服务实例
PubSubService = _PubSubServiceClass()