import os
import json
import hashlib
import redis
import random
import logging
import asyncio
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import stealth_async
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

try:
    from fake_useragent import UserAgent
    ua = UserAgent()
    use_fake_ua = True
except ImportError:
    use_fake_ua = False

# Configuration
CONFIG = {
    # Browser configuration
    "browser_type": "firefox", # chromium or firefox
    "headless": False,
    "browser_args": [
        "--disable-gpu",
        "--enable-webgl",
        "--mute-audio",
        "--no-sandbox",
        "--disable-extensions",
        "--disable-http2",
        "--disable-cache",
        # "--disable-blink-features=AutomationControlled",
        # "--disable-dev-shm-usage",
        # "--window-size=1920,1080",
    ],
    "context_settings": {
        "java_script_enabled": True,
        "ignore_https_errors": True,
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "permissions": ["geolocation"],
        "extra_http_headers": {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        },
    },
    
    # Redis configuration
    "redis_url": os.getenv("REDIS_URL"), # Connect to Redis server
    "url_pools": "url_amazon:start_urls", # URLs pool
    "metadata_crawler": "url_amazon:metadata", # Metadata storage queue
    # "storage_folder": "html", # HTML storage folder
    "storage_folder": "//172.16.9.61/02_Picture_Lookup/Crawling/html_storage", # HTML storage folder
    
    # Retries settings
    "max_retries": 2,
    "base_wait_time": 5, # base duration between retries
    "max_urls_before_restart": 1000,
    "pause_every": 20000,
    "pause_duration": 180,
}

# Validate configuration
def validate_config():
    if CONFIG["browser_type"] not in ["chromium", "firefox"]:
        raise ValueError(f"Invalid browser_type: {CONFIG['browser_type']}. Must be 'chromium' or 'firefox'.")
    if CONFIG["max_retries"] < 0:
        raise ValueError("max_retries must be non-negative")
    if CONFIG["base_wait_time"] <= 0:
        raise ValueError("base_wait_time must be positive")
    if CONFIG["max_urls_before_restart"] <= 0:
        raise ValueError("max_urls_before_restart must be positive")
    if CONFIG["pause_every"] <= 0:
        raise ValueError("pause_every must be positive")
    if CONFIG["pause_duration"] <= 0:
        raise ValueError("pause_duration must be positive")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Redis client
try:
    redis_client = redis.from_url(CONFIG["redis_url"], decode_responses=True)
except redis.RedisError as e:
    logger.error(f"Failed to connect to Redis: {str(e)}")
    raise

# Function to get a random User-Agent
def get_random_user_agent():
    """Get a random User-Agent if fake_useragent is available."""
    if use_fake_ua:
        try:
            return ua.random
        except Exception as e:
            logger.error(f"Error getting random User-Agent: {str(e)}")
    return None


# Simulation functions
async def simulate_scrollbar_interaction(page):
    """Simulate clicking scrollbar and scrolling up/down."""
    try:
        await page.mouse.click(1880, 540)  # Click near right edge
        await page.evaluate("window.scrollBy(0, 1000)")
        await asyncio.sleep(0.4)
        await page.evaluate("window.scrollBy(0, -1000)")
        await asyncio.sleep(0.6)
        logger.info("Simulated scrollbar interaction")
    except Exception as e:
        logger.warning(f"Failed to simulate scrollbar interaction: {str(e)}")

# Simulate mouse movement
async def simulate_mouse_movement(page):
    """Simulate natural mo  movement across the page."""
    try:
        for _ in range(3):
            x = random.randint(100, 1800)
            y = random.randint(100, 900)
            await page.mouse.move(x, y, steps=10)
            await asyncio.sleep(random.uniform(0.2, 0.5))
        logger.info("Simulated mouse movement")
    except Exception as e:
        logger.warning(f"Failed to simulate mouse movement: {str(e)}")

# Simulate fake typing
async def simulate_fake_typing(page):
    """Simulate typing in a text input field."""
    try:
        inputs = await page.query_selector_all("input[type='text'], input[type='search']")
        if inputs:
            input_field = random.choice(inputs)
            await input_field.focus()
            await input_field.type("test search", delay=random.uniform(50, 150))
            await asyncio.sleep(0.5)
            await input_field.press("Backspace", delay=random.uniform(50, 150))
            logger.info("Simulated fake typing")
    except Exception as e:
        logger.warning(f"Failed to simulate fake typing: {str(e)}")

