# -*- coding: utf-8 -*-

"""Tests ``libactivitypub.signature``.
"""

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from libactivitypub.signature import (
    VerificationError,
    digest_request_body,
    is_valid_request_body,
    is_valid_signature_date,
    make_signature_header,
    parse_signature,
    parse_signature_headers_parameter,
    sign_headers,
    verify_headers,
)
import pytest


def test_parse_signature_with_full_parameters():
    """Tests ``parse_signature`` with all the parameters: "keyId", "algorithm",
    "headers", and "signature".
    """
    signature = (
        'keyId="https://mastodon-japan.net/users/kemoto#main-key",'
        'algorithm="rsa-sha256",'
        'headers="(request-target) host date digest content-type",'
        'signature="VWKg2dPhJRJxHpq8L2XmTgYN01aqojiOs/jUXe/F1DyZN97Sl5urr0NMqKXm8A3QgaqDiVc1OZSxbTVQBDpLone8js6qxKSheAwzkOe/Ozjbu3wptwmbmGMyeb3VHwcI2A3pNC+EiiZuvDQFCWQYKJfgsjUrz+yC0yoMi9finTIPSqLwVnkacPxn1U8tzCp5ReHkgPa70wPD9lIO/qe9YR+xxjHoO3qwIdwNU8wA5lVjnw0fhvALDSYbysjePAAcg6qLJ+wSlCoA0xSPnfwZYhpmI2WOYs/ePcLNkyFLqMsXhOmB8PREA+QENzSeKhdgphkwd6u8OE3F44W8S/OPFg=="'
    )
    assert parse_signature(signature) == {
        'key_id': 'https://mastodon-japan.net/users/kemoto#main-key',
        'algorithm': 'rsa-sha256',
        'headers': '(request-target) host date digest content-type',
        'signature': 'VWKg2dPhJRJxHpq8L2XmTgYN01aqojiOs/jUXe/F1DyZN97Sl5urr0NMqKXm8A3QgaqDiVc1OZSxbTVQBDpLone8js6qxKSheAwzkOe/Ozjbu3wptwmbmGMyeb3VHwcI2A3pNC+EiiZuvDQFCWQYKJfgsjUrz+yC0yoMi9finTIPSqLwVnkacPxn1U8tzCp5ReHkgPa70wPD9lIO/qe9YR+xxjHoO3qwIdwNU8wA5lVjnw0fhvALDSYbysjePAAcg6qLJ+wSlCoA0xSPnfwZYhpmI2WOYs/ePcLNkyFLqMsXhOmB8PREA+QENzSeKhdgphkwd6u8OE3F44W8S/OPFg==',
    }


def test_parse_signature_without_algorithm():
    """Tests ``parse_signature`` without "algorithm".
    """
    signature = (
        'keyId="https://mastodon-japan.net/users/kemoto#main-key",'
        'headers="(request-target) host date digest content-type",'
        'signature="VWKg2dPhJRJxHpq8L2XmTgYN01aqojiOs/jUXe/F1DyZN97Sl5urr0NMqKXm8A3QgaqDiVc1OZSxbTVQBDpLone8js6qxKSheAwzkOe/Ozjbu3wptwmbmGMyeb3VHwcI2A3pNC+EiiZuvDQFCWQYKJfgsjUrz+yC0yoMi9finTIPSqLwVnkacPxn1U8tzCp5ReHkgPa70wPD9lIO/qe9YR+xxjHoO3qwIdwNU8wA5lVjnw0fhvALDSYbysjePAAcg6qLJ+wSlCoA0xSPnfwZYhpmI2WOYs/ePcLNkyFLqMsXhOmB8PREA+QENzSeKhdgphkwd6u8OE3F44W8S/OPFg=="'
    )
    assert parse_signature(signature) == {
        'key_id': 'https://mastodon-japan.net/users/kemoto#main-key',
        'algorithm': 'rsa-sha256',
        'headers': '(request-target) host date digest content-type',
        'signature': 'VWKg2dPhJRJxHpq8L2XmTgYN01aqojiOs/jUXe/F1DyZN97Sl5urr0NMqKXm8A3QgaqDiVc1OZSxbTVQBDpLone8js6qxKSheAwzkOe/Ozjbu3wptwmbmGMyeb3VHwcI2A3pNC+EiiZuvDQFCWQYKJfgsjUrz+yC0yoMi9finTIPSqLwVnkacPxn1U8tzCp5ReHkgPa70wPD9lIO/qe9YR+xxjHoO3qwIdwNU8wA5lVjnw0fhvALDSYbysjePAAcg6qLJ+wSlCoA0xSPnfwZYhpmI2WOYs/ePcLNkyFLqMsXhOmB8PREA+QENzSeKhdgphkwd6u8OE3F44W8S/OPFg==',
    }


