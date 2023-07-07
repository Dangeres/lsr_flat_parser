import requests
import time
import os
import hashlib
import random

from bs4 import BeautifulSoup
from jsona import Jsona


BASE_URL = 'https://www.lsr.ru'

jsona = Jsona('', 'settings.json')

settings = jsona.return_json().get('data', {})


FOLDER_DATA = 'data/'
FOLDER_QUEUE = 'queue/'


for path in [
    FOLDER_DATA,
    FOLDER_QUEUE,
]:
    os.makedirs(path, exist_ok = True)


def get_all_flats():
    result = []

    try:
        for page in range(1, 1000):
            req = requests.post(
                url='https://www.lsr.ru/ajax/search/msk/',
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
                }
            )

            response = req.json()

            soup = BeautifulSoup(response['html'], "html.parser")

            flats = soup.select('tr')

            if len(flats) == 0:
                break

            for flat in flats:
                url = ''.join(
                    [
                        BASE_URL,
                        (flat.select_one('a') or {}).get('href', '')
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

                data = {
                    'uid': hashlib.sha256(url.encode()).hexdigest(),
                    'link': url,
                    'name': name,
                    'object': build_obj,
                    'price': int(price),
                    'time': int(time.time()),
                }

                result.append(
                    data
                )

            time.sleep(random.uniform(1, 3))
    except Exception as e:
        print(e)

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
        print(e)


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
                try:
                    result = requests.post(
                        url = settings.get('host') + '/message',
                        json = {
                            'id': queue_file.get('uid'),
                            'sender': settings.get('sender'),
                            'text': '<a href="%s">%s</a> изменила цену.\nС %i на %i' % (
                                data_file['link'],
                                data_file['name'],
                                last_price,
                                queue_file.get('price'),
                            ),
                        }
                    )

                    if result.status_code == 200 and result.json().get('success'):
                        Jsona(path_file=FOLDER_DATA, name_file=file).save_json(data = data_file)
                        os.remove(FOLDER_QUEUE + file)

                        break
                except Exception as e:
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
                try:
                    result = requests.post(
                        url = settings.get('host') + '/message',
                        json = {
                            'id': data_file.get('uid'),
                            'sender': settings.get('sender'),
                            'text': '<a href="%s">%s</a> была продана.\nПоследняя цена %i' % (
                                data_file['link'],
                                data_file['name'],
                                last_price,
                            ),
                        }
                    )
                    
                    if result.status_code == 200 and result.json().get('success'):
                        Jsona(path_file=FOLDER_DATA, name_file=file).save_json(data = data_file)
                        break
                except Exception as e:
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
            'prices': [
                {
                    'price': queue_file.get('price'),
                    'time': queue_file.get('time'),
                }
            ],
        }

        while True:
            try:
                result = requests.post(
                    url = settings.get('host') + '/message',
                    json = {
                        'id': data_file.get('uid'),
                        'sender': settings.get('sender'),
                        'text': '<a href="%s">%s</a>\nЦена новопоявившейся квартиры %i' % (
                            data_file['link'],
                            data_file['name'],
                            data_file['last_price'],
                        ),
                    }
                )

                if result.status_code == 200 and result.json().get('success'):
                    Jsona(path_file=FOLDER_DATA, name_file=file).save_json(data = data_file)
                    os.remove(FOLDER_QUEUE + file)

                    break
            except Exception as e:
                time.sleep(random.uniform(1, 2))


def main():
    while True:
        flats = get_all_flats()
        
        save_data_flats_queue(flats)

        process_flats()

        time.sleep(random.randint(30 * 60, 60 * 60))


if __name__ == '__main__':
    main()