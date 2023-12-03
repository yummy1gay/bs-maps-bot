#dev: @yummy1gay

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, InputMediaPhoto
from aiogram.utils import executor
from translate import Translator
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
from datetime import datetime

BOT_TOKEN = ''

EVENTS_ENDPOINT = "https://api.brawlapi.com/v1/events"
BRAWLERS_ENDPOINT = "https://api.brawlapi.com/v1/brawlers/{}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

async def get_active_solo_showdown():
    response = requests.get(EVENTS_ENDPOINT)

    if response.status_code == 200:
        data = response.json()

        for active_event in data["active"]:
            if active_event["slot"]["name"] == "Daily Showdown":
                return active_event
    return None

async def get_upcoming_solo_showdown():
    response = requests.get(EVENTS_ENDPOINT)

    if response.status_code == 200:
        data = response.json()

        for upcoming_event in data["upcoming"]:
            if upcoming_event["slot"]["name"] == "Daily Showdown":
                return upcoming_event
    return None

async def get_brawler_name(brawler_id):
    response = requests.get(BRAWLERS_ENDPOINT.format(brawler_id))

    if response.status_code == 200:
        brawler_data = response.json()
        return brawler_data.get("name", str(brawler_id))
    return str(brawler_id)


async def translate_to_russian(text):
    translator = Translator(to_lang="ru")
    translation = translator.translate(str(text))
    return translation

async def create_collage(current_image_url, upcoming_image_url):
    current_image = Image.open(requests.get(current_image_url, stream=True).raw)
    upcoming_image = Image.open(requests.get(upcoming_image_url, stream=True).raw)

    current_image = current_image.convert("RGBA")
    current_data = current_image.getdata()
    new_current_data = []
    for item in current_data:
        if item[3] != 0:
            new_current_data.append(item[:3] + (255,))
        else:
            new_current_data.append(item)
    current_image.putdata(new_current_data)
    current_image = current_image.convert("RGB")

    upcoming_image = upcoming_image.convert("RGBA")
    upcoming_data = upcoming_image.getdata()
    new_upcoming_data = []
    for item in upcoming_data:
        if item[3] != 0:
            new_upcoming_data.append(item[:3] + (255,))
        else:
            new_upcoming_data.append(item)
    upcoming_image.putdata(new_upcoming_data)
    upcoming_image = upcoming_image.convert("RGB")

    width, height = current_image.size

    collage = Image.new('RGB', (width * 2, height), (255, 255, 255))
    collage.paste(current_image, (0, 0))
    collage.paste(upcoming_image, (width, 0))

    collage = ImageOps.invert(ImageOps.invert(collage).crop(collage.getbbox()))

    return collage

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я бот, который отправляет информацию о предстоящей и текущей картах шд, отправь мне команду /info чтобы получить информацию")

@dp.message_handler(commands=['info'])
async def send_maps_info(message: types.Message):
    current_event = await get_active_solo_showdown()
    upcoming_event = await get_upcoming_solo_showdown()

    if current_event and upcoming_event:
        current_start_time = datetime.strptime(current_event['startTime'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d.%m")
        current_end_time = datetime.strptime(current_event['endTime'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d.%m")
        current_map_name_ru = await translate_to_russian(current_event['map']['name'])

        upcoming_start_time = datetime.strptime(upcoming_event['startTime'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d.%m")
        upcoming_end_time = datetime.strptime(upcoming_event['endTime'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d.%m")
        upcoming_map_name_ru = await translate_to_russian(upcoming_event['map']['name'])

        current_caption = (f"🌏 <b>Текущая карта шд:</b>\n\n"
                           f"📀 <b>Название:</b> <i>{current_map_name_ru}</i>\n"
                           f"🕘 <b>Начинается в:</b> <i>{current_start_time} 21:00</i>\n"
                           f"🕘 <b>Заканчивается в:</b> <i>{current_end_time} 21:00</i>\n"
                           f"🌟 <b>Топ-5 бравлеров: </b>")

        upcoming_caption = (f"😨 <b>Предстоящая карта шд:</b>\n\n"
                            f"💿 <b>Название:</b> <i>{upcoming_map_name_ru}</i>\n"
                            f"🕘 <b>Начинается в:</b> <i>{upcoming_start_time} 21:00</i>\n"
                            f"🕘 <b>Заканчивается в:</b> <i>{upcoming_end_time} 21:00</i>\n"
                            f"🌟 <b>Топ-5 бравлеров: </b>")

        current_image_url = current_event['map']['imageUrl']
        upcoming_image_url = upcoming_event['map']['imageUrl']

        top_brawlers_current = [await get_brawler_name(brawler_stat['brawler']) for brawler_stat in current_event['map']['stats'][:5]]
        top_brawlers_upcoming = [await get_brawler_name(brawler_stat['brawler']) for brawler_stat in upcoming_event['map']['stats'][:5]]

        top_brawlers_str_current = ", ".join(top_brawlers_current)
        top_brawlers_str_upcoming = ", ".join(top_brawlers_upcoming)

        combined_caption = (
            current_caption + f"{top_brawlers_str_current}\n\n" + upcoming_caption + f"{top_brawlers_str_upcoming}")

        collage = await create_collage(current_image_url, upcoming_image_url)

        image_byte_array = io.BytesIO()
        collage.save(image_byte_array, format='PNG')
        image_byte_array.seek(0)

        await bot.send_photo(message.chat.id, photo=image_byte_array, caption=combined_caption, parse_mode=ParseMode.HTML)

    else:
        await message.reply("Информация о картах не найдена.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