def test_parse_signature_with_double_quotation_in_key_id():
    """Tests ``parse_signature`` with "keyId" containing a double quotation
    mark enclosed.

    It is valid, though, I am not sure we have to accept it.
    """
    signature = (
        'keyId="https://mastodon-japan.net/users/kemoto#"main-key",'
        'algorithm="rsa-sha256",'
        'headers="(request-target) host date digest content-type",'
        'signature="VWKg2dPhJRJxHpq8L2XmTgYN01aqojiOs/jUXe/F1DyZN97Sl5urr0NMqKXm8A3QgaqDiVc1OZSxbTVQBDpLone8js6qxKSheAwzkOe/Ozjbu3wptwmbmGMyeb3VHwcI2A3pNC+EiiZuvDQFCWQYKJfgsjUrz+yC0yoMi9finTIPSqLwVnkacPxn1U8tzCp5ReHkgPa70wPD9lIO/qe9YR+xxjHoO3qwIdwNU8wA5lVjnw0fhvALDSYbysjePAAcg6qLJ+wSlCoA0xSPnfwZYhpmI2WOYs/ePcLNkyFLqMsXhOmB8PREA+QENzSeKhdgphkwd6u8OE3F44W8S/OPFg=="'
    )
    assert parse_signature(signature) == {
        'key_id': 'https://mastodon-japan.net/users/kemoto#"main-key',
        'algorithm': 'rsa-sha256',
        'headers': '(request-target) host date digest content-type',
        'signature': 'VWKg2dPhJRJxHpq8L2XmTgYN01aqojiOs/jUXe/F1DyZN97Sl5urr0NMqKXm8A3QgaqDiVc1OZSxbTVQBDpLone8js6qxKSheAwzkOe/Ozjbu3wptwmbmGMyeb3VHwcI2A3pNC+EiiZuvDQFCWQYKJfgsjUrz+yC0yoMi9finTIPSqLwVnkacPxn1U8tzCp5ReHkgPa70wPD9lIO/qe9YR+xxjHoO3qwIdwNU8wA5lVjnw0fhvALDSYbysjePAAcg6qLJ+wSlCoA0xSPnfwZYhpmI2WOYs/ePcLNkyFLqMsXhOmB8PREA+QENzSeKhdgphkwd6u8OE3F44W8S/OPFg==',
    }


def test_parse_signature_without_key_id():
    """Tests ``parse_signature`` without "keyId".
    """
    signature = (
        'algorithm="rsa-sha256",'
        'headers="(request-target) host date digest content-type",'
        'signature="VWKg2dPhJRJxHpq8L2XmTgYN01aqojiOs/jUXe/F1DyZN97Sl5urr0NMqKXm8A3QgaqDiVc1OZSxbTVQBDpLone8js6qxKSheAwzkOe/Ozjbu3wptwmbmGMyeb3VHwcI2A3pNC+EiiZuvDQFCWQYKJfgsjUrz+yC0yoMi9finTIPSqLwVnkacPxn1U8tzCp5ReHkgPa70wPD9lIO/qe9YR+xxjHoO3qwIdwNU8wA5lVjnw0fhvALDSYbysjePAAcg6qLJ+wSlCoA0xSPnfwZYhpmI2WOYs/ePcLNkyFLqMsXhOmB8PREA+QENzSeKhdgphkwd6u8OE3F44W8S/OPFg=="'
    )
    with pytest.raises(ValueError):
        parse_signature(signature)


def test_parse_signature_with_empty_key_id():
    """Tests ``parse_signature`` with empty "keyId".
    """
    signature = (
        'keyId="",'
        'algorithm="rsa-sha256",'
        'headers="(request-target) host date digest content-type",'
        'signature="VWKg2dPhJRJxHpq8L2XmTgYN01aqojiOs/jUXe/F1DyZN97Sl5urr0NMqKXm8A3QgaqDiVc1OZSxbTVQBDpLone8js6qxKSheAwzkOe/Ozjbu3wptwmbmGMyeb3VHwcI2A3pNC+EiiZuvDQFCWQYKJfgsjUrz+yC0yoMi9finTIPSqLwVnkacPxn1U8tzCp5ReHkgPa70wPD9lIO/qe9YR+xxjHoO3qwIdwNU8wA5lVjnw0fhvALDSYbysjePAAcg6qLJ+wSlCoA0xSPnfwZYhpmI2WOYs/ePcLNkyFLqMsXhOmB8PREA+QENzSeKhdgphkwd6u8OE3F44W8S/OPFg=="'
    )
    with pytest.raises(ValueError):
        parse_signature(signature)


def test_parse_signature_with_empty_algorithm():
    """Tests ``parse_signature`` with empty "algorithm".
    """
    signature = (
        'keyId="https://mastodon-japan.net/users/kemoto#main-key",'
        'algorithm="",'
        'headers="(request-target) host date digest content-type",'
        'signature="VWKg2dPhJRJxHpq8L2XmTgYN01aqojiOs/jUXe/F1DyZN97Sl5urr0NMqKXm8A3QgaqDiVc1OZSxbTVQBDpLone8js6qxKSheAwzkOe/Ozjbu3wptwmbmGMyeb3VHwcI2A3pNC+EiiZuvDQFCWQYKJfgsjUrz+yC0yoMi9finTIPSqLwVnkacPxn1U8tzCp5ReHkgPa70wPD9lIO/qe9YR+xxjHoO3qwIdwNU8wA5lVjnw0fhvALDSYbysjePAAcg6qLJ+wSlCoA0xSPnfwZYhpmI2WOYs/ePcLNkyFLqMsXhOmB8PREA+QENzSeKhdgphkwd6u8OE3F44W8S/OPFg=="'
    )
    with pytest.raises(ValueError):
        parse_signature(signature)


