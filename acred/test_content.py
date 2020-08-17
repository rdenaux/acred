#
# Copyright (c) 2020 Expert System Iberia
#
"""Credibility reviewer for a WebSite
Implemented via the MisinfoMe source service.
"""
import pytest
from acred import content 

def test_str_as_website_01():
    ws = content.str_as_website('http://theguardian.com')
    assert ws['url'] == 'http://theguardian.com/'
    assert ws['name'] == 'theguardian.com'
    assert ws['@type'] == 'WebSite'


def test_str_as_website_02():
    ws = content.str_as_website('theguardian.com')
    assert ws['url'] == 'http://theguardian.com/'
    assert ws['name'] == 'theguardian.com'
    assert ws['@type'] == 'WebSite'


def test_is_url():
    assert not content.is_url('theguardian.com')
    assert content.is_url('http://theguardian.com')
    assert content.is_url('http://theguardian.com/a/b')


def test_domain_from_url_01():
    assert 'theguardian.com' == content.domain_from_url('http://theguardian.com/a/b')
    assert 'newsexaminer.net:80' == content.domain_from_url('https://web.archive.org/web/20150214123436/http://newsexaminer.net:80/entertainment/')

def test_try_fix_url_01():
    assert 'http://energycommerce.house.gov/108/News/02152006_1778.htm' == content.try_fix_url('http:/energycommerce.house.gov/108/News/02152006_1778.htm')
