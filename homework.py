import logging
import os
import time
import telegram

import requests

from logging.handlers import RotatingFileHandler

from exceptions import (
    StatusNotAccording,
    TokenRequired,
    StatusIsUnexepted,
    MessageNotSent
)

from dotenv import load_dotenv

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logger = logging.getLogger(__name__)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5,
    encoding='utf-8'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем доступность переменных окружения."""
    token_list = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
    ]
    for token in token_list:
        if token is None:
            message = f'Отсутствует необходимый токен: {token}'
            logging.critical(message)
            raise TokenRequired(message)
    return True


def send_message(bot, message):
    """Отправляем сообщение в Телеграм о статусе домашней работы."""
    try:
        logger.debug('Сообщение успешно отправлено')
        return bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logger.error(f'Не удалось отправить сообщение {error}')
        raise MessageNotSent('Сообщение не отправлено')


def get_api_answer(timestamp):
    """Отправялем запрос к API Яндекса."""
    PAYLOAD = {'from_date': timestamp}
    try:
        homeworks = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=PAYLOAD
        )
    except Exception as error:
        logger.error(f'ошибка при запросе к API: {error}')
    if homeworks.status_code != 200:
        raise StatusIsUnexepted(f'Эндпоинт недоступен. Ошибка: '
                                f'{homeworks.status_code}')
    return homeworks.json()


def check_response(response):
    """Проверяем ответ на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Ответ API под ключом "homeworks" не является списком')

    homeworks = response['homeworks'][0]
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является списком')
    return homeworks


def parse_status(homework):
    """Проверяем статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status" в ответе API')

    homework_name = homework['homework_name']
    status = homework['status']
    if status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[status]
        logger.debug('Неожиданных статусов не присутствует')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        message = f'Статус {status} не соответствует ожидаемому'
        logger.error(message)
        raise StatusNotAccording(message)


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    check_tokens()
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
            else:
                message = 'Ваша домашка еще не принята на проверку'
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