def test_parse_signature_without_headers():
    """Tests ``parse_signature`` without "headers".
    """
    signature = (
        'keyId="https://mastodon-japan.net/users/kemoto#main-key",'
        'algorithm="rsa-sha256",'
        'signature="VWKg2dPhJRJxHpq8L2XmTgYN01aqojiOs/jUXe/F1DyZN97Sl5urr0NMqKXm8A3QgaqDiVc1OZSxbTVQBDpLone8js6qxKSheAwzkOe/Ozjbu3wptwmbmGMyeb3VHwcI2A3pNC+EiiZuvDQFCWQYKJfgsjUrz+yC0yoMi9finTIPSqLwVnkacPxn1U8tzCp5ReHkgPa70wPD9lIO/qe9YR+xxjHoO3qwIdwNU8wA5lVjnw0fhvALDSYbysjePAAcg6qLJ+wSlCoA0xSPnfwZYhpmI2WOYs/ePcLNkyFLqMsXhOmB8PREA+QENzSeKhdgphkwd6u8OE3F44W8S/OPFg=="'
    )
    with pytest.raises(ValueError):
        parse_signature(signature)


def test_parse_signature_with_empty_headers():
    """Tests ``parse_signature`` with empty "headers".
    """
    signature = (
        'keyId="https://mastodon-japan.net/users/kemoto#main-key",'
        'algorithm="rsa-sha256",'
        'headers="",'
        'signature="VWKg2dPhJRJxHpq8L2XmTgYN01aqojiOs/jUXe/F1DyZN97Sl5urr0NMqKXm8A3QgaqDiVc1OZSxbTVQBDpLone8js6qxKSheAwzkOe/Ozjbu3wptwmbmGMyeb3VHwcI2A3pNC+EiiZuvDQFCWQYKJfgsjUrz+yC0yoMi9finTIPSqLwVnkacPxn1U8tzCp5ReHkgPa70wPD9lIO/qe9YR+xxjHoO3qwIdwNU8wA5lVjnw0fhvALDSYbysjePAAcg6qLJ+wSlCoA0xSPnfwZYhpmI2WOYs/ePcLNkyFLqMsXhOmB8PREA+QENzSeKhdgphkwd6u8OE3F44W8S/OPFg=="'
    )
    with pytest.raises(ValueError):
        parse_signature(signature)


def test_parse_signature_without_signature():
    """Tests ``parse_signature`` without "signature".
    """
    signature = (
        'keyId="https://mastodon-japan.net/users/kemoto#main-key",'
        'algorithm="rsa-sha256",'
        'headers="(request-target) host date digest content-type",'
    )
    with pytest.raises(ValueError):
        parse_signature(signature)


def test_parse_signature_with_empty_signature():
    """Tests ``parse_signature`` with empty "signature".
    """
    signature = (
        'keyId="https://mastodon-japan.net/users/kemoto#main-key",'
        'algorithm="rsa-sha256",'
        'headers="(request-target) host date digest content-type",'
        'signature=""'
    )
    with pytest.raises(ValueError):
        parse_signature(signature)


def test_parse_signature_single_quoted():
    """Tests ``parse_signature`` with parameters enclosed in single quotation
    marks.
    """
    signature = (
        "keyId='https://mastodon-japan.net/users/kemoto#main-key',"
        "algorithm='rsa-sha256',"
        "headers='(request-target) host date digest content-type',"
        "signature='VWKg2dPhJRJxHpq8L2XmTgYN01aqojiOs/jUXe/F1DyZN97Sl5urr0NMqKXm8A3QgaqDiVc1OZSxbTVQBDpLone8js6qxKSheAwzkOe/Ozjbu3wptwmbmGMyeb3VHwcI2A3pNC+EiiZuvDQFCWQYKJfgsjUrz+yC0yoMi9finTIPSqLwVnkacPxn1U8tzCp5ReHkgPa70wPD9lIO/qe9YR+xxjHoO3qwIdwNU8wA5lVjnw0fhvALDSYbysjePAAcg6qLJ+wSlCoA0xSPnfwZYhpmI2WOYs/ePcLNkyFLqMsXhOmB8PREA+QENzSeKhdgphkwd6u8OE3F44W8S/OPFg=='"
    )
    with pytest.raises(ValueError):
        parse_signature(signature)


def test_parse_signature_headers_parameter_with_mandatory_headers():
    """Tests ``parse_signature_headers_parameter`` with
    "(request-taget) host date".
    """
    headers = '(request-target) host date'
    assert parse_signature_headers_parameter(headers) == [
        '(request-target)',
        'host',
        'date',
    ]


def test_parse_signature_headers_parameter_with_extra_headers():
    """Tests ``parse_signature_headers_parameter`` with
    "(request-target) host date digest content-type".
    """
    headers = '(request-target) host date digest content-type'
    assert parse_signature_headers_parameter(headers) == [
        '(request-target)',
        'host',
        'date',
        'digest',
        'content-type',
    ]


