"""
消息队列模块 - Kafka集成（可选）
使用代理模式，如果Kafka不可用则使用本地队列
"""
from typing import Dict, Any, Optional
from datetime import datetime
from django.conf import settings
from .interfaces import MusicScannerInterface


class MessageQueueInterface:
    """消息队列接口"""
    
    def send_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """发送消息"""
        pass
    
    def consume_messages(self, topic: str, callback) -> None:
        """消费消息"""
        pass


class KafkaMessageQueue(MessageQueueInterface):
    """Kafka消息队列实现"""
    
    def __init__(self):
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self._producer = None
        self._consumer = None
    
    def _get_producer(self):
        """获取生产者（延迟初始化）"""
        if self._producer is None and settings.KAFKA_ENABLED:
            try:
                from kafka import KafkaProducer
                import json
                self._producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
            except Exception as e:
                print(f"Kafka producer initialization failed: {e}")
        return self._producer
    
    def send_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """发送消息到Kafka"""
        producer = self._get_producer()
        if producer:
            try:
                producer.send(topic, message)
                producer.flush()
                return True
            except Exception as e:
                print(f"Failed to send message to Kafka: {e}")
                return False
        return False
    
    def consume_messages(self, topic: str, callback) -> None:
        """从Kafka消费消息"""
        if not settings.KAFKA_ENABLED:
            return
        
        try:
            from kafka import KafkaConsumer
            import json
            
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
            
            for message in consumer:
                callback(message.value)
        except Exception as e:
            print(f"Kafka consumer error: {e}")


class LocalMessageQueue(MessageQueueInterface):
    """本地消息队列实现（当Kafka不可用时使用）"""
    
    def __init__(self):
        self._queue: Dict[str, list] = {}
    
    def send_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """发送消息到本地队列"""
        if topic not in self._queue:
            self._queue[topic] = []
        self._queue[topic].append(message)
        return True
    
    def consume_messages(self, topic: str, callback) -> None:
        """从本地队列消费消息"""
        if topic in self._queue:
            for message in self._queue[topic]:
                callback(message)
            self._queue[topic].clear()


class MessageQueueProxy:
    """消息队列代理 - 根据配置选择Kafka或本地队列"""
    
    def __init__(self):
        if settings.KAFKA_ENABLED:
            try:
                self._queue = KafkaMessageQueue()
            except Exception:
                self._queue = LocalMessageQueue()
        else:
            self._queue = LocalMessageQueue()
    
    def send_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """发送消息"""
        return self._queue.send_message(topic, message)
    
    def consume_messages(self, topic: str, callback) -> None:
        """消费消息"""
        self._queue.consume_messages(topic, callback)
    
    def send_scan_task(self, directory_path: str) -> bool:
        """发送扫描任务消息"""
        return self.send_message('scan_tasks', {
            'action': 'scan_directory',
            'directory_path': directory_path,
            'timestamp': datetime.now().isoformat()
        })


# 全局消息队列实例
message_queue = MessageQueueProxy()

