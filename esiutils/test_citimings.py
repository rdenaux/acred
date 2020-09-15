#
# Copyright (c) 2020 Expert System Iberia
#
"""Tests methods in isodate
"""
import pytest
from esiutils import citimings
from time import sleep

def test_basic():
    f_out = f()
    assert 'timings' in f_out
    expected = {
        '@context': 'http://expertsystem.com',
        '@type': 'Timing',
        'phase': 'f',
        'sub_timings': [],
        'total_ms': 50}
    assert f_out['timings'] == expected

def test_composite():
    fc_out = f_composite()
    assert 'timings' in fc_out
    expected = {
        '@context': 'http://expertsystem.com',
        '@type': 'Timing',
        'phase': 'f_composite',
        'sub_timings': [
            {
                '@context': 'http://expertsystem.com',
                '@type': 'Timing',
                'phase': 'f',
                'sub_timings': [],
                'total_ms': 50},
            {
                '@context': 'http://expertsystem.com',
                '@type': 'Timing',
                'phase': 'g',
                'sub_timings': [],
                'total_ms': 100}
        ],
        'total_ms': 160
    }
    assert fc_out['timings'] == expected


def f():
    start = citimings.start()
    sleep(0.05)
    result = {
        'a': 'b',
        'c': 'd',
        'timings': citimings.timing('f', start)
    }
    return result

def g():
    start = citimings.start()
    sleep(0.1)
    return {
        'e': 'f',
        'g': 'h',
        'timings': citimings.timing('g', start)
    }
    
def f_composite():
    start = citimings.start()
    sleep(0.01)
    f_out = f()
    g_out = g()
    result = {
        **f_out,
        **g_out,
        'timings': citimings.timing(
            'f_composite', start,
            [p['timings'] for p in [f_out, g_out]
             if p and type(p) is dict and 'timings' in p])
    }
    return result
    