def test_parse_signature_headers_parameter_without_request_target():
    """Tests ``parse_signature_headers_parameter`` with "host date".
    """
    headers = 'host date'
    with pytest.raises(ValueError):
        parse_signature_headers_parameter(headers)


def test_parse_signature_headers_parameter_without_host():
    """Tests ``parse_signature_headers_parameter`` with
    "(request-target) date".
    """
    headers = '(request-target) date'
    with pytest.raises(ValueError):
        parse_signature_headers_parameter(headers)


def test_parse_signature_headers_parameter_without_date():
    """Tests ``parse_signature_headers_parameter`` with
    "(request-target) host".
    """
    headers = '(request-target) host'
    with pytest.raises(ValueError):
        parse_signature_headers_parameter(headers)


def test_parse_signature_headers_parameter_with_extra_whitespace():
    """Tests ``parse_signature_headers_parameter`` with
    "(request-target)  host  date".
    """
    headers = '(request-target)  host  date'
    with pytest.raises(ValueError):
        parse_signature_headers_parameter(headers)


def test_is_valid_signature_date_with_current_time():
    """Tests ``is_valid_signature_date`` with the current time.
    """
    now = datetime.now(tz=timezone.utc)
    date = format_datetime(now)
    assert is_valid_signature_date(date)


def test_is_valid_signature_date_with_current_time_plus_40_s():
    """Tests ``is_valid_signature_date`` with the current time + 40 seconds.
    """
    now = datetime.now(tz=timezone.utc)
    date = format_datetime(now + timedelta(seconds=40))
    assert not is_valid_signature_date(date)


def test_is_valid_signature_date_with_current_time_minus_40_s():
    """Tests ``is_valid_signature_date`` with the current time - 40 seconds.
    """
    now = datetime.now(tz=timezone.utc)
    date = format_datetime(now - timedelta(seconds=40))
    assert not is_valid_signature_date(date)


def test_is_valid_signature_date_with_invalid_date():
    """Tests ``is_valid_signature_date`` with an invalid date.
    """
    with pytest.raises(TypeError):
        is_valid_signature_date('2023年4月22日(土)')


def test_digest_request_body():
    """Tests ``digest_request_body``.
    """
    body = 'Please digest me!'.encode('utf-8')
    digest = 'SHA-256=bJHL/rvRZ2mepX6J1bjavpj8TFMFNM+EDx8lQ/3LDGI='
    assert digest_request_body(body) == digest


def test_is_valid_request_body_with_valid_body():
    """Tests ``is_valid_request_body`` with a valid body.
    """
    body = 'This is the original body!'
    digest = 'SHA-256=Vy3Jx1225w2R58b11gY7s7TueFelSNZ/OK6Vk7D2n1U='
    assert is_valid_request_body(body, digest)


def test_is_valid_request_body_with_invalid_body():
    """Tests ``is_valid_request_body`` with an invalid body.
    """
    body = 'This is a tampered body!'
    digest = 'SHA-256=Vy3Jx1225w2R58b11gY7s7TueFelSNZ/OK6Vk7D2n1U='
    assert not is_valid_request_body(body, digest)


def test_verify_headers_with_valid_values():
    """Tests ``verify_headers`` with valid values.

    Kikuo: I made the signature according to the steps described at
    https://www.pycryptodome.org/src/signature/pkcs1_v1_5
    """
    headers = ['(request-target)', 'host', 'date', 'digest']
    header_values = {
        '(request-target)': 'post /users/kemoto/inbox',
        'host': 'mumble.codemonger.io',
        'date': 'Fri, 21 Apr 2023 11:32:00 GMT',
        'digest': 'SHA-256=abcdefg',
    }
    signature = 'KTZHoFpvAy0y7xl2Z391YVxW/PEVUWUFaG57vP1y22dK8tPuhvJ+z3G0H0eWwQUpybdR53qF6A+tHWyDdTn0fwRk6jwNqmY9QH4sp7lddv2q0tNoFynTWjJWGe0qJKurFD6Pfp/6nwsgWC6sgtIRdVjh/iQN4UZH4RLTs1GoNnRMzS97srWheq6UlKZzhGWT8Os+88JIuuiZXDOqyuHMFT16Dfmy2IoynVLaJqSap22QYwWZiBuRTkirQUX6dcyF5EE99CgRp2u7f1SQW/PoBsKr+WlwnbTzIwzd9ulZ/yLmnZazJMBuPgJrQgQkkKDdOCszSrsc1eoiHBNsUCF+Iw=='
    public_key_pem = PUBLIC_KEY_PEM_1
    # never throws
    verify_headers(headers, header_values, signature, public_key_pem)


