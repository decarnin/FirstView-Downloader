# FirstView Downloader

A simple Windows application for bulk‑downloading runway collection images from [FirstView](https://www.firstview.com/)

## Features

- **Batch URLs** — Paste one or more FirstView collection links at once.  
- **Parallel Downloads** — Collections and their images download concurrently using async requests for faster throughput.
- **Progress Bars** — Track each collection’s download progress.
- **Default Path** — `%USERPROFILE%\Pictures\Firstview`
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

## Acknowledgements
Fish icon by [Icons8](https://icons8.com/), licensed under [CC BY‑ND 3.0](https://creativecommons.org/licenses/by-nd/3.0/).
