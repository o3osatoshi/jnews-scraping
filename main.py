import os
import time
import requests
import chardet
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

load_dotenv()


def detect_encoding(content):
    result = chardet.detect(content)
    return result['encoding']


def download_file(url, folder, auth=None):
    parsed_url = urlparse(url)
    local_filename = os.path.join(folder, parsed_url.path.lstrip('/'))
    os.makedirs(os.path.dirname(local_filename), exist_ok=True)
    try:
        response = requests.get(url, auth=auth, stream=True)
        response.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"Downloaded {url} to {local_filename}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while downloading {url}: {e}")
    return local_filename


def download_html_with_resources(url, html_path, folder, user, password):
    try:
        auth = HTTPBasicAuth(user, password)
        response = requests.get(url, auth=auth)
        response.raise_for_status()

        # 文字エンコーディングを自動検出
        encoding = detect_encoding(response.content)
        response.encoding = encoding

        # BeautifulSoupのパース時にエンコーディングを指定
        soup = BeautifulSoup(response.content, 'html.parser', from_encoding=encoding)

        # Create folders for resources
        os.makedirs(folder, exist_ok=True)

        # Download CSS
        for link in soup.find_all('link', href=True):
            if link['href'].startswith(('http://', 'https://')) or link['href'].startswith('.'):
                resource_url = urljoin(url, link['href'])
                download_file(resource_url, folder, auth)

        # Download JS
        for script in soup.find_all('script', src=True):
            if script['src'].startswith(('http://', 'https://')) or script['src'].startswith('.'):
                resource_url = urljoin(url, script['src'])
                download_file(resource_url, folder, auth)

        # Download images
        for img in soup.find_all('img', src=True):
            if img['src'].startswith(('http://', 'https://')) or img['src'].startswith('.'):
                resource_url = urljoin(url, img['src'])
                download_file(resource_url, folder, auth)

        # Save HTML without modifying paths
        local_html_path = os.path.join(folder, urlparse(url).path.lstrip('/'))
        os.makedirs(os.path.dirname(local_html_path), exist_ok=True)
        with open(local_html_path, 'w') as f:
            f.write(soup.prettify())
        print(f"HTML content saved to {local_html_path}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")


def get_hrefs(url, user, password):
    auth = HTTPBasicAuth(user, password)
    response = requests.get(url, auth=auth)
    response.raise_for_status()

    # 文字エンコーディングを自動検出
    encoding = detect_encoding(response.content)
    response.encoding = encoding

    soup = BeautifulSoup(response.content, 'html.parser', from_encoding=encoding)

    hrefs = [a['href'] for a in soup.find_all('a', href=True) if "JNEWS LETTER" in a.text]

    return hrefs


def replace_substring(original_string):
    return original_string.replace('./', 'mem/back/')


if __name__ == '__main__':
    base_url = os.getenv("BASE_URL")
    user = os.getenv("BASIC_AUTH_USER")
    password = os.getenv("BASIC_AUTH_PASSWORD")

    folder = "jnews"

    for i in range(1996, 2025):
        html_path = f"mem/back/backNumber_{i}.html"
        url = f"{base_url}/{html_path}"
        hrefs = get_hrefs(url, user, password)
        download_html_with_resources(url, html_path, folder, user, password)
        print(hrefs)

        for href in hrefs:
            html_path = replace_substring(href)
            url = f"{base_url}/{html_path}"
            download_html_with_resources(url, html_path, folder, user, password)
            time.sleep(1)
