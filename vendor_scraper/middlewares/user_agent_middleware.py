import random
from fake_useragent import UserAgent
import logging

logger = logging.getLogger(__name__)

class RandomUserAgentMiddleware:
    def __init__(self):
        self.ua = UserAgent()

    def process_request(self, request, spider):
        request.headers['User-Agent'] = self.ua.random
        logger.debug(f"[User-Agent] {request.headers['User-Agent']}")