def test_verify_headers_with_wrong_public_key():
    """Tests ``verify_headers`` with a wrong public key.
    """
    headers = ['(request-target)', 'host', 'date', 'digest']
    header_values = {
        '(request-target)': 'post /users/kemoto/inbox',
        'host': 'mumble.codemonger.io',
        'date': 'Fri, 21 Apr 2023 11:32:00 GMT',
        'digest': 'SHA-256=abcdefg',
    }
    signature = 'KTZHoFpvAy0y7xl2Z391YVxW/PEVUWUFaG57vP1y22dK8tPuhvJ+z3G0H0eWwQUpybdR53qF6A+tHWyDdTn0fwRk6jwNqmY9QH4sp7lddv2q0tNoFynTWjJWGe0qJKurFD6Pfp/6nwsgWC6sgtIRdVjh/iQN4UZH4RLTs1GoNnRMzS97srWheq6UlKZzhGWT8Os+88JIuuiZXDOqyuHMFT16Dfmy2IoynVLaJqSap22QYwWZiBuRTkirQUX6dcyF5EE99CgRp2u7f1SQW/PoBsKr+WlwnbTzIwzd9ulZ/yLmnZazJMBuPgJrQgQkkKDdOCszSrsc1eoiHBNsUCF+Iw=='
    public_key_pem = PUBLIC_KEY_PEM_2
    with pytest.raises(VerificationError):
        verify_headers(headers, header_values, signature, public_key_pem)


def test_verify_headers_with_wrong_private_key():
    """Tests ``verify_headers`` with a signature signed with a wrong private
    key.

    Kikuo: I made the signature according to the steps described at
    https://www.pycryptodome.org/src/signature/pkcs1_v1_5
    """
    headers = ['(request-target)', 'host', 'date', 'digest']
    header_values = {
        '(request-target)': 'post /users/kemoto/inbox',
        'host': 'mumble.codemonger.io',
        'date': 'Fri, 21 Apr 2023 11:32:00 GMT',
        'digest': 'SHA-256=abcdefg',
    }
    signature = 'Hz/RPq18umk6H661X+8rPVFaDFbamcCCbhCF1qwF3cyvvaGSSpE4w2aDITbAdERjHzUHrAZM69UOeImq83e7VZ42layF3hQnA5CNU9d6IJI93aOM2/fiGrrtyHr5OHJUBEodWdvdOsvflMfEy+BDKyWpOfMlQXnfgAjK/9Y4Lbi+VCiGlRpF5838ATvMYwIwNEXh7xAh9S3ifZ/76WyNh6UIEPhIg2K1qnVbs7yKMJj+GLncaXi5DAxMprGoUo1S+MkjO92ILpi3NifwanhRaqbmTNlkoQ0UknRDalt36ojCUL3tOHGKikQAOGdXimnCln4ysV+fdoMG9Uww7rywTg=='
    public_key_pem = PUBLIC_KEY_PEM_1
    with pytest.raises(VerificationError):
        verify_headers(headers, header_values, signature, public_key_pem)


def test_verify_headers_with_tampered_values():
    """Tests ``verify_headers`` with tampered values.
    """
    headers = ['(request-target)', 'host', 'date', 'digest']
    header_values = {
        '(request-target)': 'post /users/imposter/inbox',
        'host': 'speakloud.codemonger.com',
        'date': 'Fri, 21 Apr 2023 11:32:00 GMT',
        'digest': 'SHA-256=abcdefg',
    }
    signature = 'KTZHoFpvAy0y7xl2Z391YVxW/PEVUWUFaG57vP1y22dK8tPuhvJ+z3G0H0eWwQUpybdR53qF6A+tHWyDdTn0fwRk6jwNqmY9QH4sp7lddv2q0tNoFynTWjJWGe0qJKurFD6Pfp/6nwsgWC6sgtIRdVjh/iQN4UZH4RLTs1GoNnRMzS97srWheq6UlKZzhGWT8Os+88JIuuiZXDOqyuHMFT16Dfmy2IoynVLaJqSap22QYwWZiBuRTkirQUX6dcyF5EE99CgRp2u7f1SQW/PoBsKr+WlwnbTzIwzd9ulZ/yLmnZazJMBuPgJrQgQkkKDdOCszSrsc1eoiHBNsUCF+Iw=='
    public_key_pem = PUBLIC_KEY_PEM_1
    with pytest.raises(VerificationError):
        verify_headers(headers, header_values, signature, public_key_pem)


def test_verify_headers_with_broken_public_key():
    """Tests ``verify_headers`` with a broken public key.
    """
    headers = ['(request-target)', 'host', 'date', 'digest']
    header_values = {
        '(request-target)': 'post /users/kemoto/inbox',
        'host': 'mumble.codemonger.io',
        'date': 'Fri, 21 Apr 2023 11:32:00 GMT',
        'digest': 'SHA-256=abcdefg',
    }
    signature = 'KTZHoFpvAy0y7xl2Z391YVxW/PEVUWUFaG57vP1y22dK8tPuhvJ+z3G0H0eWwQUpybdR53qF6A+tHWyDdTn0fwRk6jwNqmY9QH4sp7lddv2q0tNoFynTWjJWGe0qJKurFD6Pfp/6nwsgWC6sgtIRdVjh/iQN4UZH4RLTs1GoNnRMzS97srWheq6UlKZzhGWT8Os+88JIuuiZXDOqyuHMFT16Dfmy2IoynVLaJqSap22QYwWZiBuRTkirQUX6dcyF5EE99CgRp2u7f1SQW/PoBsKr+WlwnbTzIwzd9ulZ/yLmnZazJMBuPgJrQgQkkKDdOCszSrsc1eoiHBNsUCF+Iw=='
    public_key_pem = 'Trust me! I am a public key!'
    with pytest.raises(VerificationError):
        verify_headers(headers, header_values, signature, public_key_pem)


