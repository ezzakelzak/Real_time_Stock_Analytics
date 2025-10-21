#Import requirements
import json
import boto3
import time
from kafka import KafkaConsumer
import os
from dotenv import load_dotenv

load_dotenv()

#Minio Connection
minio = boto3.client(
    "minio",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY
)

bucket_name = "bronze-transactions"

# Ensure bucket exists (idempotent)
try:
    minio.head_bucket(Bucket=bucket_name)
    print(f"Bucket {bucket_name} already exists.")
except Exception:
    minio.create_bucket(Bucket=bucket_name)
    print(f"Created bucket {bucket_name}.")

#Define Consumer
consumer = KafkaConsumer(
    "stock-quotes",
    bootstrap_servers=["host.docker.internal:29092"],
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="bronze-consumer1",
    value_deserializer=lambda v: json.loads(v.decode("utf-8"))
)

print("Consumerstreaming and saving to MinIO...")

#Main Function
for message in consumer:
    record = message.value
    symbol = record.get("symbol", "unknown")
    ts = record.get("fetched_at",int(time.time()))
    key = f"{symbol}/{ts}.json"

    minio.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(record),
        ContentType="application/json"
    )
    print(f"Saved record for {symbol} = minio://{bucket_name}/{key}")
                    