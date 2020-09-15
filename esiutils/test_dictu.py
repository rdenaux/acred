#
# Copyright (c) 2020 Expert System Iberia
#
"""Tests methods in dictu
"""
import pytest
from esiutils import dictu

def test_select_keys_01():
    d1 = {'a': 1, 'b': 2}
    d2 = {'a': 1}
    d3 = dictu.select_keys(d1, ['a'])
    assert d2 == d3

def test_select_keys_02():
    d1 = {'a': 1, 'b': 2,
          'c': {
              'd': 'e',
              'f': 'g'}}
    d2 = {'a': 1,
          'c': {
              'd': 'e',
              'f': 'g'}}
    d3 = dictu.select_keys(d1, ['a', 'c'])
    assert d2 == d3

    
def test_select_keys_03():
    d1 = {'a': 1, 'b': 2}
    d3 = dictu.select_keys(d1, [])
    assert {} == d3


def test_select_keys_04():
    d1 = {'a': 1, 'b': 2}
    d3 = dictu.select_keys(d1, ['e'])
    assert {} == d3


def test_select_paths_01():
    d1 = {'a': 1, 'b': 2}
    d2 = {'a': 1}
    d3 = dictu.select_paths(d1, [
        ['a']])
    assert d2 == d3
    
def test_select_paths_02():
    d1 = {'a': 1, 'b': 2,
          'c': {
              'd': 'e',
              'f': 'g'}}
    d2 = {'a': 1,
          'c': {
              'd': 'e'}}
    d3 = dictu.select_paths(d1, [['a'], ['c', 'd']])
    assert d2 == d3


def test_select_paths_03():
    d1 = {'a': 1, 'b': 2,
          'c': {
              'd': 'e',
              'f': 'g'}}
    d2 = {'a': 1,
          'c': {
              'd': 'e'}}
    with pytest.raises(ValueError) as excinfo:
        d3 = dictu.select_paths(d1, [['c'], ['c', 'd']])
    assert 'One path is deeper' in str(excinfo.value)
    