def test_sign_headers():
    """Tests ``sign_headers`` with ``PRIVATE_KEY_PEM_1``.

    Kikuo: I made the signature according to the steps described at
    https://www.pycryptodome.org/src/signature/pkcs1_v1_5
    """
    headers = ['(request-target)', 'host', 'date', 'digest', 'content-type']
    header_values = {
        '(request-target)': 'post /users/kemoto/inbox',
        'host': 'mumble.codemonger.io',
        'date': 'Wed, 26 Apr 2023 11:32:00 GMT',
        'digest': 'SHA-256=abcdefg',
        'content-type': 'application/json',
    }
    private_key_pem = PRIVATE_KEY_PEM_1
    signature = 'ZKAhY+h/a9nstRzRBlXFr7F3+75SjfJJQMkYBkoO4wStbfL7hf+EfQHRaDkw6wR95gec/yBnBFY/mvxshA+ctglD58gr7K8uYZJZDBUqbuSXES+HTTIZFBj+486jjE5F8faEb2Y0fW7UgdedPV6Jsuu3CraoyxhfbYtn32sHENfMJma7En9OFo0Sp7WX6reqMgBiW70Ogr1xoz3cRsQBgxg9POtghfI8NCiYDAsKe/rdYx3kBicps9Cel3aQ/zz3nPYtSrAjLwPYJ+PFPjni6HVt5vCq5yjo1qFLtZF0IEP3iOQbA7oibWy9msQQgpFo6ib2zW5iq9e+mCun5MmiwA=='
    assert sign_headers(headers, header_values, private_key_pem) == signature


def test_sign_headers_with_public_key():
    """Tests ``sign_headers`` with a public key.
    """
    headers = ['(request-target)', 'host', 'date', 'digest', 'content-type']
    header_values = {
        '(request-target)': 'post /users/kemoto/inbox',
        'host': 'mumble.codemonger.io',
        'date': 'Wed, 26 Apr 2023 11:32:00 GMT',
        'digest': 'SHA-256=abcdefg',
        'content-type': 'application/json',
    }
    private_key_pem = PUBLIC_KEY_PEM_1
    with pytest.raises(ValueError):
        sign_headers(headers, header_values, private_key_pem)


def test_sign_headers_with_broken_key():
    """Tests ``sign_headers`` with a broken private key.
    """
    headers = ['(request-target)', 'host', 'date', 'digest', 'content-type']
    header_values = {
        '(request-target)': 'post /users/kemoto/inbox',
        'host': 'mumble.codemonger.io',
        'date': 'Wed, 26 Apr 2023 11:32:00 GMT',
        'digest': 'SHA-256=abcdefg',
        'content-type': 'application/json',
    }
    private_key_pem = 'Please use me as a private key!'
    with pytest.raises(ValueError):
        sign_headers(headers, header_values, private_key_pem)


def test_make_signature_header():
    """Tests ``make_signature_header``.
    """
    key_id = 'https://mumble.codemonger.io/users/kemoto#main-key'
    header_values = [
        ('(request-target)', 'post /users/kemoto/inbox'),
        ('host', 'mumble.codemonger.io'),
        ('date', 'Wed, 26 Apr 2023 11:32:00 GMT'),
        ('digest', 'SHA-256=abcdefg'),
        ('content-type', 'application/json'),
    ]
    private_key_pem = PRIVATE_KEY_PEM_1
    assert make_signature_header(key_id, private_key_pem, header_values) == (
        'keyId="https://mumble.codemonger.io/users/kemoto#main-key",'
        'algorithm="rsa-sha256",'
        'headers="(request-target) host date digest content-type",'
        'signature="ZKAhY+h/a9nstRzRBlXFr7F3+75SjfJJQMkYBkoO4wStbfL7hf+EfQHRaDkw6wR95gec/yBnBFY/mvxshA+ctglD58gr7K8uYZJZDBUqbuSXES+HTTIZFBj+486jjE5F8faEb2Y0fW7UgdedPV6Jsuu3CraoyxhfbYtn32sHENfMJma7En9OFo0Sp7WX6reqMgBiW70Ogr1xoz3cRsQBgxg9POtghfI8NCiYDAsKe/rdYx3kBicps9Cel3aQ/zz3nPYtSrAjLwPYJ+PFPjni6HVt5vCq5yjo1qFLtZF0IEP3iOQbA7oibWy9msQQgpFo6ib2zW5iq9e+mCun5MmiwA=="'
    )


