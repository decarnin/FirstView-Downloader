from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import os
import requests
import io
from PIL import Image

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(service = ChromeService(ChromeDriverManager().install()), options = options)
    return driver

def download_image(url: str, download_path: str, file_name: str):
    try:
        image_content = requests.get(url).content
        image_file = io.BytesIO(image_content)
        image = Image.open(image_file)
        file_path = os.path.join(download_path, file_name)
        with open(file_path, 'wb') as file:
            image.save(file, format = 'PNG')
    except Exception as e:
        print(f'Error downloading image: {e}')

def get_images(driver: webdriver.Chrome, url: str, download_path: str, total_images: int):
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    current_image = 1

    thumbnail = driver.find_elements(By.CLASS_NAME, 'picture')[0]
    try:
        wait.until(EC.element_to_be_clickable(thumbnail))
        ActionChains(driver).move_to_element(thumbnail).click().perform()
    except Exception as e:
        print(f'Error clicking thumbnail: {e}')

    while current_image < total_images + 1:
        try:
            runway_image = wait.until(
                EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'ImageID:')]"))
            )

            image_url = runway_image.get_attribute('src')
            download_image(image_url, download_path, f'{current_image}.png')

            current_image += 1
            next_button = wait.until(
                EC.element_to_be_clickable((By.LINK_TEXT, 'next'))
            )
            next_button.click()

        except Exception as e:
            print(f'Error fetching image: {e}')

def main():
    url_list: list[str] = []
    with open('config.txt') as file:
        for line in file:
            url_list.append(line.strip())

    driver = setup_driver()
    wait = WebDriverWait(driver, 10)

    if not os.path.exists('Downloads'):
        os.makedirs('Downloads')
    os.chdir('Downloads')

    for url in url_list:
        driver.get(url)

        runway_information = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'pageTitle'))).text.split(' - ')
        designer = runway_information[0]
        album = runway_information[2]
        gender = runway_information[3]
        season = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'season'))).text.replace(' / ', ' ')
        total_images = int(wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'info'))).text.split(' ')[0])

        if not os.path.exists(designer):
            os.makedirs(designer)
        os.chdir(designer)

        if not os.path.exists(gender):
            os.makedirs(gender)
        os.chdir(gender)

        if not os.path.exists(season):
            os.makedirs(season)
        os.chdir(season)

        if not os.path.exists(album):
            os.makedirs(album)
        else:
            os.chdir('../../..')
            continue

        get_images(driver, url, album, total_images)
        os.chdir('../../..')

    driver.quit()

if __name__ == '__main__':
    main()
