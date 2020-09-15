#
# Copyright (c) 2020 Expert System Iberia
#
"""Provides methods to help describe `Bot` instances
"""
import platform
import socket
import os
from esiutils import isodate, hashu


def esiLab_organization():
    """Returns the standard ESI Lab Madrid Organization dict

    :returns: the standard ESI Lab Madrid Organization dict
    :rtype: dict
    """
    return {
        '@type': 'Organization',
        'name': 'Expert System Lab Madrid',
        'url': 'http://expertsystem.com'
    }


def inspect_execution_env():
    """Returns a dict describing the current execution environment

    :returns: 
    :rtype: dict
    """
    return {
        'python.version': platform.python_version(),
        'hostname': socket.gethostname()
    }


def path_as_media_object(path):
    """Returns a MediaObject dict for the file at `path`

    :param path: path to a local file
    :returns: a MediaObject dict including a `sha256Digest` and other
      relevant fields
    :rtype: dict
    """
    if not os.path.isfile(path):
        return None
    return {
        '@type': 'MediaObject',
        'name': os.path.basename(path),
        'sha256Digest': hashu.sha256_file(path),
        'contentSize': readable_file_size(path),
        'dateCreated': isodate.as_utc_timestamp(os.path.getctime(path)),
        'dateModified': isodate.as_utc_timestamp(os.path.getmtime(path))
    }


def readable_file_size(path):
    return _bytes_to_size_str(os.path.getsize(path))
    

def _bytes_to_size_str(s_bytes):
    assert type(s_bytes) == int, '%s' (type(s_bytes))
    K = 1024
    if s_bytes < 2 * K:
        return '%s B' % s_bytes
    elif s_bytes < 2 * K * K:
        return '%.2f KB' % (s_bytes / K)
    elif s_bytes < 2 * (K**3):
        return '%.2f MB' % (s_bytes / (K * K))
    elif s_bytes < 2 * (K**4):
        return '%.2f GB' % (s_bytes / (K**3))
    else:
        return '%.2f TB' % (s_bytes / (K**4))

