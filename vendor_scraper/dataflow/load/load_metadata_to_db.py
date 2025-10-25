"""
Module: load_metadata_to_db
Description: Lấy dữ liệu metadata từ Redis queue và insert vào PostgreSQL theo batch.
"""

import os
import sys
import json
import time
import uuid
import redis
import psycopg2
import logging
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

BATCH_SIZE = 10000
CHECK_INTERVAL = 10


def get_redis_client():
    """Tạo Redis client từ REDIS_URL"""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL not set in environment")
    return redis.from_url(redis_url, decode_responses=True)


def get_postgres_connection():
    """Tạo kết nối PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        logging.info("Connected to PostgreSQL successfully.")
        return conn, conn.cursor()
    except psycopg2.OperationalError as e:
        logging.critical(f"PostgreSQL connection failed: {e}")
        sys.exit(1)


def backup_metadata(batch):
    """Backup metadata batch ra file JSON"""
    os.makedirs("metadata", exist_ok=True)
    date_str = time.strftime("%Y%m%d_%H%M")
    backup_path = f"metadata/metadata_backup_{uuid.uuid4().hex}_{date_str}.json"
    with open(backup_path, "w", encoding="utf-8") as f:
        for record in batch:
            json.dump(record, f, ensure_ascii=False)
            f.write("\n")
    return backup_path


def insert_metadata_to_db(cursor, conn, batch):
    """Thực hiện batch insert vào bảng PostgreSQL"""
    query = """
        INSERT INTO metadata_crawl_website 
        (url, domain, file_html, http_status, saved_date, crawl_status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    args = [
        (
            item["url"],
            item["domain"],
            item.get("file_path", ""),
            item["http_status"],
            item["saved_date"],
            item.get("crawl_status", "")
        )
        for item in batch
    ]

    cursor.executemany(query, args)
    conn.commit()


def main():
    redis_client = get_redis_client()
    conn, cursor = get_postgres_connection()

    while True:
        try:
            queue_length = redis_client.llen("scrapy:metadata")
            logging.info(f"Queue length: {queue_length}")

            if queue_length == 0:
                logging.warning(f"Queue empty, waiting {CHECK_INTERVAL} seconds...")
                time.sleep(CHECK_INTERVAL)
                continue

            batch_size = min(queue_length, BATCH_SIZE)
            batch_data = redis_client.lrange("scrapy:metadata", 0, batch_size - 1)
            batch = [json.loads(data) for data in batch_data]

            backup_file = backup_metadata(batch)
            logging.info(f"Backed up batch to {backup_file}")

            insert_metadata_to_db(cursor, conn, batch)
            logging.info(f"Inserted {len(batch)} records into PostgreSQL")

            redis_client.ltrim("scrapy:metadata", batch_size, -1)
            logging.info(f"Removed {len(batch)} records from Redis queue")

            # Optional cleanup backup
            # os.remove(backup_file)

            time.sleep(CHECK_INTERVAL)

        except psycopg2.Error as e:
            logging.error(f"Database error: {e}")
            conn.rollback()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            logging.error(f"Unexpected error: {e}", exc_info=True)
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