# Simulate smooth scrolling
async def simulate_smooth_scrolling(page):
    """Simulate smooth, variable-speed scrolling."""
    try:
        scroll_amount = random.randint(500, 1500)
        await page.evaluate(f"""
            window.scrollTo({{ 
                top: {scroll_amount}, 
                behavior: 'smooth' 
            }})
        """)
        await asyncio.sleep(random.uniform(0.5, 1))
        await page.evaluate(f"""
            window.scrollTo({{ 
                top: 0, 
                behavior: 'smooth' 
            }})
        """)
        await asyncio.sleep(random.uniform(0.5, 1))
        logger.info("Simulated smooth scrolling")
    except Exception as e:
        logger.warning(f"Failed to simulate smooth scrolling: {str(e)}")

async def simulate_scrollbar_drag(page):
    """Simulate clicking and slowly dragging the scrollbar down over 1-2 seconds."""
    try:
        # Click the scrollbar (near right edge of the window)
        scrollbar_x = 1880  # Approximate scrollbar position
        start_y = 540  # Middle of the window
        await page.mouse.move(scrollbar_x, start_y)
        await page.mouse.down()

        # Simulate slow drag down
        drag_duration = random.uniform(1, 2)  # Random duration between 1-2 seconds
        steps = 10  # Number of steps for smooth dragging
        step_duration = drag_duration / steps
        drag_distance = 500  # Pixels to drag down

        for i in range(steps):
            y = start_y + (drag_distance * (i + 1) / steps)
            await page.mouse.move(scrollbar_x, y, steps=5)
            await asyncio.sleep(step_duration)

        # Release the mouse
        await page.mouse.up()
        logger.info("Simulated scrollbar drag")
    except Exception as e:
        logger.warning(f"Failed to simulate scrollbar drag: {str(e)}")

# List of behavior simulation functions
BEHAVIOR_SIMULATIONS = [
    # simulate_scrollbar_interaction,
    # simulate_mouse_movement,
    simulate_fake_typing,
    simulate_smooth_scrolling,
    simulate_scrollbar_drag,
]

#### Simuate user behavior
async def simulate_user_behavior(page):
    """Randomly select and execute a user behavior simulation."""
    try:
        behavior = random.choice(BEHAVIOR_SIMULATIONS)
        await behavior(page)
    except Exception as e:
        logger.warning(f"Failed to simulate user behavior: {str(e)}")


#### Initialize browser and context
async def initialize_browser(playwright, browser_type, headless, args, context_settings):
    """Initialize the browser and context."""
    try:
        browser_launcher = (
            playwright.chromium if browser_type == "chromium" else playwright.firefox
        )
        browser = await browser_launcher.launch(headless=headless, args=args)
        context = await browser.new_context(**context_settings)
        page = await context.new_page()
        await stealth_async(page)
        
        logger.info(f"Initialized {browser_type} browser")
        return browser, context, page
    
    except Exception as e:
        logger.error(f"Failed to initialize {browser_type} browser: {str(e)}")
        raise

#### Load page with retries and exponential backoff
async def load_page_with_retry(page, url, max_retries, base_wait_time):
    """Load a page with retries and exponential backoff."""
    for attempt in range(max_retries):
        user_agent = get_random_user_agent()
        headers = {"User-Agent": user_agent} if user_agent else {}
        logger.info(f"Attempt {attempt + 1} for {url} with User-Agent: {user_agent or 'default'}")
        await page.context.set_extra_http_headers(headers)
        
        cookies = await page.context.cookies()
        await page.context.add_cookies(cookies)
        logger.info(f"Loaded {len(cookies)} cookies for {url}")

        try:
            response = await page.goto(url, timeout=70000, wait_until="networkidle")
            
            if response and response.status in [404, 500]:
                logger.error(f"HTTP error {response.status} for {url}. Skipping retries.")
                return False
            if response and response.status >= 400:
                raise Exception(f"HTTP error: {response.status}")
            
            await simulate_user_behavior(page) # Simaulate user behavior after loading the page
            return True
        
        except PlaywrightTimeoutError as e:
            logger.warning(f"Timeout loading {url}: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading {url}: {str(e)}")

        if attempt < max_retries - 1:
            wait_time = base_wait_time * (2 ** attempt) + random.uniform(1, 3)
            logger.info(f"Retrying after {wait_time:.2f}s... ({attempt + 2}/{max_retries})")
            await asyncio.sleep(wait_time)
    return False


