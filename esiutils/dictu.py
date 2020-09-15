#
# Copyright (c) 2020 Expert System Iberia
#
"""Utility methods for dicts

A lot of these are inspired in the clojure.core functions for maps
"""
import copy


def select_keys(d, keys):
    """Returns a dict containing only those entries in dict whose key is in keys

    See also select_paths

    :param d: dict to filter
    :param keys: a list of keys to select
    :returns: a copy of subset of d with only the specified keys
    :rtype: dict
    """
    return {k: copy.deepcopy(v)
            for k, v in d.items()
            if k in keys}


def select_paths(d, paths):
    """Returns a dict containing only those entries in nested dict whose path is in paths

    :param d: dict to filter
    :param paths: a list of paths, a path is a list of nested keys
    :returns: a copy of the subset of d with the specified paths
    :rtype: dict
    """
    assert type(paths) == list, "%s" % (type(paths))
    if len(paths) == 0:
        return {}
    for p in paths:
        assert type(p) == list
        assert len(p) > 0
    sub_paths = {}
    for p in paths:
        k, sp = p[0], p[1:]
        sps = sub_paths.get(k, [])
        sps.append(sp)
        sub_paths[k] = sps
    # print('Extracting subpaths', sub_paths)
    result = {}
    for k, sps in sub_paths.items():
        lens = [len(sp) for sp in sps]
        if max(lens) > 0 and 0 in lens:
            raise ValueError('One path is deeper than the other one for %s %s' % (
                k, sps))
        if max(lens) == 0:
            result[k] = copy.deepcopy(d[k])
        elif max(lens) == 1:
            result[k] = select_keys(d[k], [sp[0] for sp in sps])
        else:
            result[k] = select_paths(d[k], sps)
    return result
    
    
def get_in(dct, path, default_val=None):
    """Gets a nested value in a dict by following the path

    :param dct: a python dictionary
    :param path: a list of keys pointing to a node in dct
    :returns: the value at the specified path
    :rtype: any
    """
    if dct is None:
        return default_val
    assert len(path) > 0
    next_dct = dct.get(path[0], None)
    if len(path) == 1:
        return next_dct
    return get_in(next_dct, path[1:], default_val=default_val)

def is_value(dct, path=[]):
    """Checks that dct is a value dict. I.e. it doesn't contain functions.

    All keys and values (possibly nested), should be basic data types like str, int, 
    but (partial) functions are not allowed.

    :param dct: a dict to test
    :param path: path for the current sub-value 
    :returns: a tuple of bool and str. The bool indicates whether the `dct` is a value, 
      the str gives information about which part of the dct is not a value.
    :rtype: tuple
    """
    if type(dct) is dict:
        for k, v in dct.items():
            if type(k) not in [str, int, float]:
                return False, 'Key %s at %s is not a valid key type but %s' % (
                    k, path, type(k))
            b, msg = is_value(v, path + [k])
            if not b:
                return b, 'Value at %s is not a valid value. %s' % (
                    path + [k], msg)
        return True, ''
    assert len(path) > 0
    if dct is None:
        return True, ''
    elif type(dct) in [str, int, float]:
        return True, ''
    elif type(dct) == list:
        return is_value({i:v for
                         i, v in enumerate(dct)}, path)
    else:
        return False, 'Not a value type at %s: %s for %s' % (
            path, type(dct), dct)
    

    

