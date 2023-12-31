import requests
import datetime
import time
import os
import sys
import logging
import hashlib
import random

from bs4 import BeautifulSoup
from jsona import Jsona
from utils import price_format, send_telegram, just_print


BASE_URL = 'https://www.lsr.ru'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

my_uid = [
    'a1d68c2b187d1ab123672f0c9860453d94285bacbe89b32859caf2ac8291b577', # 2279
    '18f1ea156ff67b334746edbadd7f3da9ac1ec11a9a3d9c0e2848d9437bec4570', # 2272
]

jsona_settings = Jsona('', 'settings.json')
jsona_system = Jsona('', 'settings_system.json')

settings = jsona_settings.return_json().get('data', {})
settings_system = jsona_system.return_json().get('data', {'time': int(time.time())})


FOLDER_DATA = 'data/'
FOLDER_QUEUE = 'queue/'
FOLDER_ERRORS = 'errors/'


for path in [
    FOLDER_DATA,
    FOLDER_QUEUE,
    FOLDER_ERRORS,
]:
    os.makedirs(path, exist_ok = True)


def get_all_flats():
    result = []
    page = 1

    try:
        while True:
            while True:
                try:
                    req = requests.post(
                        url=BASE_URL + '/ajax/search/msk/',
                        headers={
                            'Accept': 'application/json, text/javascript, */*; q=0.01',
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-Requested-With': 'XMLHttpRequest',
                            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.806 YaBrowser/23.11.2.806 Yowser/2.5 Safari/537.36',
                        },
                        params={
                            'price[min]': '',
                            'price[max]': '',
                            'area[min]': '',
                            'area[max]': '',
                            'floor[min]': '',
                            'floor[max]': '',
                            'location[]': 'district_19',
                            'last_delivery': 30,
                            'flattype[flat]': 'on',
                            'mortgage_type': 3,
                            'mortgage_payment': '',
                            'mortgage_time:': '',
                            '__s': '',
                            'ob[page]': page,
                            'ob[id]': 52,
                            'ob[sort]': 'price',
                            'ob[order]': 'asc',
                            'a': 'flats',
                            'object': 52,
                            '__s': '',
                        },
                        # verify = False,
                    )

                    response = req.json()

                    soup = BeautifulSoup(response['html'], "html.parser")

                    flats = soup.select('tr.b-building_type_inner-flat')

                    break
                except Exception as e:
                    time.sleep(random.uniform(1, 4))
                    logger.error(e)

            if len(flats) == 0:
                break

            for flat in flats:
                url = ''.join(
                    [
                        BASE_URL,
                        '/%s/' % (
                            (flat.select_one('a') or {}).get('href', '').strip('/'),
                        ),
                    ]
                )

                name = getattr(flat.select_one('a'), 'text', '').strip()
                price = getattr(flat.select_one('.b-building__price'), 'next', '').strip().replace(' ', '').replace('руб.', '')

                temp_name = []

                for i in flat.select_one('.b-building__object').contents:
                    if isinstance(i, str):
                        temp_name.append(
                            i.strip()
                        )

                build_obj = ' '.join(temp_name)
                floor = list(map(int, flat.select('div.b-buliding__flat-info-val')[0].text.strip().split(' / ')))
                size = float(flat.select('div.b-buliding__flat-info-val')[1].text.strip().replace('\xa0м²', ''))
                image = BASE_URL + flat.select_one('img.b-building__plan').attrs.get('data-src')

                type_decor = flat.select('.b-building__flat-decor')[0].text.strip().replace('\xa0', ' ')
                type_furnish = flat.select('.b-building__flat-decor')[1].text.strip().replace('\xa0', ' ')

                data = {
                    'uid': hashlib.sha256(url.encode()).hexdigest(),
                    'link': url,
                    'name': name,
                    'size': size,
                    'floor': floor,
                    'object': build_obj,
                    'price': int(price),
                    'type_decor': type_decor,
                    'type_furnish': type_furnish,
                    'image': image,
                    'time': int(time.time()),
                }

                result.append(
                    data
                )

            page += 1

            time.sleep(random.uniform(0.1, 0.7))
    except Exception as e:
        logger.error(e)

    return result


def save_data_flats_queue(flats):
    try:
        for data in flats:
            jsona = Jsona(
                path_file=FOLDER_QUEUE,
                name_file=f'{data["uid"]}.json'
            )

            jsona.save_json(
                data = data,
            )
    except Exception as e:
        logger.error(e)


