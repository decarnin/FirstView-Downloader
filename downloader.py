import aiohttp
import asyncio
from playwright.async_api import async_playwright
from playwright.async_api import Page
from pathlib import Path
from urllib.parse import urljoin
import os
import io
from PIL import Image
from typing import Callable

async def download_image(session: aiohttp.ClientSession, url: str, download_path: Path, file_name: str) -> None:
    try:
        async with session.get(url) as response:
            response.raise_for_status() # Checks if the response is in the error range (4xx or 5xx) and raises an exception
            data = await response.read()
            image = Image.open(io.BytesIO(data))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.save(download_path / file_name, format = 'JPEG')
    except Exception as e:
        print(f'Error downloading image {url}: {e}')

async def get_thumbnails(page: Page, total_images: int) -> list[str]:
    thumbnail_list: list[str] = []

    for i in range(total_images):
        thumbnail = page.locator('.picture').nth(i)
        thumbnail_url = await thumbnail.get_attribute('src')
        thumbnail_list.append(thumbnail_url)
        await thumbnail.scroll_into_view_if_needed()

    return thumbnail_list

async def get_images(session: aiohttp.ClientSession, page: Page, download_path: Path, total_images: int, status_callback: Callable[[str], None], label: str) -> None:
    BASE = 'https://www.firstview.com'
    download_path.mkdir(parents = True, exist_ok = True)
    thumbnail_list = await get_thumbnails(page, total_images)
    first_thumbnail = urljoin(BASE, thumbnail_list[0])

    await page.locator('.picture').first.click()
    runway_image = page.locator('img[alt*="ImageID:"]')
    await runway_image.wait_for()
    first_runway = urljoin(BASE, await runway_image.get_attribute('src'))

    prefix = os.path.commonprefix([first_thumbnail, first_runway])
    suffix = os.path.commonprefix([first_thumbnail[::-1], first_runway[::-1]])[::-1]
    middle = first_runway[len(prefix): -len(suffix)]

    image_urls : list[str] = []
    for thumbnail in thumbnail_list:
        thumbnail_url = urljoin(BASE, thumbnail)
        download_url = prefix + middle + thumbnail_url[-len(suffix):]
        image_urls.append(download_url)

    futures: dict[asyncio.Task, int] = {}
    for i, url in enumerate(image_urls, start = 1):
        task = asyncio.create_task(download_image(session, url, download_path, f'{i}.jpg'))
        futures[task] = i

    downloaded_images = 0
    # as each download finishes, emit a PROGRESS update
    for task in asyncio.as_completed(futures):
        await task
        downloaded_images += 1
        status_callback(f'PROGRESS:{label}:{downloaded_images}:{total_images}')

async def main(url_list: list[str], base_path: Path, status_callback: Callable[[str], None]) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless = True)
        context = await browser.new_context()
        page = await context.new_page()

        firstview: Path = Path.home() / 'Downloads' / 'FirstView'
    
        timeout = aiohttp.ClientTimeout(total = 60)
        connector = aiohttp.TCPConnector(limit = 100, limit_per_host = 10, force_close = True)
        headers   = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)…',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': page.url,
        }
        async with aiohttp.ClientSession(connector = connector, timeout = timeout, headers = headers) as session:
            for url in url_list:
                await page.goto(url)

                raw_title = await page.locator('.pageTitle').text_content()
                runway_information = raw_title.split(' - ')
                designer = runway_information[0]
                album = runway_information[2].rstrip()
                gender = runway_information[3]

                raw_season = await page.locator('.season').text_content()
                season = raw_season.replace(' / ', ' ')
                
                raw_total_images = await page.locator('.info').text_content()
                total_images = int(raw_total_images.split(' ')[0])

                runway_directory: Path = firstview / designer / gender/ season / album
                runway_directory.mkdir(parents = True, exist_ok = True)
                
                label = f'{designer} - {gender} - {raw_season} - {album}'
                await get_images(session, page, runway_directory, total_images, status_callback, label)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())