"""
Spider: distributed_worker
Description:
    Worker spider dùng Scrapy-Redis để lấy URL từ Redis List `url_pools:start_urls`
    và trích xuất dữ liệu HTML theo cấu hình DOM từ `DOM_site.json`.
"""

import json
import scrapy
import logging
from urllib.parse import urlparse
from scrapy_redis.spiders import RedisSpider
from scrapy.loader import ItemLoader
from vendor_scraper.items import ProductItem


class VendorSpider(RedisSpider):
    name = "distributed-worker"
    redis_key = "url_pools:start_urls"
    redis_batch_size = 1
    max_idle_time = 7  # Seconds worker will wait before stopping when idle

    custom_settings = {
        "LOG_LEVEL": "INFO",
        "DOWNLOAD_DELAY": 2,  # Slight delay to avoid flooding
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 2,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            with open("vendor_scraper/configs/DOM_site.json", "r", encoding="utf-8") as f:
                self.website_configs = json.load(f)
        except FileNotFoundError:
            logging.critical("DOM_site.json not found! Spider will exit.")
            raise
        except json.JSONDecodeError:
            logging.critical("Error decoding DOM_site.json — please check the format.")
            raise

    def parse(self, response):
        domain = urlparse(response.url).netloc
        config = next(
            (c for c in self.website_configs["website"] if c["domain"] == domain), None
        )

        if not config:
            logging.warning(f"No configuration found for domain: {domain}")
            return

        loader = ItemLoader(item=ProductItem(), selector=response)
        loader.add_value("domain", domain)
        loader.add_value("url_item", response.url)
        loader.add_value("status_code", response.status)

        selector = config["selectors"].get("SOURCE_PAGE")
        if not selector:
            logging.warning(f"No SOURCE_PAGE selector found for {domain}")
            return

        logging.info(f"Parsing {response.url} using selector: {selector}")
        loader.add_css("source_page_html", selector)

        yield loader.load_item()
