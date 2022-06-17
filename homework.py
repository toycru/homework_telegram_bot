import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('YANDEX_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logging.info('Начат запрос к API')
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception as error:
        message = f'Недоступен эндпоинт сервиса {error}'
        logging.critical(message)
        raise ConnectionError(message)
    else:
        if homework_statuses.status_code == HTTPStatus.OK:
            # Возврещает ответ API в формате JSON
            response = homework_statuses.json()
            return response
        else:
            message = 'Статус не 200'
            logging.critical(message)
            raise ConnectionError(message)


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict) or response is None:
        message = 'Ответ API не содержит словаря с данными'
        raise TypeError(message)

    elif any([response.get('homeworks') is None,
              response.get('current_date') is None]):
        message = ('Словарь ответа API не содержит ключей homeworks и/или '
                   'current_date')
        raise KeyError(message)

    elif not isinstance(response.get('homeworks'), list):
        message = 'Ключ homeworks в ответе API не содержит списка'
        raise TypeError(message)

    elif not response.get('homeworks'):
        logging.info('Статус проверки не изменился')
        return []

    else:
        return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о конкретной ДЗ статус этой работы."""
    if homework.get('homework_name') is None:
        message = 'Словарь ответа API не содержит ключа homework_name'
        raise KeyError(message)
    elif homework.get('status') is None:
        message = 'Словарь ответа API не содержит ключа status'
        raise KeyError(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
    else:
        message = 'Статус ответа не известен'
        # raise APIResponseError(message)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения для работы программы."""
    return all(
        [
            PRACTICUM_TOKEN is not None,
            TELEGRAM_TOKEN is not None,
            TELEGRAM_CHAT_ID is not None,
        ]
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Одна или несколько пересменных окружения не доступны'
        logging.critical(message)
        raise NameError(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    send_message(bot, 'Бот запущен и отслеживает статус проверки ДЗ!')

    while True:
        try:
            response = get_api_answer(current_timestamp)
            if response:
                homework = check_response(response)
                if len(homework) > 0:
                    message = parse_status(homework)
                    send_message(bot, message)
                current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.critical(message)
            time.sleep(RETRY_TIME)
        else:
            logging.info('Итерация проверки ДЗ прошла успешно')


if __name__ == '__main__':
    log_format = (
        '%(asctime)s [%(levelname)s] - '
        '(%(filename)s).%(funcName)s:%(lineno)d - %(message)s'
    )
    logging.basicConfig(
        level=logging.INFO,
        filename='homework_bot.log',
        format=log_format
    )
    main()
