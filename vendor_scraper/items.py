"""
Defines Scrapy Item classes for vendor_scraper project.
"""

import scrapy
from scrapy.loader.processors import MapCompose, TakeFirst
from bs4 import BeautifulSoup


def prettify_html(html):
    """Clean and prettify HTML."""
    try:
        soup = BeautifulSoup(html, "lxml")
        cleaned = " ".join(soup.prettify().split())
        return cleaned
    except Exception:
        return html.strip()


class ProductItem(scrapy.Item):
    """Item structure for storing scraped product data."""

    domain = scrapy.Field(output_processor=TakeFirst())
    url_item = scrapy.Field(output_processor=TakeFirst())
    status_code = scrapy.Field(output_processor=TakeFirst())
    source_page_html = scrapy.Field(input_processor=MapCompose(prettify_html))
