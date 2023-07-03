import requests
import time
import os
import hashlib
import random

from bs4 import BeautifulSoup
from jsona import Jsona


BASE_URL = 'https://www.lsr.ru'


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
        jsona_queue = Jsona(path_file=FOLDER_QUEUE, name_file=file).return_json()

        if jsona_queue.get('success'):
            jsona_data = Jsona(path_file=FOLDER_DATA, name_file=file).return_json()
            data_file = jsona_data.get('data', {})

            print('NEED UPDATE DATA')
        else:
            print('FLAT HAS BEEN SOLD')

    for file in os.listdir(FOLDER_QUEUE):
        jsona_queue = Jsona(path_file=FOLDER_QUEUE, name_file=file).return_json()

        print(f'NEED ADD NEW FLAT {jsona_queue["data"]["link"]}')
    
    print()

    


def main():
    while True:
        flats = get_all_flats()
        
        save_data_flats_queue(flats)

        process_flats()

        time.sleep(random.randint(30 * 60, 60 * 60))


if __name__ == '__main__':
    main()