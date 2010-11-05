import py
from pypy.conftest import gettestobjspace

class AppTestHashlib:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_hashlib'])

    def test_simple(self):
        import _hashlib
        assert _hashlib.new('md5').__class__.__name__ == 'HASH'
        assert len(_hashlib.new('md5').hexdigest()) == 32

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
            py_new = getattr(hashlib, '__get_builtin_constructor')
            h = py_new(name)('')
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

    def test_shortcut(self):
        import hashlib
        assert repr(hashlib.md5()).startswith("<md5 HASH object")

    def test_unicode(self):
        import _hashlib
        assert _hashlib.new('sha1', u'xxx').__class__.__name__ == 'HASH'

    def test_uppercase(self):
        import _hashlib
        h = _hashlib.new('MD5')
        assert h.digest_size == 16
        assert len(h.hexdigest()) == 32

    def test_buffer(self):
        import _hashlib, array
        b = array.array('b', 'x' * 10)
        h = _hashlib.new('md5', b)
        h.update(b)
        assert h.digest() == _hashlib.openssl_md5('x' * 20).digest()
        _hashlib.openssl_sha1(b).digest()

