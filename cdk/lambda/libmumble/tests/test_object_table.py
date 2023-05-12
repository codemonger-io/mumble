# -*- coding: utf-8 -*-

"""Tests ``libmumble.object_table``.
"""

import datetime
from libmumble.object_table import format_yyyymm


def test_format_yyyymm():
    """Tests ``format_yyyymm`` with ``date(2023, 5, 12)``.
    """
    date = datetime.date(2023, 5, 12)
    assert format_yyyymm(date) == '2023-05'