#### Save HTML content
async def save_html(url, html, storage_folder):
    """Save cleaned HTML content to a file."""
    try:
        # Check if HTML content is valid
        if not html or not isinstance(html, str):
            logger.error(f"Invalid HTML content for {url}: {html}")
            return None

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "video"]):
            tag.decompose()
        
        # Use prettify() instead of pretty_print()
        cleaned_html = soup.prettify()

        domain = urlparse(url).netloc
        domain_folder = os.path.join(storage_folder, domain)
        os.makedirs(domain_folder, exist_ok=True)

        hash_filename = hashlib.sha256(url.encode("utf-8")).hexdigest() + ".html"
        file_path = os.path.join(domain_folder, hash_filename)

        with file_writer(file_path) as f:
            if f:
                f.write(cleaned_html)
                logger.info(f"Stored HTML: {file_path}")
                return file_path
        return None
    except AttributeError as e:
        logger.error(f"BeautifulSoup error for {url}: {str(e)}. Possibly invalid HTML or method issue.")
        return None
    except Exception as e:
        logger.error(f"Failed to save HTML for {url}: {str(e)}")
        return None


#### Write to file with context manager
@contextmanager
def file_writer(file_path):
    """Context manager for file writing."""
    try:
        file = open(file_path, "w", encoding="utf-8")
        yield file
    except (OSError, IOError) as e:
        logger.error(f"Failed to write to file {file_path}: {str(e)}")
        yield None
    finally:
        if file:
            file.close()


#### Save metadata to Redis
async def save_metadata(url, file_path, user_agent, browser_type):
    """Save metadata to Redis."""
    try:
        metadata = {
            "url": url,
            "domain": urlparse(url).netloc,
            "file_path": file_path,
            "http_status": 200,
            "saved_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_agent": user_agent or "default",
            "browser_type": browser_type,
        }
        redis_client.rpush(CONFIG["metadata_crawler"], json.dumps(metadata))
        logger.debug(f"Metadata saved for {url}: {metadata}")
        
    except redis.RedisError as e:
        logger.error(f"Failed to save metadata for {url}: {str(e)}")


#### Restart browser context (if increased memory issues)
async def restart_browser_context(browser, page, context, context_settings):
    """Restart browser context to clear memory."""
    try:
        await page.close()
        await context.close()
        context = await browser.new_context(**context_settings)
        page = await context.new_page()
        await stealth_async(page)
        logger.info("Restarted browser context")
        return context, page
    
    except Exception as e:
        logger.error(f"Failed to restart browser context: {str(e)}")
        raise

# Main crawling function
async def crawl_urls():
    """Main crawling logic."""
    try:
        validate_config()
        os.makedirs(CONFIG["storage_folder"], exist_ok=True)
        urls_processed = 0

        async with async_playwright() as playwright:
            # Initialize browser and context
            browser, context, page = await initialize_browser(
                playwright,
                CONFIG["browser_type"],
                CONFIG["headless"],
                CONFIG["browser_args"],
                CONFIG["context_settings"],
            )
            user_agent = get_random_user_agent() # Get random User-Agent for the session

            try:
                while True:
                    # Get URL from Redis
                    url = redis_client.lpop(CONFIG["url_pools"])
                    if not url:
                        logger.info("No more URLs to crawl.")
                        break

                    # load page with retries and exponential backoff
                    logger.info(f"Crawling: {url}")
                    if not await load_page_with_retry(page, url, CONFIG["max_retries"], CONFIG["base_wait_time"]):
                        logger.error(f"Failed to load {url} after retries. Skipping.")
                        continue
                    
                    # Get page source
                    try:
                        html = await page.content()
                    except Exception as e:
                        logger.error(f"Failed to get page source for {url}: {str(e)}")
                        continue
                    
                    # Save HTML content and metadata
                    file_path = await save_html(url, html, CONFIG["storage_folder"])
                    if file_path:
                        await save_metadata(url, file_path, user_agent, CONFIG["browser_type"])

                    # Pause every url processed
                    urls_processed += 1

                    if urls_processed % CONFIG["pause_every"] == 0:
                        logger.info(f"Processed {urls_processed} URLs, pausing for {CONFIG['pause_duration']} seconds...")
                        await asyncio.sleep(CONFIG["pause_duration"])
                    
                    # Restart browser context if memory issues arise
                    if urls_processed >= CONFIG["max_urls_before_restart"]:
                        logger.info("Restarting browser context to clear memory...")
                        urls_processed = 0
                        context, page = await restart_browser_context(
                            browser, page, context, CONFIG["context_settings"]
                        )

                    # Pause random between requests
                    logger.info(f"Pausing for a random (2s->4s) duration between requests")
                    await asyncio.sleep(random.uniform(1, 3))
                    
            except Exception as e:
                logger.error(f"Crawling interrupted: {str(e)}")
            finally:
                await page.close()
                await context.close()
                await browser.close()
                logger.info("Browser closed successfully.")

    except Exception as e:
        logger.error(f"Fatal error in crawl_urls: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(crawl_urls())