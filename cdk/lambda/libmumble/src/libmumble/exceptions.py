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


class CorruptedDataError(MumbleBaseException):
    """Raised if the data is corrupted.
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


class TransientError(MumbleBaseException):
    """Raised if there is a transient error; e.g., temporary service outage.
    """


class DuplicateItemError(MumbleBaseException):
    """Raised if an item is duplicated.
    """


class TooManyAccessError(TransientError):
    """Raised if there are too many requests.
    """


class UnauthorizedError(MumbleBaseException):
    """Raised if a credential is invalid.
    """


class ForbiddenError(MumbleBaseException):
    """Raised if a credential is valid but not allowed to access a resource.
    """


class CommunicationError(MumbleBaseException):
    """Raised if communication between other server fails.
    """
