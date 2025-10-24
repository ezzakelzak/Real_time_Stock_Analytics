import os
import boto3
import snowflake.connector
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- LOAD ENV VARIABLES ---
load_dotenv()

# --- MINIO CONFIG ---
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
BUCKET = os.getenv("MINIO_BUCKET")
LOCAL_DIR = "/tmp/minio_downloads"  

# --- SNOWFLAKE CONFIG ---
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DB = os.getenv("SNOWFLAKE_DB")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")


# --- TASK 1: DOWNLOAD FILES FROM MINIO ---
def download_from_minio():
    os.makedirs(LOCAL_DIR, exist_ok=True)
    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY
    )

    objects = s3.list_objects_v2(Bucket=BUCKET, Prefix="to_load/").get("Contents", [])
    local_files = []

    for obj in objects:
        key = obj["Key"]
        if key.endswith("/"):
            continue

        local_file = os.path.join(LOCAL_DIR, os.path.basename(key))
        s3.download_file(BUCKET, key, local_file)
        print(f"Downloaded {key} -> {local_file}")
        local_files.append({"key": key, "local_path": local_file})

    print(f"Total files downloaded: {len(local_files)}")
    return local_files


# --- TASK 2: LOAD FILES INTO SNOWFLAKE ---
def load_to_snowflake(**kwargs):
    files_info = kwargs["ti"].xcom_pull(task_ids="download_minio")
    if not files_info:
        print("No files to load.")
        return

    conn = snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DB,
        schema=SNOWFLAKE_SCHEMA,
    )
    cur = conn.cursor()

    for f in files_info:
        local_path = f["local_path"]
        cur.execute(f"PUT file://{local_path} @%bronze_stock_quotes_raw")
        print(f"Uploaded {local_path} to Snowflake stage")

    cur.execute("""
        COPY INTO bronze_stock_quotes_raw
        FROM @%bronze_stock_quotes_raw
        FILE_FORMAT = (TYPE=JSON)
    """)
    print("COPY INTO executed")

    cur.close()
    conn.close()


# --- TASK 3: MOVE PROCESSED FILES TO 'loaded/' ---
def move_to_loaded(**kwargs):
    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY
    )

    files_info = kwargs["ti"].xcom_pull(task_ids="download_minio")
    if not files_info:
        print("No files to move.")
        return

    for f in files_info:
        key = f["key"]
        filename = os.path.basename(key)
        parts = key.split("/")
        symbol = parts[1] if len(parts) >= 3 else "unknown"

        src_key = key
        dst_key = f"loaded/{symbol}/{filename}"

        s3.copy_object(Bucket=BUCKET, CopySource=f"{BUCKET}/{src_key}", Key=dst_key)
        s3.delete_object(Bucket=BUCKET, Key=src_key)
        print(f"Moved {src_key} -> {dst_key}")


# --- DAG CONFIG ---
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 9, 9),
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "minio_to_snowflake",
    default_args=default_args,
    schedule_interval="*/3 * * * *",  # every 3 minutes
    catchup=False,
) as dag:

    download_task = PythonOperator(
        task_id="download_minio",
        python_callable=download_from_minio,
    )

    load_task = PythonOperator(
        task_id="load_snowflake",
        python_callable=load_to_snowflake,
        provide_context=True,
    )

    move_task = PythonOperator(
        task_id="move_to_loaded",
        python_callable=move_to_loaded,
        provide_context=True,
    )

    download_task >> load_task >> move_task
