import py
from pypy.conftest import gettestobjspace

class AppTestHashlib:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_hashlib'])

    def test_simple(self):
        import _hashlib
        assert isinstance(_hashlib.new('md5'), _hashlib.HASH)

    def test_attributes(self):
        import _hashlib
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
            h = hashlib.__get_builtin_constructor(name)('')
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

    def test_unicode(self):
        import _hashlib
        assert isinstance(hashlib.new('sha1', u'xxx'), _hashlib.HASH)

