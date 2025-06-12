import asyncio
import json
import logging
import re
import time
from typing import List, Dict, Optional, Any

import aiohttp
import requests
from bs4 import BeautifulSoup

from constants import (
    get_random_headers, HEADERS, REQUEST_TIMEOUT, RETRY_ATTEMPTS, RETRY_DELAY,
    TRASH_TYPES, MAX_PARALLEL_REQUESTS
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def retry_request_async(func, *args, retries=RETRY_ATTEMPTS, delay=RETRY_DELAY, fallback=None):
    # Асинхронная версия функции повторных попыток с экспоненциальной задержкой
    for attempt in range(1, retries + 1):
        try:
            return await func(*args)
        except Exception as e:
            if attempt < retries:
                logger.warning(f"⚠️ Ошибка: {e}. Ретрай через {delay}с... (попытка {attempt}/{retries})")
                await asyncio.sleep(delay)
            else:
                logger.error(f"❌ Ошибка: {e}. Пропускаем (после {retries} попыток)")
                return fallback
    return None


def is_card_game(card):
    # Проверяет, является ли карточка товара игрой (не DLC, валюта и т.д.).
    # Находим product-type, если есть
    tag = card.find("span", class_="psw-product-tile__product-type")
    if not tag:
        return True  # Нет типа — скорее всего, игра
    type_text = tag.text.strip().lower()

    for trash in TRASH_TYPES:
        if trash in type_text:
            return False  # Тип явно мусорный
    return True  # Тип есть, но он не мусорный → оставляем


async def search_game_async(session: aiohttp.ClientSession, region: str, query: str, platform: str) -> Optional[str]:
    # Асинхронная версия поиска игры в PS Store
    url = f"https://store.playstation.com/{region}/search/{query.lower().replace(' ', '%20').replace('-', '%20')}"
    logger.info(f"🔍 Поиск игры: {url}")

    headers = get_random_headers()
    async with session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as resp:
        text = await resp.text()
        soup = BeautifulSoup(text, "html.parser")

        # Получаем максимум 20 карточек
        product_cards = soup.select('a[href*="/product/"]')[:20]
        candidates = []

        for a_tag in product_cards:
            href = a_tag.get("href", "")
            full_url = "https://store.playstation.com" + href
            text = a_tag.get_text()

            if "unavailable" in text.lower() or "pre-order" in text.lower() or "announced" in text.lower():
                continue

            if not text.lower().strip().startswith("ps5") and not text.lower().strip().startswith("ps4"):
                continue

            if not is_card_game(a_tag):
                continue

            candidates.append((text, full_url))

        # Ищем карточку с упоминанием и ps4/ps5
        for text, url in candidates:
            if platform.lower() in text.lower():
                return url

        return None


async def get_languages_async(session: aiohttp.ClientSession, game_url: str) -> Dict[str, List[str]]:
    # Асинхронная версия получения языков игры
    headers = get_random_headers()
    async with session.get(game_url, headers=headers, timeout=REQUEST_TIMEOUT) as resp:
        text = await resp.text()
        soup = BeautifulSoup(text, "html.parser")

        script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script_tag:
            raise Exception("❌ JSON-блок __NEXT_DATA__ не найден")

        text = script_tag.string.replace('\\"', '"')

        # Найдём ВСЕ вложенные JSON-строки, содержащие нужные типы
        voice_jsons = re.findall(r'\{[^{}]*"__typename":"SpokenLanguagesByPlatformElement"[^{}]*\}', text)
        sub_jsons = re.findall(r'\{[^{}]*"__typename":"ScreenLanguagesByPlatformElement"[^{}]*\}', text)

        result = {
            'ps5_voice': [],
            'ps5_subs': [],
            'ps4_voice': [],
            'ps4_subs': [],
        }

        def parse_json_block(raw, field, prefix):
            try:
                data = json.loads(raw)
                platform = data.get("platform", "").lower()
                if platform in ["ps4", "ps5"]:
                    result[f"{platform}_{prefix}"] = data.get(field, [])
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при парсинге блока: {e}")

        for j in voice_jsons:
            parse_json_block(j, "spokenLanguages", "voice")

        for j in sub_jsons:
            parse_json_block(j, "screenLanguages", "subs")

        return result


def yesno_md(x):
    # Конвертирует булево значение в markdown-галочку.
    return "✅" if x else "❌"


async def check_single_game_language_for_region_md_async(
        session: aiohttp.ClientSession,
        game_query: str,
        region: str,
        platform: str = 'ps5',
        lang_code: str = 'ru'
) -> None | list[str] | list[str | None | Any]:
    # Асинхронная версия проверки языка для одной игры в одном регионе
    url = await retry_request_async(
        search_game_async,
        session,
        region,
        game_query,
        platform
    )

    if not url:
        return [game_query, region.split('-')[-1].upper()] + ["❌"] * 6 + ["Игра не найдена или ошибка запроса"]

    langs = await retry_request_async(get_languages_async, session, url)
    if not langs:
        return [game_query, region.split('-')[-1].upper()] + ["Ошибка"] * 6 + ["Не удалось получить языки"]

    has_ps5 = bool(langs['ps5_voice'] or langs['ps5_subs'])
    has_ps4 = bool(langs['ps4_voice'] or langs['ps4_subs'])

    if platform.lower() == "ps5":
        return [
            game_query,
            region.split('-')[-1].upper(),
            yesno_md(has_ps5),
            yesno_md(lang_code in langs['ps5_voice']),
            yesno_md(lang_code in langs['ps5_subs']),
            url
        ]
    if platform.lower() == "ps4":
        return [
            game_query,
            region.split('-')[-1].upper(),
            yesno_md(has_ps4),
            yesno_md(lang_code in langs['ps4_voice']),
            yesno_md(lang_code in langs['ps4_subs']),
            url
        ]
    return None


async def check_multiple_games_languages_md_async(
        games: List[str],
        regions: List[str],
        platform: str = 'ps5',
        lang_code: str = 'ru',
        output_file: str = 'output.md',
        max_parallel_requests: int = MAX_PARALLEL_REQUESTS
) -> None:
    # Асинхронная версия проверки языков для нескольких игр
    header = f"### 🎮 Проверка языков для игр (язык: {lang_code})\n\n"
    table_header = (
        f"| Игра | Регион | {platform.upper()} | Озв. | Суб. | URL |\n"
        "|------|--------|-----|------|------|-----|\n"
    )

    # Создаем файл и записываем заголовки
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(table_header)

    logger.info(header.strip())
    logger.info(table_header.strip())

    # Создаем семафор для ограничения параллельных запросов
    semaphore = asyncio.Semaphore(max_parallel_requests)

    async def process_game_region(game: str, region: str):
        async with semaphore:
            return await check_single_game_language_for_region_md_async(
                session,
                game,
                region,
                platform,
                lang_code
            )

    async with aiohttp.ClientSession() as session:
        tasks = []
        for game in games:
            for region in regions:
                tasks.append(process_game_region(game, region))

        # Запускаем все задачи параллельно
        results = await asyncio.gather(*tasks)

        # Записываем результаты в файл
        for result in results:
            if result:
                row_str = f"| {' | '.join(result)} |\n"
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(row_str)
                logger.info(row_str.strip())


# Оставляем синхронные версии для обратной совместимости
def retry_request(func, *args, retries=RETRY_ATTEMPTS, delay=RETRY_DELAY, fallback=None):
    # Повторная попытка вызова функции с экспоненциальной задержкой.
    for attempt in range(1, retries + 1):
        try:
            return func(*args)
        except Exception as e:
            if attempt < retries:
                logger.warning(f"⚠️ Ошибка: {e}. Ретрай через {delay}с... (попытка {attempt}/{retries})")
                time.sleep(delay)
            else:
                logger.error(f"❌ Ошибка: {e}. Пропускаем (после {retries} попыток)")
                return fallback
    return None


def search_game(region, query, platform):
    # Ищет игру в PS Store и возвращает её URL.
    url = f"https://store.playstation.com/{region}/search/{query.lower().replace(' ', '%20').replace('-', '%20')}"
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Получаем максимум 20 карточек
    product_cards = soup.select('a[href*="/product/"]')[:20]
    candidates = []

    for a_tag in product_cards:
        href = a_tag.get("href", "")
        full_url = "https://store.playstation.com" + href
        text = a_tag.get_text()

        if "unavailable" in text.lower() or "pre-order" in text.lower() or "announced" in text.lower():
            continue

        if not text.lower().strip().startswith("ps5") and not text.lower().strip().startswith("ps4"):
            continue

        if not is_card_game(a_tag):
            continue

        candidates.append((text, full_url))

    # Ищем карточку с упоминанием и ps4/ps5
    for text, url in candidates:
        if platform.lower() in text.lower():
            return url

    return None


def get_languages(game_url):
    # Получает доступные языки для игры.
    resp = requests.get(game_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    soup = BeautifulSoup(resp.text, "html.parser")

    script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
    if not script_tag:
        raise Exception("❌ JSON-блок __NEXT_DATA__ не найден")

    text = script_tag.string.replace('\\"', '"')

    # Найдём ВСЕ вложенные JSON-строки, содержащие нужные типы
    voice_jsons = re.findall(r'\{[^{}]*"__typename":"SpokenLanguagesByPlatformElement"[^{}]*\}', text)
    sub_jsons = re.findall(r'\{[^{}]*"__typename":"ScreenLanguagesByPlatformElement"[^{}]*\}', text)

    result = {
        'ps5_voice': [],
        'ps5_subs': [],
        'ps4_voice': [],
        'ps4_subs': [],
    }

    def parse_json_block(raw, field, prefix):
        try:
            data = json.loads(raw)
            platform = data.get("platform", "").lower()
            if platform in ["ps4", "ps5"]:
                result[f"{platform}_{prefix}"] = data.get(field, [])
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при парсинге блока: {e}")

    for j in voice_jsons:
        parse_json_block(j, "spokenLanguages", "voice")

    for j in sub_jsons:
        parse_json_block(j, "screenLanguages", "subs")

    return result


def check_single_game_language_for_region_md(game_query, region, platform='ps5', lang_code='ru'):
    # Проверяет наличие языка для одной игры в одном регионе.
    url = retry_request(search_game, region, game_query, platform)
    if not url:
        return [game_query, region.split('-')[-1].upper()] + ["❌"] * 6 + ["Игра не найдена или ошибка запроса"]

    langs = retry_request(get_languages, url)
    if not langs:
        return [game_query, region.split('-')[-1].upper()] + ["Ошибка"] * 6 + ["Не удалось получить языки"]

    has_ps5 = bool(langs['ps5_voice'] or langs['ps5_subs'])
    has_ps4 = bool(langs['ps4_voice'] or langs['ps4_subs'])

    if platform.lower() == "ps5":
        return [
            game_query,
            region.split('-')[-1].upper(),
            yesno_md(has_ps5),
            yesno_md(lang_code in langs['ps5_voice']),
            yesno_md(lang_code in langs['ps5_subs']),
            url
        ]
    if platform.lower() == "ps4":
        return [
            game_query,
            region.split('-')[-1].upper(),
            yesno_md(has_ps4),
            yesno_md(lang_code in langs['ps4_voice']),
            yesno_md(lang_code in langs['ps4_subs']),
            url
        ]
    return None


def check_multiple_games_languages_md(games, regions, platform='ps5', lang_code='ru', output_file='output.md'):
    # Проверяет наличие языков для нескольких игр в нескольких регионах.
    header = f"### 🎮 Проверка языков для игр (язык: {lang_code})\n\n"
    table_header = (
        f"| Игра | Регион | {platform.upper()} | Озв. | Суб. | URL |\n"
        "|------|--------|-----|------|------|-----|\n"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(table_header)

        logger.info(header.strip())
        logger.info(table_header.strip())

        for game in games:
            for region in regions:
                row = check_single_game_language_for_region_md(game, region, platform, lang_code)
                row_str = f"| {' | '.join(row)} |\n"
                f.write(row_str)
                logger.info(row_str.strip())
