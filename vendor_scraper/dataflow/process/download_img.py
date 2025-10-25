import asyncio
import aiohttp
import pandas as pd
import io
from PIL import Image
import logging
import os
from datetime import datetime
import concurrent.futures
from tqdm import tqdm
import aiohttp_retry
import nest_asyncio

# Apply nest_asyncio to allow running asyncio in environments like Jupyter, Anaconda, or Google Colab
# nest_asyncio.apply()

# Initialize logging
logging.basicConfig(
    filename=f"download_image_{datetime.now().strftime('%Y%m%d')}.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# File paths
excel_path = r"download_img.xlsx"
img_storage_path = r"D:\05_ RELEASE_UDB\Image_20250709_Create_Matrix_Id\\"

# Verify file existence
if not os.path.exists(excel_path):
    raise FileNotFoundError(f"Excel file not found: {excel_path}")

# Create output directory if it doesn't exist
os.makedirs(img_storage_path, exist_ok=True)

# Read Excel file
df = pd.read_excel(excel_path)
print(f"Number of rows in DataFrame: {len(df)}")

# Headers for HTTP requests
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36"
    )
}

async def save_image(image_content, img_name, img_storage_path):
    """Save image content to disk using PIL in a thread pool."""
    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await loop.run_in_executor(
                pool,
                lambda: _save_image_sync(image_content, img_name, img_storage_path)
            )
        logging.info(f"Downloaded {img_name}")
    except Exception as e:
        logging.error(f"Failed to save {img_name}: {e}")

def _save_image_sync(image_content, img_name, img_storage_path):
    """Synchronous function to save image using PIL."""
    image_file = io.BytesIO(image_content)
    image = Image.open(image_file)
    # Convert CMYK to RGB if necessary
    if image.mode == 'CMYK':
        image = image.convert('RGB')
    file_path = os.path.join(img_storage_path, img_name)
    image.save(file_path, "PNG")

async def download_image(session, img_url, img_name, img_storage_path, retries=3):
    """Download a single image with retry logic."""
    retry_client = aiohttp_retry.RetryClient(
        client_session=session,
        retry_options=aiohttp_retry.ExponentialRetry(attempts=retries)
    )
    try:
        async with retry_client.get(img_url, headers=headers, timeout=30) as response:
            if response.status == 200:
                image_content = await response.read()
                await save_image(image_content, img_name, img_storage_path)
            else:
                logging.error(f"Failed to download {img_name}: HTTP {response.status}")
    except Exception as e:
        logging.error(f"Failed to download {img_name}: {e}")

async def download_images_batch(urls, names, img_storage_path, batch_size=100):
    """Download images in batches with connection pooling."""
    connector = aiohttp.TCPConnector(limit=100)  # Limit concurrent connections
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            batch_names = names[i:i + batch_size]
            tasks = [
                download_image(session, url, name, img_storage_path)
                for url, name in zip(batch_urls, batch_names)
                if pd.notna(url) and pd.notna(name)
            ]
            for future in tqdm(
                asyncio.as_completed(tasks),
                total=len(tasks),
                desc=f"Downloading batch {i//batch_size + 1}"
            ):
                await future

async def main():
    """Main function to orchestrate the download process."""
    # Log start time with datetime format
    logging.info("Starting image download process.", extra={"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    
    # Read URLs and names from DataFrame
    urls = df["URL_PICTURE"].tolist()
    names = df["PICTURE_NAME"].tolist()
    
    # Download images in batches
    await download_images_batch(urls, names, img_storage_path, batch_size=100)
    
    # Log end time with datetime format
    logging.info("Image download process completed.", extra={"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())