# private key for tests (DO NOT USE for other than tests)
# openssl genrsa -out PRIVATE_KEY_PEM_1.pem 2048
PRIVATE_KEY_PEM_1 = '''-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAnSuSfBj/vrqtSTTTZNvZNQO9dMwlKwSH0qW2fwWRFI8dRLJU
7MTSQ0pKwBhuX0gXbisM5HSCcKnvJV52m7gi5iBULDLo31TgD5qS9SDqtytJLyWH
EyFOh/cEsxW0+j7YnC0xaOJRkpXdzzLh35hNbKIKm0YnbisQ8vF8Xd15nf/U1Qzq
amutbdhJoErfPDojhlrqyAIwrmQKRZaRWKUFwVP66c775c3rLnAE+zf9yXuKGSE8
NQJByejHI3z/LIsMxNjgFXyvETTK41UFCKraIbCc8stAvxR+6TjUCsWv4RCdOq17
sijm0OVo/af6Aa6tIQFcDIefVj5OENozu6jYywIDAQABAoIBAGuzSPzq8I1VRJuO
rHFHyc7vUiswHSQeRaiOT8E5IlKxQ0Ao59MbiG3+Ab0iwLdgIlYm//2o7R2hBTRZ
R/OrOZbyfluPQ06Ozb9DkAKT3ONJsSuyjp4IS9UV602AyXRWDn7u5RXXSEink8iB
OJDMv/l6DMScTTbMIiAoZK25r7YZX17TSCjNlQ0hIvdJXKPUuxBG7EzyMu1rL5Qn
OS5OG7Ad/fHh9wdmVUhYrh8Duv/0WBENqJk2gfToELmJ2FOTVuiKbSn+Ai3QNP4+
o87oUYcvJCO//Ajx0N5duF2jTLmR5KOQUBLYc+zu1t7g5rY1tRJxyfKY5b2DxWfw
1e9x/CkCgYEAzBITU3XPSM+KbgHaOT7xqmmCNf1kBtC8FCzaq7Lz0t3CYAW7zywM
kiJ08orPhXq53YSp0JKMM+6uQeY04hKhiLwYrwXB6TvZABIfVZG3dYm+Z9d8kvV7
t2rKFep4+DikKjnXh4qICJspOrndudPtiShdv6tb8VUeCHcqHKc3fa0CgYEAxSo6
hHrf0YJmRyYuo1OBZ1yN767nvseuK0kHbm5xLW05aGijezN/OwNcp6Bd1Th0XW7f
scdqlXvn9qPYlfb56cDK4DucQ1/tg1qu294mfqQ+ahqjwkCcZm0YIdAhhIDL6D8v
63X0boT6WEo1w0yQFMRyZxKhlFmlGQTfFFMwD1cCgYEAkvXBbS0+JZUwf6Bd4zPt
HWf2GaNtUWsoxu62W0f4RzbkL/pxEfUK6IJf7fsBD4MeLuTG1ilzRkLwwwxhsRzx
r2Kl9AUVbD1pPJ/QaPMTR1X3BRkt4Tdf7Oq+taGxlDBWKQKWsEmXRXtX6a7Ienag
bVHgkZN6FwXRJw+KCDBzydECgYBwy8Dgi79CB9zldWWXEK3maR/WcHSqQ2hT4Rq8
Rbi/6U2/eqWUVRjDtR+r0mX8FqkTzttwxIoobNN+2auN19aPsTkfYVr7fITP8fA5
XvUc3G/MmeL3vaj8PAtjRMP4HwsImiWbCkdFdxQVsJbjXQjMqLpeV11TFpoKHyxU
X2cOTwKBgQC1CkOaMeNTt2Jgvempeyrqd0kkLb0nQCya3FhPojh0WTeHCCYpVOIk
qmW7ZUtmvM7DFVmn3CKYHnt4gIjeGezjp14ljkYx2r8D76j3vIIfF5BcTtoSYqvN
44milNZIb8/wvNGkpyuuKGcWytAMYPVpifHHwWXNrIIUWgkCTJsG4w==
-----END RSA PRIVATE KEY-----'''

