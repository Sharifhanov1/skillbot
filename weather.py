import aiohttp
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

async def get_weather(city: str):
    try:
        async with aiohttp.ClientSession() as session:
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
            async with session.get(weather_url) as response:
                weather_data = await response.json()

                if weather_data.get("cod") != 200:
                    return "Город не найден. Пожалуйста, проверьте название и попробуйте снова.", None

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

                return weather_info, None  # Фото можно добавить позже

    except Exception as e:
        return f"Произошла ошибка при получении данных о погоде: {e}", None