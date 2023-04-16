# -*- coding: utf-8 -*-

"""Defines common exceptions.
"""

class MumbleBaseException(Exception):
    """Base exception.

    As the string representation is like ``ExceptionClassName(message)``, you
    can easily filter exceptions with a selection pattern of API Gateway
    integration responses.
    """
    message: str
    """Brief explanation about the problem."""

    def __init__(self, message: str):
        """Initializes with a given message.
        """
        self.message = message

    def __str__(self):
        class_name = type(self).__name__
        return f'{class_name}({self.message})'

    def __rerp__(self):
        class_name = type(self).__name__
        return f'{class_name}({repr(self.message)})'


class BadConfigurationError(MumbleBaseException):
    """Raised if the configuration is wrong.
    """


class BadRequestError(MumbleBaseException):
    """Raised if the request is invalid.
    """


class UnexpectedDomainError(MumbleBaseException):
    """Raised if the domain name is unexpected.
    """


class NotFoundError(MumbleBaseException):
    """Raised if the account is not found.
    """
