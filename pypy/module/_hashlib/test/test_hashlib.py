import py
from pypy.conftest import gettestobjspace

class AppTestHashlib:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_hashlib'])

    def test_simple(self):
        import _hashlib
        assert isinstance(_hashlib.new('md5'), _hashlib.HASH)

    def test_attributes(self):
        import hashlib
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
            assert digest    == h2.digest()
            assert hexdigest == h2.hexdigest()
            assert len(digest)    == h.digest_size
            assert len(hexdigest) == h.digest_size * 2
            c_digest    = digest
            c_hexdigest = hexdigest

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
            assert digest    == h2.digest()
            assert hexdigest == h2.hexdigest()

            # compare both implementations
            assert c_digest    == digest
            assert c_hexdigest == hexdigest

    def test_unicode(self):
        import _hashlib
        assert isinstance(_hashlib.new('sha1', u'xxx'), _hashlib.HASH)

