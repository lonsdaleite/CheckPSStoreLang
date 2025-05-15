import time
import json
import re
import requests
from bs4 import BeautifulSoup


headers = {
    "User-Agent": "Mozilla/5.0"
}


def retry_request(func, *args, retries=5, delay=3, fallback=None):
    for attempt in range(1, retries + 1):
        try:
            return func(*args)
        except Exception as e:
            if attempt < retries:
                print(f"⚠️ Ошибка: {e}. Ретрай через {delay}с... (попытка {attempt}/{retries})")
                time.sleep(delay)
            else:
                print(f"❌ Ошибка: {e}. Пропускаем (после {retries} попыток)")
                return fallback

# Список ключевых "мусорных" типов (многоязычный, можно расширять)
TRASH_TYPES = [
    # Английский
    "virtual currency", "credits", "coins", "money", "pack", "item", "skin",
    "outfit", "weapon", "armor", "dlc", "add-on", "expansion", "season pass",
    "upgrade", "booster", "demo", "trial", "bundle only", "costume", "level",

    # Русский
    "валюта", "монеты", "кредиты", "скин", "скины", "набор", "предмет", "оружие",
    "броня", "дополнение", "доп контент", "доп. контент", "dlc", "бустер",
    "расширение", "обновление", "апгрейд", "только в составе набора", "демо",
    "пробная версия", "сезонный пропуск", "season pass", "уровень",

    # Немецкий
    "virtuelle währung", "credits", "münzen", "gegenstand", "kostüm",
    "waffe", "rüstung", "erweiterung", "zusatzinhalt", "addon", "booster",
    "aufwertung", "testversion", "probeversion", "nur im bundle", "season pass",
    "stufenpaket", "charakter", "level", "objekt",

    # Французский
    "monnaie virtuelle", "crédits", "pièces", "pack", "objet", "tenue",
    "arme", "armure", "extension", "contenu additionnel", "add-on",
    "amélioration", "booster", "mise à niveau", "démo", "version d'essai",
    "season pass", "essai gratuit", "niveau", "élément",

    "nivel",

    # Украинский
    "віртуальна валюта", "кредити", "монети", "пакет", "набір",
    "набір предметів", "предмет", "зброя", "доповнення", "додатковий контент",
    "dlc", "апґрейд", "покращення", "бустер", "розширення",
    "оновлення", "пробна версія", "демо", "сезонний пропуск", "season pass",
    "пропуск", "лише в складі набору", "тільки у складі пакета", "контент", "додаток",
    "тимчасовий доступ", "рівень", "рівня", "рівнів", "набір рівнів",
    "пакет рівнів", "додатковий рівень", "відкриття рівня", "розблокування рівня", "збільшення рівня",
    "підвищення рівня", "нові рівні",
]

def is_card_game(card):
    # Находим product-type, если есть
    tag = card.find("span", class_="psw-product-tile__product-type")
    if not tag:
        return True  # Нет типа — скорее всего, игра
    type_text = tag.text.strip().lower()

    # print(card.get_text())
    # print(type_text)
    for trash in TRASH_TYPES:
        if trash in type_text:
            return False  # Тип явно мусорный
    return True  # Тип есть, но он не мусорный → оставляем


