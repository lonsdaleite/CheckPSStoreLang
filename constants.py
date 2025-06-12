import random
from typing import Dict

# Maximum number of parallel requests
MAX_PARALLEL_REQUESTS = 2

# Список User-Agent для ротации
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def get_random_headers() -> Dict[str, str]:
    # Генерирует случайные заголовки для запроса
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }

# HTTP-заголовки для запросов (устаревшие, используйте get_random_headers())
HEADERS = get_random_headers()

# Таймаут запросов в секундах
REQUEST_TIMEOUT = 5

# Настройки повторных попыток
RETRY_ATTEMPTS = 5
RETRY_DELAY = 3

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

# Доступные регионы
REGIONS = [
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