def process_flats():
    for file in os.listdir(FOLDER_DATA):
        if not file.endswith('.json'):
            continue
        
        jsona_queue = Jsona(path_file=FOLDER_QUEUE, name_file=file).return_json()
        jsona_data = Jsona(path_file=FOLDER_DATA, name_file=file).return_json()

        if jsona_queue.get('success'):
            data_file = jsona_data.get('data')
            queue_file = jsona_queue.get('data')

            last_price = data_file['last_price']

            for tag in [
                'image',
                'type_decor',
                'type_furnish',
            ]:
                if data_file.get(tag) == queue_file.get(tag):
                    continue

                data_file[tag] = queue_file[tag]

                Jsona(path_file=FOLDER_DATA, name_file=file).save_json(data = data_file)

            if last_price == queue_file.get('price'):
                continue

            data_file['last_price'] = queue_file.get('price')

            data_file['prices'].append(
                {
                    'price': queue_file.get('price'),
                    'time': queue_file.get('time'),
                }
            )

            while True:
                if last_price == -1:
                    prev_last_price = price_format(data_file['prices'][-3]['price']) if len(data_file['prices']) > 2 else 'Неизвестно'

                    flat_type = (data_file.get('image', '').split('/')[-1].split('-') or ['unknown'])[0]

                    message_html = 'Обьект: %s\n\nНазвание: <a href="%s">%s</a>\nТип квартиры: <a href="%s">%s (планировка)</a>\n\nСообщение: пропадала с продажи но вернулась.\nЦена до продажи %s\nТекущая цена %s\n\n<i>uid: %s</i>' % (
                        data_file['object'],
                        data_file['link'],
                        data_file['name'],
                        data_file.get('image'),
                        flat_type,
                        prev_last_price,
                        price_format(queue_file.get('price')),
                        queue_file.get('uid'),
                    )

                    message_raw = '%s %s пропадала с продажи но вернулась.\nЦена до продажи %s\nТекущая цена %s\n\nuid: %s' % (
                        data_file['name'],
                        data_file['link'],
                        prev_last_price,
                        price_format(queue_file.get('price')),
                        queue_file.get('uid'),
                    )
                
                else:
                    flat_type = (data_file.get('image', '').split('/')[-1].split('-') or ['unknown'])[0]

                    message_html = 'Обьект: %s\n\nНазвание: <a href="%s">%s</a>\nТип квартиры: <a href="%s">%s (планировка)</a>\n\nСообщение: изменила цену с %s на %s\n\n<i>uid: %s</i>' % (
                        data_file['object'],
                        data_file['link'],
                        data_file['name'],
                        data_file.get('image'),
                        flat_type,
                        price_format(last_price),
                        price_format(queue_file.get('price')),
                        queue_file.get('uid'),
                    )

                    message_raw = 'Изменение цены %s %s\nС %s на %s\n\nuid: %s' % (
                        data_file['name'],
                        data_file['link'],
                        price_format(last_price),
                        price_format(queue_file.get('price')),
                        queue_file.get('uid'),
                    )

                result = send_telegram(
                    uid = queue_file.get('uid'),
                    message = message_html,
                    host = settings.get('host'),
                    sender = settings.get('sender'),
                    token = settings.get('token'),
                ) if settings.get('send_telegram_message') else just_print(
                    message = message_raw,
                )

                result2 = True
                
                if queue_file.get('uid') in my_uid:
                    result2 = send_telegram(
                        uid = queue_file.get('uid'),
                        message = 'Дополнительное уведомление по квартире (изменение цены) <a href="%s">ссылка</a>\n%s"' % (
                            data_file['link'],
                            queue_file.get('uid'),
                        ),
                        host = settings.get('host'),
                        sender = 'yablokov',
                        token = settings.get('token'),
                    )

                if result and result2:
                    Jsona(path_file=FOLDER_DATA, name_file=file).save_json(data = data_file)
                    os.remove(FOLDER_QUEUE + file)

                    break
                else:
                    time.sleep(random.uniform(1, 2))
        
        else:
            data_file = jsona_data.get('data')

            last_price = data_file['last_price']

            if last_price == -1:
                continue

            data_file['last_price'] = -1

            data_file['prices'].append(
                {
                    'price': -1,
                    'time': int(time.time()),
                }
            )

            while True:
                flat_type = (data_file.get('image', '').split('/')[-1].split('-') or ['unknown'])[0]

                message_html = 'Обьект: %s\n\nНазвание: <a href="%s">%s</a>\nТип квартиры: <a href="%s">%s (планировка)</a>\n\nСообщение: была забронирована(скоро подписание договоров).\nПоследняя цена %s\n\n<i>uid: %s</i>' % (
                    data_file['object'],
                    data_file['link'],
                    data_file['name'],
                    data_file.get('image'),
                    flat_type,
                    price_format(last_price),
                    data_file.get('uid'),
                )

                message_raw = 'Продажа %s %s\nПоследняя цена %s\n\nuid: %s' % (
                    data_file['name'],
                    data_file['link'],
                    price_format(last_price),
                    data_file.get('uid'),
                )

                result = send_telegram(
                    uid = data_file.get('uid'),
                    message = message_html,
                    host = settings.get('host'),
                    sender = settings.get('sender'),
                    token = settings.get('token'),
                ) if settings.get('send_telegram_message') else just_print(
                    message = message_raw,
                )

                result2 = True

                if data_file.get('uid') in my_uid:
                    result2 = send_telegram(
                        uid = data_file.get('uid'),
                        message = 'Дополнительное уведомление по квартире (ПРОДАЖА квартиры) <a href="%s">ссылка</a>\n%s"' % (
                            data_file['link'],
                            data_file.get('uid'),
                        ),
                        host = settings.get('host'),
                        sender = 'yablokov',
                        token = settings.get('token'),
                    )
                
                if result and result2:
                    Jsona(path_file=FOLDER_DATA, name_file=file).save_json(data = data_file)
                    break
                else:
                    time.sleep(random.uniform(1, 2))

    for file in os.listdir(FOLDER_QUEUE):
        if not file.endswith('.json'):
            continue

        jsona_queue = Jsona(path_file=FOLDER_QUEUE, name_file=file).return_json()
        jsona_data = Jsona(path_file=FOLDER_DATA, name_file=file).return_json()

        if jsona_data.get('success'):
            os.remove(FOLDER_QUEUE + file)
            continue

        queue_file = jsona_queue.get('data')
        
        data_file = {
            'uid': queue_file.get('uid'),
            'object': queue_file.get('object'),
            'name': queue_file.get('name'),
            'link': queue_file.get('link'),
            'last_price': queue_file.get('price'),
            'size': queue_file.get('size'),
            'floor': queue_file.get('floor'),
            'image': queue_file.get('image'),
            'type_decor': queue_file.get('type_decor'),
            'type_furnish': queue_file.get('type_furnish'),
            'prices': [
                {
                    'price': queue_file.get('price'),
                    'time': queue_file.get('time'),
                }
            ],
        }

        while True:
            flat_type = (data_file.get('image', '').split('/')[-1].split('-') or ['unknown'])[0]

            message_html = 'Обьект: %s\n\nНазвание: <a href="%s">%s</a>\nТип квартиры: <a href="%s">%s (планировка)</a>\n\nСообщение: появилась новая квартира по цене %s\n\n<i>uid: %s</i>' % (
                data_file['object'],
                data_file['link'],
                data_file['name'],
                data_file.get('image'),
                flat_type,
                price_format(data_file['last_price']),
                queue_file.get('uid'),
            )

            message_raw = 'Появилась %s %s\nЦена %s\n\nuid: %s' % (
                data_file['name'],
                data_file['link'],
                price_format(data_file['last_price']),
                queue_file.get('uid'),
            )

            result = send_telegram(
                uid = queue_file.get('uid'),
                message = message_html,
                host = settings.get('host'),
                sender = settings.get('sender'),
                token = settings.get('token'),
            ) if settings.get('send_telegram_message') else just_print(
                message = message_raw,
            )
            
            if result:
                Jsona(path_file=FOLDER_DATA, name_file=file).save_json(data = data_file)
                os.remove(FOLDER_QUEUE + file)

                break
            else:
                time.sleep(random.uniform(1, 2))


def tick():
    logger.info('Начинаем получать квартиры....')

    flats = get_all_flats()

    logger.info('Квартиры были получены')
    
    save_data_flats_queue(flats)
    
    logger.info('Квартиры были обработаны')

    process_flats()


def main():
    while not settings.get('use_cron', False):
        now_time = int(time.time())

        sleep_time = max(settings_system['time'] - now_time, 0)

        logger.info(f'Спим {sleep_time} секунд.\nВремя: {datetime.datetime.fromtimestamp(settings_system["time"]).strftime("%d.%m.%y %H:%M:%S")}')

        time.sleep(sleep_time)

        tick()

        settings_system['time'] = int(time.time()) + settings['await_time']

        jsona_system.save_json(data = settings_system, ident=4)


    if settings.get('use_cron', False):
        tick()


if __name__ == '__main__':
    main()