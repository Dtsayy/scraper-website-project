import base64

class MyProxyMiddleware:
    def __init__(self, settings):
        self.user = settings.get('PROXY_USER')
        self.password = settings.get('PROXY_PASSWORD')
        self.endpoint = settings.get('PROXY_ENDPOINT')
        self.port = settings.get('PROXY_PORT')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        if not all([self.user, self.password, self.endpoint, self.port]):
            return
        user_credentials = f'{self.user}:{self.password}'
        encoded = base64.b64encode(user_credentials.encode()).decode()
        request.meta['proxy'] = f'http://{self.endpoint}:{self.port}'
        request.headers['Proxy-Authorization'] = f'Basic {encoded}'
