from __future__ import absolute_import
from ..ctypes_config_cache import rebuild
rebuild.rebuild_one('hashlib.ctc.py')

from . import hack___pypy__
from .. import hashlib, _hashlib

def test_unicode():
    assert isinstance(hashlib.new('sha256', u'xxx'), _hashlib.hash)

pure_python_version = {
    'md5': 'md5.new',
    'sha1': 'sha.new',
    'sha224': '_sha256.sha224',
    'sha256': '_sha256.sha256',
    'sha384': '_sha512.sha384',
    'sha512': '_sha512.sha512',
    }

def test_attributes():
    for name, expected_size in {'md5': 16,
                                'sha1': 20,
                                'sha224': 28,
                                'sha256': 32,
                                'sha384': 48,
                                'sha512': 64,
                                }.items():
        h = hashlib.new(name)
        assert h.digest_size == expected_size
        assert h.digestsize == expected_size
        #
        h.update('abc')
        h2 = h.copy()
        h.update('def')
        digest = h.digest()
        hexdigest = h.hexdigest()
        h2.update('d')
        h2.update('ef')
        assert digest == h.digest()
        assert hexdigest == h.hexdigest()

        # also test the pure Python implementation
        modname, constructor = pure_python_version[name].split('.')
        mod = __import__('lib_pypy.' + modname, None, None, ['__doc__'])
        builder = getattr(mod, constructor)
        h = builder('')
        assert h.digest_size == expected_size
        assert h.digestsize == expected_size
        #
        h.update('abc')
        h2 = h.copy()
        h.update('def')
        digest = h.digest()
        hexdigest = h.hexdigest()
        h2.update('d')
        h2.update('ef')
        assert digest == h.digest()
        assert hexdigest == h.hexdigest()
