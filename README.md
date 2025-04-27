# FirstView Downloader

A bulk image downloader for FirstView collections using Selenium and Python.

## Features
- **Automated browser control**: Headless Chrome driven by Selenium.
- **Dynamic pagination**: Clicks “Next” buttons to traverse images.
- **Structured output**: Downloads organized in nested folders (Designer → Gender → Season → Album).
- **Configurable input**: Reads a list of target URLs from `config.txt` for batch processing.

## Prerequisites
- Python 3.8+
- Google Chrome (latest stable version)
- Chromedriver (automatically handled by `webdriver-manager`)
- Internet access to FirstView

## Installation
1. Clone the repository:
    ```bash
    git clone https://github.com/decarnin/firstview_downloader.git
    cd firstview_downloader
    ```
2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage
1. Add FirstView collection URLs to `config.txt`, one URL per line.
2. Run the script:
    ```bash
    python firstview_downloader.py
    ```
3. Downloaded images will be saved into:
    ```
    Downloads/<Designer>/<Gender>/<Season>/<Album>/
    ```

## Configuration
- **Headless Mode**: Enabled by default. To disable, remove the `--headless` argument in the `setup_driver()` function.
- **Download Format**: Images are saved as PNG by default. To change formats, modify `image.save(..., format='PNG')` in the `download_image()` function.

## Dependencies
Listed in `requirements.txt`:
    ```
    selenium
    webdriver-manager
    requests
    Pillow
    ```
