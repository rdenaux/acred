#
# Copyright (c) 2020 Expert System Iberia
#
"""Tests methods in isodate
"""
import pytest
from esiutils import isodate
import datetime

def test_as_utc_timestamp_01():
    assert '1970-01-01T12:40:00.420000Z' == isodate.as_utc_timestamp(42000.42)
    assert '2007-12-05T00:00:00Z' == isodate.as_utc_timestamp(datetime.date(2007, 12, 5))
    assert '2007-12-05T13:42:42.000042Z' == isodate.as_utc_timestamp(datetime.datetime(2007, 12, 5, 13, 42, 42, 42))

def test_start_of_week_utc_timestamp_01():
    assert '1970-01-01T12:40:00.420000Z' == isodate.as_utc_timestamp(42000.42)
    assert '2007-12-05T13:42:42.000042Z' == isodate.as_utc_timestamp(datetime.datetime(2007, 12, 5, 13, 42, 42, 42))


def test_is_valid_iso8601_dt_01():
    assert isodate.is_valid_iso8601_dt('2020-01-17T23:18:45.431Z')
    assert not isodate.is_valid_iso8601_dt('2020-01-17')
    assert not isodate.is_valid_iso8601_dt('23:18:45.431Z')

def test_parse_iso8601_dt_01():
    dt_str = '2020-01-17T23:18:45.431Z'
    dt = isodate.parse_iso8601_dt(dt_str)
    print('type', type(dt))
    assert type(dt) == datetime.datetime
    assert '2020-01-17T23:18:45.431000Z' == isodate.as_utc_timestamp(dt)



 
