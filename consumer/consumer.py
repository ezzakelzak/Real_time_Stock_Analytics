import json
import time
import boto3
from kafka import KafkaConsumer
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET")

KAFKA_BOOTSTRAP_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVER")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")

# Connect to MinIO
minio = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY
)

# Create Kafka consumer
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=[KAFKA_BOOTSTRAP_SERVER],
    auto_offset_reset="latest",
    enable_auto_commit=True,
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)

print(f"Listening for messages on topic: {KAFKA_TOPIC}")

for message in consumer:
    data = message.value
    print(f"Received: {data}")

    file_name = f"{int(time.time())}.json"
    minio.put_object(
        Bucket=MINIO_BUCKET,
        Key=file_name,
        Body=json.dumps(data).encode("utf-8"),
    )

    print(f"Saved {file_name} to {MINIO_BUCKET}")