# public key for tests
# openssl rsa -in PRIVATE_KEY_PEM_1.pem -outform PEM -pubout -out PUBLIC_KEY_PEM_1.pem
PUBLIC_KEY_PEM_1 = '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnSuSfBj/vrqtSTTTZNvZ
NQO9dMwlKwSH0qW2fwWRFI8dRLJU7MTSQ0pKwBhuX0gXbisM5HSCcKnvJV52m7gi
5iBULDLo31TgD5qS9SDqtytJLyWHEyFOh/cEsxW0+j7YnC0xaOJRkpXdzzLh35hN
bKIKm0YnbisQ8vF8Xd15nf/U1QzqamutbdhJoErfPDojhlrqyAIwrmQKRZaRWKUF
wVP66c775c3rLnAE+zf9yXuKGSE8NQJByejHI3z/LIsMxNjgFXyvETTK41UFCKra
IbCc8stAvxR+6TjUCsWv4RCdOq17sijm0OVo/af6Aa6tIQFcDIefVj5OENozu6jY
ywIDAQAB
-----END PUBLIC KEY-----'''

# another private key for tests (DO NOT USE for other than tests)
# openssl genrsa -out PRIVATE_KEY_PEM_2.pem 2048
PRIVATE_KEY_PEM_2 = '''-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEAyuYUMXs5udl0Q61F1AZE0qYGWGmJqiZnbDP7UuR01HTUBlKI
Tk0zFSREs1kLTiaojrgfShZi3MWbYPHZFTSF0DT6pOjwOYbk5Wp3C/i/A3RlEDHE
aCGpwMJL9si1hfhehG7I7jsyhor+fq5OkC5tMYvZCl7G5Ku6lMY5d5ux+MObGTRA
/3eCP3N4mWnosKpkgsx4d02fwnZbsjC8Ng6ANQbAppkz3HkEv8F8euvIQtEJy08M
vFvRAnk80TwDEMivVXI4gKGdiXd0pb8AaZvX5urPX5fWZmYFK3diCaaw2Uq39hQO
We0l8cTAcDoz04dyc0xPOt8f9+iYWmdOmDWIyQIDAQABAoIBAQDIxmHHEQvvVzoQ
Wh7WDxn9ZGK1DEI4h+YhkVKqFP1y2uSQGQ1ehk/9JLWCz6M7Q0/aYmI7+uj7U+NM
TCWnMSEVBcfcddB47H4GcpK42v2RWpVDMCwNavpCj0GCQ9w0ZLCK1eGotBVsQ5BQ
JQYC8J4GwD8WXvDriO+Jlpl5PS0gXhIHr9mIQkJdF8lNXUSIRW6zSA2Yaw/z5Uke
jZgCeEA1Nl+nmj1Gq5kYYMbtCCiBJ/duOMw38gXGGhglYiz/XS+eZBrxmd0pfUTb
l8Akf3tR6Tc3hSVhx97gWyltaV5eFfHa563dn9YaXBQc097h/Qc4cq5QkbDgXQ0j
3Na6EMgxAoGBAPvXaU/uSLO88ra9JXxmm1WFOGDPKWG+qylEC7sJRxsa1Pe/qHHv
rUhbfOR69UTeQeEJ/qoPaB5iRD02vfL6uLBhP7KYp+cCDy1TH9l0llrlJkcqK2sI
u4jMKlkJCobboAZQ429m6Fujsh19ODLZD5deEIlk4YnfPYGu7XQbgJW9AoGBAM4/
xqpoAFKBV4ASE9ZjavLlsW1FwlWqHgD9ApF3z+gzhfpRMCix4DRlZb5l5jAskd9t
7ASsrrxhLnzvX93oQT29n8XmgPetYHID/ykejwIpq8TR3qwuKyP3hU3IExdvkCSp
GIm89W994WCrwV1OqTn6rdE7O3tE1FOCWtfr8BH9AoGBAPCa9CWGfXUjPywxd5/r
k9pX5e4v3dRhyrspJJ/0FDgkIXX1aSQ5nW804RSVGMFMKtqqpuCoyYvFzHZDV6TN
vyfcMXQa/sboo8Fk2lfyWDfNGA4Djum6tRjUHl1kEueW6sM+ApyLT9FFisU7vjZu
RMQT/W6WsBf97ZB5pKk6IVZtAoGAe7h0IuqKLvPZmkC916ABmr1AZo0vGxYWM3+S
V9KoS+EEYHjtS6wQEz4z/ze/EmzaAE4/AzrXArfFHDq3pjTZVgD248721BwTu7E8
Ed176c83c7R1P5HeXQ/wzgzTrv5EWEl7J7zK+dtoJAZD0wYJq3b9Z4KBltteBs4u
UlH8y70CgYEAzmQZ8dYL3uAjzzQ5RVkzq+0pNFgDiZx0+jeOAWWGDGU5pMgNy7px
VBpW3Bjgju8hjQrnNK23cGSu2rSmibR4Y0Sw/3jNAFvukGdVPaSX22/B8U3O2iLm
WNszlYupUU7RaWByvM5IuTxJTXcBVQ5fTnUcTmKBrQDXoW7gJKvAkB8=
-----END RSA PRIVATE KEY-----'''

# another public key for tests
# openssl rsa -in PRIVATE_KEY_PEM_2.pem -outform PEM -pubout -out PUBLIC_KEY_PEM_2.pem
PUBLIC_KEY_PEM_2 = '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyuYUMXs5udl0Q61F1AZE
0qYGWGmJqiZnbDP7UuR01HTUBlKITk0zFSREs1kLTiaojrgfShZi3MWbYPHZFTSF
0DT6pOjwOYbk5Wp3C/i/A3RlEDHEaCGpwMJL9si1hfhehG7I7jsyhor+fq5OkC5t
MYvZCl7G5Ku6lMY5d5ux+MObGTRA/3eCP3N4mWnosKpkgsx4d02fwnZbsjC8Ng6A
NQbAppkz3HkEv8F8euvIQtEJy08MvFvRAnk80TwDEMivVXI4gKGdiXd0pb8AaZvX
5urPX5fWZmYFK3diCaaw2Uq39hQOWe0l8cTAcDoz04dyc0xPOt8f9+iYWmdOmDWI
yQIDAQAB
-----END PUBLIC KEY-----'''
