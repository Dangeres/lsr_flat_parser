import re
import requests


def price_format(value):
    str_value = str(value)

    regex = r'\d{3}(?!$)'
    subst = '\g<0>.'

    return re.sub(regex, subst, str_value[::-1], 0, re.MULTILINE)[::-1]


def send_telegram(uid, message, host, sender):
    try:
        result = requests.post(
            url = host + '/message',
            json = {
                'id': uid,
                'sender': sender,
                'text': message,
            }
        )

        print(message)

        return result.status_code == 200 and result.json().get('success')
    except Exception as e:
        print(e)

    return False


def just_print(message):
    print(message)

    return True