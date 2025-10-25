"""
Scrapy project settings for vendor_scraper
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_NAME = "vendor_scraper"
SPIDER_MODULES = ["vendor_scraper.spiders"]
NEWSPIDER_MODULE = "vendor_scraper.spiders"

ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 2
AUTOTHROTTLE_ENABLED = False

DOWNLOADER_MIDDLEWARES = {
    "vendor_scraper.middlewares.user_agent_middleware.RandomUserAgentMiddleware": 400,
    "vendor_scraper.middlewares.proxy_middleware.MyProxyMiddleware": 410,
    # "vendor_scraper.middlewares.browser_headers_middleware.ScrapeOpsFakeBrowserHeaderAgentMiddleware": 420,
}

ITEM_PIPELINES = {
    "vendor_scraper.pipelines.StoreHTMLPipeline": 450,
}

# Redis (Scrapy-Redis integration)
REDIS_URL = os.getenv("REDIS_URL")
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
SCHEDULER_PERSIST = True

# Logging & encoding
LOG_LEVEL = "INFO"
FEED_EXPORT_ENCODING = "utf-8"

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