def search_game(region, query, platform):
    url = f"https://store.playstation.com/{region}/search/{query.lower().replace(' ', '%20').replace('-', '%20')}"
    # print(url)
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Получаем максимум 5 карточек
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
    resp = requests.get(game_url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
    if not script_tag:
        raise Exception("❌ JSON-блок __NEXT_DATA__ не найден")

    text = script_tag.string.replace('\\"', '"')

    # Найдём ВСЕ вложенные JSON-строки, содержащие нужные типы
    voice_jsons = re.findall(r'\{[^{}]*"__typename":"SpokenLanguagesByPlatformElement"[^{}]*\}', text)
    sub_jsons   = re.findall(r'\{[^{}]*"__typename":"ScreenLanguagesByPlatformElement"[^{}]*\}', text)

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
            print(f"⚠️ Ошибка при парсинге блока: {e}")

    for j in voice_jsons:
        parse_json_block(j, "spokenLanguages", "voice")

    for j in sub_jsons:
        parse_json_block(j, "screenLanguages", "subs")

    return result

def yesno_md(x):
    return "✅" if x else "❌"

def check_single_game_language_for_region_md(game_query, region, platform='ps5', lang_code='ru'):
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

def check_multiple_games_languages_md(games, regions, platform='ps5', lang_code='ru', output_file='output.md'):
    header = f"### 🎮 Проверка языков для игр (язык: {lang_code})\n\n"
    table_header = (
        f"| Игра | Регион | {platform.upper()} | Озв. | Суб. | URL |\n"
        "|------|--------|-----|------|------|-----|\n"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(table_header)

        print(header.strip())
        print(table_header.strip())

        for game in games:
            for region in regions:
                row = check_single_game_language_for_region_md(game, region, platform, lang_code)
                row_str = f"| {' | '.join(row)} |\n"
                f.write(row_str)
                print(row_str.strip())


regions = [
    'es-ar',   # Argentina
    'en-au',   # Australia
    'de-at',   # Austria
    'en-bh',   # Bahrain
    'fr-be',   # Belgium
    'es-bo',   # Bolivia
    'pt-br',   # Brazil
    'bg-bg',   # Bulgaria
    'en-ca',   # Canada
    'es-cl',   # Chile
    'es-co',   # Colombia
    'es-cr',   # Costa Rica
    'en-hr',   # Croatia
    'en-cy',   # Cyprus
    'cs-cz',   # Czech Republic
    'da-dk',   # Denmark
    'es-ec',   # Ecuador
    'es-sv',   # El Salvador
    'fi-fi',   # Finland
    'fr-fr',   # France
    'de-de',   # Germany
    'el-gr',   # Greece
    'es-gt',   # Guatemala
    'es-hn',   # Honduras
    'en-hk',   # Hong Kong
    'en-hu',   # Hungary
    'en-is',   # Iceland
    'en-in',   # India
    'en-id',   # Indonesia
    'en-ie',   # Ireland
    'en-il',   # Israel
    'it-it',   # Italy
    'ja-jp',   # Japan
    'ko-kr',   # Korea
    'en-kw',   # Kuwait
    'en-lb',   # Lebanon
    'fr-lu',   # Luxembourg
    'en-my',   # Malaysia
    'en-mt',   # Malta
    'es-mx',   # Mexico
    'nl-nl',   # Netherlands
    'en-nz',   # New Zealand
    'es-ni',   # Nicaragua
    'en-no',   # Norway
    'en-om',   # Oman
    'es-pa',   # Panama
    'es-py',   # Paraguay
    'es-pe',   # Peru
    'en-pl',   # Poland
    'pt-pt',   # Portugal
    'en-qa',   # Qatar
    'en-ro',   # Romania
    # 'ru-ru',   # Russia
    'en-sa',   # Saudi Arabia
    'en-sg',   # Singapore
    'en-si',   # Slovenia
    'en-sk',   # Slovakia
    'en-za',   # South Africa
    'es-es',   # Spain
    'sv-se',   # Sweden
    'de-ch',   # Switzerland
    'zh-tw',   # Taiwan
    'th-th',   # Thailand
    'en-tr',   # Turkey
    'uk-ua',   # Ukraine
    'en-ae',   # UAE
    'en-us',   # United States
    'en-gb',   # United Kingdom
    'es-uy',   # Uruguay
]

regions = ['de-de', 'en-gb', 'en-in', 'en-pl', 'en-tr', 'uk-ua', 'en-us']

games = ["God of War Ragnarok", "Spider-Man: Miles Morales", "Death Stranding", "Immortals Fenyx Rising", "Grand Theft Auto V", "Horizon Zero Dawn", "Horizon Forbidden West"]
check_multiple_games_languages_md(games, regions, "ps5", "ru")

games = ["Assassins Creed Origins", "Detroit Become Human", "Days Gone", "Horizon Zero Dawn", "Horizon Forbidden West"]
check_multiple_games_languages_md(games, regions, "ps4", "ru")
