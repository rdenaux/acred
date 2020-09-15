#
# Copyright (c) 2020 Expert System Iberia
#
"""Tests methods in bot_desriber
"""
import pytest
from esiutils import bot_describer


def test_path_as_media_object_01():
    mobj = bot_describer.path_as_media_object('doc/ES-logo-1-std-rgb-A-72.png')
    expected = {
        '@type': 'MediaObject',
        'contentSize': '3.34 KB',
        'dateCreated': '2020-06-10T17:32:23.856191Z',
        'dateModified': '2019-02-28T09:36:47Z',
        'name': 'ES-logo-1-std-rgb-A-72.png',
        'sha256Digest': '81bf532ca7f55ab9920a2fb398e2ba47604cab29982bb01afe75f5eb4d777fae'
    }
    assert expected == mobj
    

def test_bytes_to_size_str():
    cases = {
        0: '0 B',
        1024: '1024 B',
        4256: '4.16 KB',
        12568972: '11.99 MB',
        31614681: '30.15 MB',
        3161468131614681: '2875.34 TB'
    }
    for s, expected in cases.items():
        assert bot_describer._bytes_to_size_str(s) == expected


