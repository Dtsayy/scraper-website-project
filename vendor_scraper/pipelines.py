"""
Pipelines: handle scraped items
- StoreHTMLPipeline: Save HTML files to server/local folder
- Push metadata to Redis queue for downstream processing
"""

import os
import json
import redis
import hashlib
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from scrapy.exceptions import DropItem
from itemadapter import ItemAdapter


class StoreHTMLPipeline:
    """Pipeline: Save cleaned HTML content and metadata to Redis."""

    SERVER_FOLDER = r".\html_storage"
    LOCAL_FOLDER = "html_storage"

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        if not self.redis_url:
            raise ValueError("REDIS_URL is missing in environment variables")
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        domain = adapter.get("domain")
        url = adapter.get("url_item")
        status = adapter.get("status_code")
        html_content = adapter.get("source_page_html")

        if not all([domain, url, html_content]):
            raise DropItem(f"Incomplete item: {item}")

        logging.info(f"Storing URL: {url} (status: {status})")

        try:
            soup = BeautifulSoup(html_content, "html.parser")
            for tag in soup(["video", "script", "iframe"]):
                tag.decompose()
            cleaned_html = soup.prettify()

            storage_folder = (
                self.SERVER_FOLDER
                if os.path.exists(self.SERVER_FOLDER)
                else self.LOCAL_FOLDER
            )
            os.makedirs(os.path.join(storage_folder, domain), exist_ok=True)

            hash_name = hashlib.sha256(url.encode("utf-8")).hexdigest() + ".html"
            file_path = os.path.join(storage_folder, domain, hash_name)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(cleaned_html)

            logging.info(f"HTML saved: {file_path}")

        except Exception as e:
            logging.error(f"Error saving HTML for {url}: {e}")
            raise DropItem(f"Failed to save HTML for {url}")

        metadata = {
            "url": url,
            "domain": domain,
            "file_path": file_path,
            "http_status": status,
            "saved_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "crawl_status": "success",
        }

        # Push metadata to Redis
        self.redis_client.rpush("scrapy:metadata", json.dumps(metadata))
        return item
