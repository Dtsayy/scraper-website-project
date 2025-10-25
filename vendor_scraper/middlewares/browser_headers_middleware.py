import requests, random, logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class ScrapeOpsFakeBrowserHeaderAgentMiddleware:
    def __init__(self, settings):
        self.api_key = settings.get('SCRAPEOPS_API_KEY')
        self.endpoint = settings.get('SCRAPEOPS_FAKE_BROWSER_HEADER_ENDPOINT', 'http://headers.scrapeops.io/v1/browser-headers')
        self.num_results = settings.get('SCRAPEOPS_NUM_RESULTS')
        self.headers_list = []
        self._get_headers_list()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def _get_headers_list(self):
        payload = {'api_key': self.api_key}
        if self.num_results:
            payload['num_results'] = self.num_results
        res = requests.get(self.endpoint, params=urlencode(payload))
        self.headers_list = res.json().get('result', [])

    def process_request(self, request, spider):
        if not self.headers_list:
            return
        header = random.choice(self.headers_list)
        request.headers.update(header)
        logger.debug(f"[Browser-Headers] Applied headers for {request.url}")
