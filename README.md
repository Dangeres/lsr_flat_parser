<h1 align="center">
  LSR парсер недвижимости.
</h1>

<h3 align="center">❗️ Работу парсера можно глянуть в <a href="https://t.me/+yW_YH0Nx541hYjNi">телеграм канале</a></h3>

<h4 align="center">Оглавление README:</h4>
<div align="center">
    <a href="#про-скрипт"> • Для чего нужен этот скрипт • </a><br>
    <a href="#установка"> • Установка • </a><br>
    <a href="#внутрянка"> • Что внутри • </a><br>
    <a href="#файл-settingsjson"> • Что такое файл settings.json • </a><br>
    <a href="#примечание"> • Примечание • </a>
</div>


## Про скрипт
Есть такой застройщик недвижимости как ЛСР (https://www.lsr.ru/).

На циане застройщик удаляет обьявления и выставляет по новой, поэтому для того что бы понимать как меняются цены, необходимо забирать данные самостоятельно и агрегируя их, производить анализ.

Поэтому хочется поглядеть как меняется спрос на квартиры и их цена в новостройках ЖК Лучи.


## Установка
1. Скачиваете ветку;
2. Устанавливаете python 3.9;
3. Создаете виртуальное окружение `python3.9 -m venv env`
4. Активируете виртуальное окружение и устанавливаете зависимости `pip install -r requirements.txt`
5. Редактируете файл `settings.json` под себя;
6. Запускаете `parse.py` и наслаждаетесь результатом.


## Внутрянка
1. Данные для настройки указываются в конфиг файле `settings.json` *(шаблон заполнен тестовыми данными и называется sample_settings.json)*;
2. Автоматизированная программа(скрипт) забирает все квартиры по адресу, преобразует в список [`get_all_flats` функция];
3. Этот список закидывается в файлы внутрь папки `queue` [`save_data_flats_queue` функция];
4. Затем происходит обработка всех данных путем сравнения полученных квартир из пункта 2 и сохраненными раннее данными в папку `data` [`process_flats`];
5. В ходе процессинга в пункте 5 происходит отправка уведомлений в телеграм путем post запроса на собственный микросервис по отправке сообщений (при условии что флаг `send_telegram_message` внутри настроеек имеет значение True);
6. После процессинга засыпаем на время указанное в `settings.json`, значение следующего запроса записываем в системный файл `settings_system.json`.


## Файл settings.json
Файл settings.json имеет формат json, с следующими ключами:

* "host": [str] адрес микросервиса для отправки сообщений в телегу,

* "sender": [str|int] кому отправлять сообщение в телеге, если указана str то будет ресолвить username, если указан int то будет считать что это userid(можно указывать ид канала),

* "token": [str] токен микросервиса для отправки сообщения (по сути подпись),

* "await_time": [int] количество секунд перед, следующим циклом запросов,

* "send_telegram_message": [bool] использовать ли уведомление в телеграм или обойдемся обычными принтами.

*Если возникают какие-то сложности с файлом `settings.json` то можно переименовать файл с базовыми настройками `sample_settings.json` в `settings.json`, скрипт будет работать корректно*.


## Примечание
По работе с виртуальными окружениями можно почитать <a href="https://docs.python.org/3/library/venv.html#how-venvs-work"> docs.python.org</a>