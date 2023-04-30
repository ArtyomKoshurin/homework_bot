import os
import sys
import time

import telegram
import logging
from logging.handlers import RotatingFileHandler
import requests
from dotenv import load_dotenv

from exceptions import (
    StatusNotAccording,
    TokenRequired,
    StatusIsUnexepted,
    MessageNotSent
)

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
second_handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(second_handler)

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
        if not token:
            message = f'Отсутствует необходимый токен: {token}'
            logging.critical(message)
            raise TokenRequired(message)


def send_message(bot, message):
    """Отправляем сообщение в Телеграм о статусе домашней работы."""
    try:
        logger.debug('Сообщение успешно отправлено')
        return bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception:
        raise MessageNotSent('Сообщение не отправлено')


def get_api_answer(timestamp):
    """Отправялем запрос к API Яндекса."""
    payload = {'from_date': timestamp}
    try:
        homeworks = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
    except requests.RequestException as error:
        raise error(
            f'Ошибка при запросе к API: {error}'
            f'Запрашиваемые параметры: {payload}, {ENDPOINT}')
    if homeworks.status_code != 200:
        raise StatusIsUnexepted(f'Эндпоинт недоступен. Ошибка: '
                                f'{homeworks.status_code}')
    return homeworks.json()


def check_response(response):
    """Проверяем ответ на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(f'Ответ API не является словарем'
                        f'Тип полученных данных: {type(response)}')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "homeworks" в ответе API')
    if 'current_date' not in response:
        raise KeyError('Отсутствует ключ "current_date" в ответе API')

    homework_list = response['homeworks']
    if not isinstance(homework_list, list):
        raise TypeError(f'Ответ API под ключом "homeworks" не является списком'
                        f'Тип полученных данных: {type(homework_list)}')
    return homework_list


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
    raise StatusNotAccording(f'Статус {status} не соответствует ожидаемому')


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    check_tokens()
    first_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)[0]
            # Не совсем понимаю, что ты иммешь ввиду под пустым списком.
            # Как я понял - нужно поставить условие на наличие списка homework,
            # и если его нет - поднять логгер с непроверенной домашкой,
            # как я и сделал. Или нужно сначала присвоить переменной
            # homework = check_response(response) без индекса, и проверять
            # условие на ней?
            if homework:
                message = parse_status(homework)
                try:
                    send_message(bot, message)
                except MessageNotSent:
                    logger.error('Не удалось отправить сообщение')
            else:
                logger.error('Вашу домашку еще не проверили')
            timestamp = response['current_date']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != first_message:
                try:
                    send_message(bot, message)
                except MessageNotSent:
                    logger.error('Не удалось отправить сообщение')
                first_message = message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
