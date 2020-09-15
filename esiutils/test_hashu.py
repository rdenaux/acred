#
# Copyright (c) 2020 Expert System Iberia
#
"""Tests methods in hashu
"""
import pytest
from esiutils import hashu


## Test hash_dict ##

def test_hash_dict_01():
    # test order independence
    hash1 = hashu.hash_dict({'a': 'b', 'c': 'd'})
    hash2 = hashu.hash_dict({'c': 'd', 'a': 'b'})
    assert hash1 == hash2

    
def test_hash_dict_02():
    # test order independence in nested values
    d1 = {
        'a': {
            'a1': 'b1',
            'a2': 'b2',
            'a3': 8.12541
        }}
    d2 = {
        'a': {
            'a3': 8.12541,
            'a1': 'b1',
            'a2': 'b2'
        }}
    hash1 = hashu.hash_dict(d1)
    hash2 = hashu.hash_dict(d2)
    assert hash1 == hash2

## Test calc_str_hash ##

def test_str_hash_01():
    assert '1B2M2Y8AsgTpgAmY7PhCfg' == hashu.calc_str_hash('')
    assert 'nNOON2qEiDomSOKBUuD5xQ' == hashu.calc_str_hash('ExpertSystem')
    with pytest.raises(AssertionError):
        hashu.calc_str_hash(None)
    with pytest.raises(AssertionError):
        hashu.calc_str_hash(42)


## Test sha256_file ##

def test_sha256_file_01():
    assert '81bf532ca7f55ab9920a2fb398e2ba47604cab29982bb01afe75f5eb4d777fae' == hashu.sha256_file('doc/ES-logo-1-std-rgb-A-72.png')
