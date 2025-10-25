"""
Module: add_url_to_pool
Description: Đọc danh sách URL từ file CSV và thêm vào Redis List (queue start_urls).
"""

import os
import redis
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def get_redis_client():
    """Tạo Redis client từ URL trong .env"""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL is not set in .env")
    return redis.from_url(redis_url, decode_responses=True)


def process_batch(redis_client, redis_key, urls):
    """Thêm 1 batch URL vào Redis, loại trừ trùng lặp."""
    urls = list(set(urls))  # Loại bỏ trùng lặp trong batch
    logging.info(f"Processing batch with {len(urls)} unique URLs")

    with redis_client.pipeline() as pipe:
        existing_urls = set(pipe.lrange(redis_key, 0, -1))
        urls_to_add = [url for url in urls if url not in existing_urls]

        if not urls_to_add:
            logging.info("No new URLs to add in this batch.")
            return

        # Chia nhỏ để tránh quá tải Redis
        chunk_size = 1000
        for i in range(0, len(urls_to_add), chunk_size):
            chunk = urls_to_add[i:i + chunk_size]
            pipe.lpush(redis_key, *chunk)
            pipe.execute()
            logging.info(f"Added {len(chunk)} URLs to Redis List ({redis_key})")

        # Log các URL bị skip
        skipped = [u for u in urls if u in existing_urls]
        if skipped:
            logging.info(f"{len(skipped)} URLs already exist and were skipped.")


def add_url_to_pool(file_path="vendor_scraper/configs/urls_pool.csv", batch_size=10000):
    """Đọc URL từ CSV và thêm vào Redis List theo batch."""
    try:
        redis_client = get_redis_client()
        redis_key = "url_pools:start_urls"

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{file_path} not found")

        new_urls = []
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                url = line.strip()
                if url:
                    new_urls.append(url)
                if len(new_urls) >= batch_size:
                    process_batch(redis_client, redis_key, new_urls)
                    new_urls = []

        if new_urls:
            process_batch(redis_client, redis_key, new_urls)

        logging.info("All new URLs added to Redis List successfully!")

    except Exception as e:
        logging.error(f"Error adding URLs to pool: {e}", exc_info=True)


if __name__ == "__main__":
    add_url_to_pool()
