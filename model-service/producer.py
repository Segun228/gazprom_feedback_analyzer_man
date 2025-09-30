from kafka import KafkaProducer
import json
import logging
import uuid
import json
import logging
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable

load_dotenv()

KAFKA_BROKER_DOCKER = os.getenv("KAFKA_BROKER_DOCKER")
KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
PRODUCER_CLIENT_ID = os.getenv("PRODUCER_CLIENT_ID")




def ensure_topic_exists():
    for i in range(10):
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=KAFKA_BROKER_DOCKER,
                client_id="admin_client"
            )

            topic_list = [NewTopic(
                name=KAFKA_TOPIC,
                num_partitions=1,
                replication_factor=1
            )]

            admin_client.create_topics(new_topics=topic_list, validate_only=False)
            logging.info(f"Kafka topic '{KAFKA_TOPIC}' created")
            admin_client.close()
            return

        except TopicAlreadyExistsError:
            logging.info(f"Kafka topic '{KAFKA_TOPIC}' already exists")
            admin_client.close()
            return

        except NoBrokersAvailable:
            logging.warning(f"[{i+1}/10] Kafka broker not available, retrying in 3s...")
            time.sleep(3)

        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(3)

_producer = None

def get_producer():
    global _producer
    if _producer is None:
        try:
            _producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER_DOCKER,
                client_id=PRODUCER_CLIENT_ID,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
        except Exception as e:
            logging.warning(f"Kafka producer not available: {e}")
            _producer = None
    return _producer



def build_message(
    text,
    date,
    sentiment,
    tags,
):
    message = {
        "text": text,
        "date": date,
        "sentiment": sentiment,
        "tags": tags,
    }

    return message


def build_message_batch(
    messages
):
    try:
        result = {
            "batch":[]
        }
        for message in messages:
            result["batch"].append(build_message(
                text = message.get("text", "The text is missing"),
                date = message.get("date", "The date is missing"),
                sentiment = message.get("sentiment", "The sentiment is missing"),
                tags = message.get("tags", ["The tags are missing"]),
            ))
        return send_to_kafka(result)
    except Exception as e:
        logging.error("Error while sending the batch")
        logging.error(e)


def serialize_bytes(obj):
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def send_to_kafka(data):
    producer = get_producer()
    if producer is None:
        logging.info(f"Kafka not available, skipping log: {data}")
        return {"status": "skipped", "messages_sent": 0}

    try:
        messages = []

        if isinstance(data, list):
            for el in data:
                if hasattr(el, "dict"):
                    el = el.dict()
                serialized = json.dumps(el, default=serialize_bytes).encode("utf-8")
                messages.append(el)
                producer.send(KAFKA_TOPIC, value=serialized)
        else:
            if hasattr(data, "dict"):
                data = data.dict()
            serialized = json.dumps(data, default=serialize_bytes).encode("utf-8")
            messages.append(data)
            producer.send(KAFKA_TOPIC, value=serialized)

        producer.flush()
        return {
            "status": "ok",
            "code": 200,
            "messages_sent": len(messages),
            "sample": messages[0] if messages else None,
        }

    except Exception as e:
        logging.exception(f"[Kafka] Ошибка отправки: {e}")
        return {"status": "failed", "error": str(e)}