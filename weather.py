import requests
import os
from telegram import InputMediaPhoto

# Ключи API из переменных окружения
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY")

async def get_weather(city: str):
    try:
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()

        if weather_data.get("cod") != 200:
            return "Город не найден. Пожалуйста, проверьте название и попробуйте снова."

        temperature = weather_data["main"]["temp"]
        feels_like = weather_data["main"]["feels_like"]
        humidity = weather_data["main"]["humidity"]
        wind_speed = weather_data["wind"]["speed"]
        weather_description = weather_data["weather"][0]["description"]
        city_name = weather_data["name"]
        country = weather_data["sys"]["country"]

        weather_info = (
            f"🌍 Место: {city_name}, {country}\n"
            f"🌡️ Температура: {temperature}°C (ощущается как {feels_like}°C)\n"
            f"💧 Влажность: {humidity}%\n"
            f"🌬️ Скорость ветра: {wind_speed} м/с\n"
            f"☁️ Погода: {weather_description.capitalize()}"
        )

        photo_url = await get_place_photo(city_name)
        return weather_info, photo_url

    except Exception as e:
        return f"Произошла ошибка при получении данных о погоде: {e}", None

async def get_place_photo(city: str):
    try:
        unsplash_url = f"https://api.unsplash.com/search/photos?query={city}&client_id={UNSPLASH_API_KEY}&per_page=1"
        unsplash_response = requests.get(unsplash_url)
        unsplash_data = unsplash_response.json()

        if unsplash_data.get("results"):
            return unsplash_data["results"][0]["urls"]["regular"]
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении фото: {e}")
        return None