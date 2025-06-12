import asyncio
from ps_store_checker import check_multiple_games_languages_md_async
from constants import REGIONS

async def main():
    # Игры для PS5
    ps5_games = [
        # "God of War Ragnarok",
        # "Spider-Man: Miles Morales",
        # "Death Stranding",
        # "Immortals Fenyx Rising",
        # "Grand Theft Auto V",
        "Horizon Zero Dawn",
        # "Horizon Forbidden West",
        "Days Gone",
    ]

    # Игры для PS4
    ps4_games = [
        # "Assassins Creed Origins",
        # "Detroit Become Human",
        "Days Gone",
        "Horizon Zero Dawn",
        # "Horizon Forbidden West",
    ]

    # Выбранные регионы для проверки
    selected_regions = ['en-pl', 'en-tr', 'uk-ua']

    # Проверяем игры для PS5
    await check_multiple_games_languages_md_async(
        ps5_games, 
        selected_regions, 
        "ps5", 
        "ru", 
        "ps5_games.md"
    )

    # Проверяем игры для PS4
    await check_multiple_games_languages_md_async(
        ps4_games, 
        selected_regions, 
        "ps4", 
        "ru", 
        "ps4_games.md"
    )

if __name__ == "__main__":
    asyncio.run(main())
