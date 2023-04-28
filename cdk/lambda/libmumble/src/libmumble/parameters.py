# -*- coding: utf-8 -*-

"""Provides utilities to access parameters in Parameter Store on AWS Systems
Manager.
"""

import logging
import os


LOGGER = logging.getLogger('libmumble.parameters')
LOGGER.setLevel(logging.DEBUG)


def get_domain_name(ssm) -> str:
    """Obtains the domain name from Parameter Store on AWS Systems Manager.

    You have to configure the following environment variable:
    * ``DOMAIN_NAME_PARAMETER_PATH``

    :param boto3.client('ssm') ssm: AWS Systems Manager client to get
    a parameter from Parameter Store.

    :raises KeyError: if the environement variable is not configured,
    or if the domain name parameter is not found in Parameter Store.
    """
    parameter_name = os.environ['DOMAIN_NAME_PARAMETER_PATH']
    LOGGER.debug('getting parameter: %s', parameter_name)
    try:
        res = ssm.get_parameter(
            Name=parameter_name,
            WithDecryption=True,
        )
        return res['Parameter']['Value']
    except (
        ssm.exceptions.InvalidKeyId,
        ssm.exceptions.ParameterNotFound,
    ) as exc:
        raise KeyError(exc) from exc
