#
# Copyright (c) 2020 Expert System Iberia
#
"""Provies standard hashing functions for various content types"""
import hashlib
import base64
import json


def calc_str_hash(s):
    """Returns the MD5 hash for the input string

    :param s: a string
    :returns: a "clean" b64 encoded MD5 digest for the string
    :rtype: str
    """
    assert type(s) == str
    return calc_md5_id(s.encode('utf-8'))


def hash_dict(d, str_encoding='base64'):
    """Returns the hash string for an input dict
    
    :param d: dict to hash

    :param str_encoding: how to encode the hash. The undelying hash
      function is always sha256, but the standard hexdigest tends to
      be quite large. To get shorter hashes, you can provide an
      alternative encoding. Supported values are: , (url safe)
      'base64' (defualt), 'ascii85' (default) or just 'hexdigest'

    :returns: hash string for dict
    :rtype: str
    """
    s = json.dumps(d, sort_keys=True)
    def str_as_bytesiter(s):
        yield s.encode()
    assert str_encoding in ['hexdigest', 'base64', 'ascii85']
    hfn, byter = hashlib.sha256(), str_as_bytesiter(s)
    if str_encoding == 'hexdigest':
        return hash_bytesiter(byter, hasher=hfn, ashexstr=True)
    elif str_encoding == 'ascii85':
        return base64.a85encode(
            hash_bytesiter(byter, hasher=hfn)).decode('utf-8')
    else:  # assume str_encoding == 'base64'
        return clean_b64(base64.urlsafe_b64encode(
            hash_bytesiter(byter, hasher=hfn)).decode('utf-8'))

    
def sha256_file(path):
    """Returns the sha256 hexdigest string of the contents of a file

    :param path: path to the file to hash
    :returns: the sha256 hexdigest string of the contents of the file
    :rtype: str
    """
    return hash_bytesiter(
        file_as_blockiter(path),
        hasher=hashlib.sha256(),
        ashexstr=True)


def hash_bytesiter(bytesiter, hasher, ashexstr=False):
    """Calculates the hash of an interation of bytes

    :param bytesiter: an iterator of bytes
    :param hasher: a hasher function like `hashlib.md5()` or `hashlib.sha256()`
    :param ashexstr: whether to output the hexdigest or the normal packed bytes digest 
    :returns: either a bytes object or a str if `ashexstr`
    :rtype: bytes or str
    """
    for block in bytesiter:
        hasher.update(block)
    return hasher.hexdigest() if ashexstr else hasher.digest()


def file_as_blockiter(afile, blocksize=65536):
    """Reads afile in blocks and returns a bytes iterator

    To be used in conjunction with e.g. `hash_bytesiter`

    :param afile: 
    :param blocksize: 
    :returns: 
    :rtype: 

    """
    if type(afile) == str:
        # assume this is the path
        afile = open(afile, 'rb')
    with afile:
        block = afile.read(blocksize)
        while len(block) > 0:
            yield block
            block = afile.read(blocksize)


def calc_md5_id(bs):
    assert type(bs) == bytes, 'Expecting bytes, but got' % (
        type(bs))
    md5 = hashlib.md5(bs).digest()
    b64 = base64.urlsafe_b64encode(md5)
    return clean_b64(b64.decode('utf-8'))


def clean_b64(b64_str):
    """Cleans a base64 encoding to be more amenable as an ID in a URL

    :param b64_str:
    :returns:
    :rtype:
    """
    assert type(b64_str) == str
    result = b64_str.replace("=", "")  # remove padding
    return result
