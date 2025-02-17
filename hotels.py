import requests
import os
from datetime import datetime, timedelta

# Ключ API RapidAPI из переменной окружения
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

async def search_hotels(city: str, check_in: str, price_per_night: int):
    try:
        check_in_date = datetime.strptime(check_in, "%d.%m").strftime("%Y-%m-%d")

        url = "https://hotels4.p.rapidapi.com/properties/list"
        querystring = {
            "destination": city,
            "checkIn": check_in_date,
            "checkOut": (datetime.strptime(check_in, "%d.%m") + timedelta(days=1)).strftime("%Y-%m-%d"),
            "adults1": "1",
            "priceMin": str(int(price_per_night * 0.8)),
            "priceMax": str(int(price_per_night * 1.2)),
            "sortOrder": "PRICE",
            "locale": "ru_RU",
            "currency": "RUB",
            "pageNumber": "1",
            "pageSize": "5"
        }
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
        }

        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()

        if "data" not in data or "body" not in data["data"] or "searchResults" not in data["data"]["body"]:
            return "Отели не найдены. Попробуйте изменить параметры поиска."

        hotels = data["data"]["body"]["searchResults"]["results"]
        if not hotels:
            return "Отели не найдены. Попробуйте изменить параметры поиска."

        result = "🏨 Найденные отели:\n\n"
        for hotel in hotels:
            name = hotel.get("name", "Название не указано")
            price = hotel.get("ratePlan", {}).get("price", {}).get("current", "Цена не указана")
            address = hotel.get("address", {}).get("streetAddress", "Адрес не указан")
            stars = hotel.get("starRating", "Рейтинг не указан")
            photo_url = await get_hotel_photo(hotel.get("id"))

            result += (
                f"🔹 {name}\n"
                f"⭐ Рейтинг: {stars}\n"
                f"💵 Цена за ночь: {price}\n"
                f"📍 Адрес: {address}\n"
            )
            if photo_url:
                result += f"📸 Фото: {photo_url}\n"
            result += "\n"

        return result

    except Exception as e:
        return f"Произошла ошибка при поиске отелей: {e}"

async def get_hotel_photo(hotel_id: str):
    try:
        url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
        querystring = {"id": hotel_id}
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
        }
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()

        if "hotelImages" in data and len(data["hotelImages"]) > 0:
            return data["hotelImages"][0].get("baseUrl", "").format(size="b")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении фото отеля: {e}")
        return None