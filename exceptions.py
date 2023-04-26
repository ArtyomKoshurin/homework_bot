class StatusNotAccording(Exception):
    """Исключение, возникающее при наличии стороннего статуса."""

    pass


class TokenRequired(Exception):
    """Исключение, возникающее при отсутствии необходмого токена."""

    pass


class StatusIsUnexepted(Exception):
    """Исключение, возникающее при невозможности перехода к API."""

    pass


class MessageNotSent(Exception):
    """Исключение, возникающее при невозможности отправки сообщения."""

    pass
