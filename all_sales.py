import os
import csv
import time
import datetime


from jsona import Jsona
from utils import (
    send_telegram,
    price_format,
    just_print,
)


jsona_settings = Jsona('', 'settings.json')

settings = jsona_settings.return_json().get('data', {})


def main():
    folder_path = 'data/'

    settings['send_telegram_message'] = False # TEMP

    sales = []

    for file in os.listdir(folder_path):
        if not file.endswith('.json'):
            continue

        jsn = Jsona(folder_path, file)

        data = jsn.return_json().get('data', {})

        if data.get('last_price') > -1:
            continue

        sales.append(
            {
                'price': data.get('prices', [])[-2]['price'],
                'time': data.get('prices', [])[-1]['time'],
                'object': data.get('object'),
                'floor': data.get('floor'),
                'link': data.get('link'),
                'image': data.get('image', ''),
                'name': data.get('name'),
                'size': data.get('size'),
                'uid': data.get('uid'),
            }
        )
        
        message_raw = '#недельные_изменения\n%s - %s\n\nЦена продажи %s\nДата продажи %s\n\n%s' % (
            data.get('object'),
            data.get('name'),
            price_format(data.get('prices', [])[-2]['price']),
            datetime.datetime.fromtimestamp(data.get('prices', [])[-1]['time']).strftime("%d.%m.%y %H:%M:%S"),
            data.get('uid'),
        )

        message_html = '#недельные_изменения\n<a href="%s">%s - %s</a>\n\nЦена продажи %s\nДата продажи %s\n\n<i>uid: %s</i>' % (
            data.get('link'),
            data.get('object'),
            data.get('name'),
            price_format(data.get('prices', [])[-2]['price']),
            datetime.datetime.fromtimestamp(data.get('prices', [])[-1]['time']).strftime("%d.%m.%y %H:%M:%S"),
            data.get('uid'),
        )

        while True:
            result = send_telegram(
                uid = data.get('uid'),
                message = message_html,
                host = settings.get('host'),
                sender = settings.get('sender'),
            ) if settings.get('send_telegram_message') else just_print(
                message = message_raw,
            )

            if result:
                break

        print('---')

    sales = sorted(sales, key = lambda x: (x['time'], x['price']))

    valid_dt = int(time.time()) - 14 * 86400

    with open('detail_info.csv', 'w', newline='') as csvfile:
        spamwriter = csv.writer(
            csvfile,
            delimiter=',',
        )
        
        spamwriter.writerow(['Цена', 'Время', 'Обьект', 'Этаж', 'ЭтажМ', 'Имя', 'Картинка', 'Размер', 'UID'])

        for data in sales:
            if data['time'] > valid_dt:
                break
            
            spamwriter.writerow([
                data['price'],
                datetime.datetime.fromtimestamp(data['time']).strftime("%d.%m.%y %H:%M:%S"),
                data.get('object'),
                data.get('floor')[0],
                data.get('floor')[1],
                data.get('name'),
                data.get('image'),
                data.get('size'),
                data.get('uid'),
            ])

    print()


if __name__ == '__main__':
    main()