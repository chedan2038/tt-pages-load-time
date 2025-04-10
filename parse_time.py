import argparse
from urllib.parse import urlparse, urlsplit, urlunparse

from selenium import webdriver
from selenium.common import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

DEFAULT_LINK = 'https://onlinetimer.ru/'

parser = argparse.ArgumentParser()
parser.add_argument(
    '-l', '--link',
    type=str,
    default=DEFAULT_LINK,
    help=f'Ссылка (по умолчанию: "{DEFAULT_LINK}")')

parser.add_argument(
    '-m', '--max',
    type=int,
    default=float('inf'),
    help='Сколько ссылок проверить (по умолчанию: Все')

args = parser.parse_args()

# CFG
TIMEOUT = 10
BASED_ON_URL_LINKS = True

visited = set()
to_visit = {args.link}
driver = webdriver.Chrome()


def extract_domain(url: str) -> str:
    """Возвращает домен"""

    return urlparse(url).netloc


start_domain = extract_domain(args.link)


def get_links() -> set:
    """Поиск ссылок на странице
    :return Уникальные ссылки
    """

    links = set()
    elements_href = driver.find_elements(By.XPATH, '//a[@href]')

    for e in elements_href:
        href = e.get_attribute('href')

        if BASED_ON_URL_LINKS:
            if extract_domain(href) == start_domain:
                links.add(normalize_url(href))
        else:
            links.add(normalize_url(href))

    return links


def normalize_url(href: str) -> str:
    """Убирает query-строку и фрагмент из URL.
    :return Нормализованный URL
    """

    parsed = urlsplit(href)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))


def get_page_load_time() -> float:
    """Вычисляет время загрузки страницы с помощью performance.timing
    Если возвращаемое значение '-1' -страница не загрузилась

    :return Время загрузки страницы
    """

    try:
        WebDriverWait(driver, timeout=TIMEOUT).until(
            lambda d: d.execute_script("return document.readyState") == "complete")

        navigation_timing = driver.execute_script("return window.performance.timing;")
        load_time = (navigation_timing['loadEventEnd'] - navigation_timing['navigationStart']) / 1000

        return load_time

    except TimeoutException:
        return -1.000


def pages_load_time_top() -> list[tuple[str, float]]:
    """Составляет список страниц сайта и времени их загрузки, сортируя от самых медленных к самым быстрым.
    :return Список страниц и времени за которое они загрузились
    """

    link_time = []

    while to_visit and args.max > len(visited):
        link = to_visit.pop()
        if link in visited:
            continue

        print(f"[{len(visited) + 1}] Проверка: {link}")

        try:
            driver.get(link)
            WebDriverWait(driver, TIMEOUT).until(lambda d: d.execute_script("return document.readyState") == "complete")
            to_visit.update(get_links())
            visited.add(link)
            link_time.append((link, get_page_load_time()))

        except WebDriverException as e:
            print(f"Ошибка при загрузке {link}: {e}")
            visited.add(link)
            link_time.append((link, -1))
            continue

    return sorted(link_time, key=lambda x: -x[1])


if __name__ == '__main__':
    result = pages_load_time_top()

    print(f"\n{'Время':<10} | {'Ссылка'}")
    print("-" * 40)

    for l, t in result:

        if t == -1:
            print(f"{'Ошибка':<9}  | {l}")

        else:
            print(f"{t:<6} сек | {l}")
