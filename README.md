# FirstView Downloader

A simple Windows application for bulk‑downloading runway collection images from [FirstView](https://www.firstview.com/)

## Features

- **Batch URLs** — Paste one or more FirstView collection links at once.  
- **Parallel Downloads** — Collections and their images download concurrently using async requests for faster throughput.
- **Progress Bars** — Track each collection’s download progress.
- **Default Path** — `%USERPROFILE%\Downloads\Firstview`
- **Custom Path** — Edit the path shown under **Download Path** or click **Change** to pick any folder.

## Installation
1. Go to **Releases** → **Assets**.  
2. Download `FirstView-Downloader.exe`.  

## Dependencies
- Windows 10+
- Python 3.8+  
- aiohttp  
- playwright  
- Pillow  
- requests  
- beautifulsoup4  
- PySide6  
