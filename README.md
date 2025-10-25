
````markdown
# 🕷️ Scraper Website Project  
**Distributed Web Crawler using Scrapy + Redis + PostgreSQL**

---

## 📘 Overview

This project — **`scraper-project`** — is a scalable, distributed web scraping system built with **Scrapy**, **Redis**, and **PostgreSQL**.  
It is designed for **massive data crawling**, **centralized control**, and **parallel execution** through multiple worker nodes.

> 💡 The architecture supports multi-domain crawling, HTML storage, and metadata tracking.

---

## ⚙️ Tech Stack

| Layer | Technology | Purpose |
|--------|-------------|----------|
| **Crawler Framework** | [Scrapy](https://scrapy.org) | Core crawling engine |
| **Distributed Queue** | [Redis](https://redis.io) | Centralized task queue for worker nodes |
| **Data Storage** | [PostgreSQL](https://www.postgresql.org/) | Metadata & structured data storage |
| **HTML Parser** | [BeautifulSoup4](https://pypi.org/project/beautifulsoup4/) | Cleaning and parsing HTML |
| **Environment Config** | [python-dotenv](https://pypi.org/project/python-dotenv/) | Manage environment variables |
| **Proxy & Rotation** | [scrapy-rotating-proxies](https://pypi.org/project/scrapy-rotating-proxies/), [fake-useragent](https://pypi.org/project/fake-useragent/) | Avoid IP bans |
| **Async Support** | [Twisted](https://twistedmatrix.com/) | Asynchronous networking |
| **HTML Storage** | Network Share / Local Folders | Store prettified HTML content |
| **Task CLI** | Custom Python Scripts | Add URLs, load data, parse results |

---

## 🧩 Project Structure

```bash
vendor_scraper/
│
├── vendor_scraper/
│   ├── configs/                         # Cấu hình đầu vào
│   │   ├── DOM_site.json                # Selector mapping cho từng website
│   │   └── list_user_agents.txt         # Danh sách user-agents thủ công (tùy chọn)
│   │
│   ├── dataflow/                        # Các module thực thi theo luồng dữ liệu
│   │   ├── load/
│   │   │   ├── add_url_to_pool.py       # Thêm URL vào Redis (start_urls)
│   │   │   └── load_metadata_to_db.py   # Ghi metadata từ Redis vào PostgreSQL
│   │   │
│   │   ├── parse/
│   │   │   └── parse_html_crawl.ipynb   # Notebook dùng để kiểm tra HTML & debug
│   │   │
│   │   └── process/
│   │       └── download_img.py          # Tải hình ảnh sản phẩm từ HTML
│   │
│   ├── middlewares/                     # Middleware chia theo chức năng
│   │   ├── base.py                      # Middleware mặc định (Scrapy template)
│   │   ├── browser_headers_middleware.py # Fake browser headers (ScrapeOps)
│   │   ├── proxy_middleware.py          # Proxy rotation handler
│   │   └── user_agent_middleware.py     # Fake User-Agent rotation
│   │
│   ├── spiders/
│   │   ├── distributed-worker.py        # Spider phân tán dùng Redis (Scrapy-Redis)
│   │   └── playwright_worker.py         # Spider dùng Playwright (cho trang động)
│   │
│   ├── items.py                         # Định nghĩa Item/Field cho pipeline
│   ├── pipelines.py                     # Pipeline xử lý, lưu HTML + metadata
│   └── settings.py                      # Cấu hình Scrapy project
│
├── pyproject.toml                       # Cấu hình project và dependencies
├── scrapy.cfg                           # Entry point Scrapy
└── README.md                            # Tài liệu dự án
````

---

## ⚙️ Features

| Feature                | Description                                         |
| ---------------------- | --------------------------------------------------- |
| **Scrapy + Redis**     | Enables horizontal scaling with multiple workers    |
| **Proxy Rotation**     | Integrated proxy middleware with authentication     |
| **Fake User-Agent**    | Random UA from file or ScrapeOps API                |
| **Playwright Support** | Crawl JavaScript-rendered websites                  |
| **HTML Storage**       | Store cleaned HTML locally or on shared network     |
| **Metadata Queue**     | Push crawl metadata into Redis for later processing |
| **PostgreSQL Loader**  | Auto-insert metadata from Redis into database       |

---

## 🚀 How It Works

### 1️⃣ Architecture Overview

```text
┌──────────────────────────┐
│       URL Producer       │  ← Push URLs to Redis queue
│  (add_url_to_pool.py)    │
└────────────┬─────────────┘
     │
     ▼
┌──────────────────────────┐
│  Redis Queue (url_pools) │  ← Acts as distributed scheduler
└────────────┬─────────────┘
     │
     ▼
┌──────────────────────────┐
│  Distributed Workers     │  ← Multiple Scrapy spiders pulling URLs
│  (spiders/distributed...)│
└────────────┬─────────────┘
     │
     ▼
┌──────────────────────────┐
│  Pipelines               │
│  - Clean HTML            │
│  - Save to storage       │
│  - Push metadata to Redis│
└────────────┬─────────────┘
     │
     ▼
┌──────────────────────────┐
│  Database / Data Lake    │  ← Store metadata or final data
└──────────────────────────┘
```

---

## 🧠 Core Components

### 🕸 `distributed-worker.py`

* Worker spider using `RedisSpider` to consume URLs from `url_pools:start_urls`.
* Loads domain-specific rules from `configs/DOM_site.json`.
* Extracts and cleans HTML using CSS selectors.
* Passes output to pipelines for saving.

---

### 📦 `items.py`

Defines `ProductItem` model with fields:

```python
domain, url_item, status_code, source_page_html
```

Optionally prettified with **BeautifulSoup** for clean formatting.

---

### ⚙️ `pipelines.py`

Handles post-crawl actions:

* Save HTML to storage path.
* Push metadata (URL, domain, file path, status, timestamp) to Redis queue `scrapy:metadata`.
* Organize storage by domain.
* Use SHA256 for unique file naming.

---

### ⚙️ `settings.py`

Core Scrapy configuration:

* Enables distributed scheduler (`scrapy_redis.scheduler`).
* Custom downloader middlewares for proxy and UA rotation.
* Controls concurrency, delays, and pipeline priorities.

---

### 🔧 `dataflow/load/add_url_to_pool.py`

Utility script to add new crawl URLs into Redis queue:

```bash
python -m vendor_scraper.dataflow.load.add_url_to_pool "https://example.com/page"
```

---

## 🧰 Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Dtsayy/scraper-website-project.git
cd cls-scraper-project
```

### 2️⃣ Install Dependencies

```bash
pip install -e .
# or, for dev mode
pip install -e .[dev]
```

### 3️⃣ Configure Environment

Create a `.env` file in the root directory:

```env
REDIS_URL=redis://localhost:6379
POSTGRES_URL=postgresql://user:password@localhost:5432/vendor_db
```

### 4️⃣ Verify Installation

```bash
scrapy list
# → should show: distributed-worker
```

---

## 🔄 Usage

### ➤ Add URLs to Queue

```bash
python -m vendor_scraper.dataflow.load.add_url_to_pool "https://example.com"
```

### ➤ Start a Distributed Worker

Each worker pulls from Redis automatically:

```bash
scrapy runspider vendor_scraper/spiders/distributed-worker.py
```

### ➤ Monitor Queue

```bash
redis-cli llen url_pools:start_urls
redis-cli llen scrapy:metadata
```

---

## 🧹 Output Example

**Stored HTML Path**

```text
html_storage/example.com/91e0b1...8f1b.html
```

**Metadata (Redis)**

```json
{
  "url": "https://example.com/page1",
  "domain": "example.com",
  "file_path": "./html_storage/example.com/91e0b1.html",
  "http_status": 200,
  "saved_date": "2025-10-25 12:10:33"
}
```

---

## 🧩 Future Improvements

* [ ] Add PostgreSQL loader pipeline
* [ ] Add retry + proxy rotation middleware
* [ ] Build dashboard for Redis queue monitoring
* [ ] Integrate Prefect / Airflow orchestration
* [ ] Automatic sitemap crawling

---

## 👨‍💻 Authors

**ThanhCD & TienTTM**
*Data Technician | Data Engineer Pathway*

---
