class AppTestHashlib:
    spaceconfig = {
        "usemodules": ['_hashlib', 'array', 'struct', 'binascii'],
    }

    def test_method_names(self):
        import _hashlib
        assert isinstance(_hashlib.openssl_md_meth_names, frozenset)
        assert "md5" in _hashlib.openssl_md_meth_names

    def test_simple(self):
        import _hashlib
        assert _hashlib.new('md5').__class__.__name__ == 'HASH'
        assert len(_hashlib.new('md5').hexdigest()) == 32

    def test_attributes(self):
        import hashlib
        for name, (expected_size, expected_block_size) in {
                'md5': (16, 64),
                'sha1': (20, 64),
                'sha224': (28, 64),
                'sha256': (32, 64),
                'sha384': (48, 128),
                'sha512': (64, 128),
                }.items():
            h = hashlib.new(name)
            assert h.name == name
            assert h.digest_size == expected_size
            assert h.block_size == expected_block_size
            #
            h.update(b'abc')
            h2 = h.copy()
            h.update(b'def')
            digest = h.digest()
            hexdigest = h.hexdigest()
            h2.update(b'd')
            h2.update(b'ef')
            assert digest    == h2.digest()
            assert hexdigest == h2.hexdigest()
            assert len(digest)    == h.digest_size
            assert len(hexdigest) == h.digest_size * 2
            c_digest    = digest
            c_hexdigest = hexdigest


    def test_shortcut(self):
        import hashlib
        assert repr(hashlib.md5()).startswith("<md5 HASH object")

    def test_uppercase(self):
        import _hashlib
        h = _hashlib.new('MD5')
        assert h.digest_size == 16
        assert len(h.hexdigest()) == 32

    def test_buffer(self):
        import _hashlib, array
        b = array.array('b', b'x' * 10)
        h = _hashlib.new('md5', b)
        h.update(b)
        assert h.digest() == _hashlib.openssl_md5(b'x' * 20).digest()
        _hashlib.openssl_sha1(b).digest()

    def test_extra_algorithms(self):
        expected_results = {
            "md5": "bb649c83dd1ea5c9d9dec9a18df0ffe9",
            "md4": "c275b8454684ea416b93d7a418b43176",
            "mdc2": None,   # XXX find the correct expected value
            "sha": "e2b0a8609b47c58e5d984c9ccfe69f9b654b032b",
            "ripemd160": "cc4a5ce1b3df48aec5d22d1f16b894a0b894eccc",
            "whirlpool": ("1a22b79fe5afda02c63a25927193ed01dc718b74"
                          "026e597608ce431f9c3d2c9e74a7350b7fbb7c5d"
                          "4effe5d7a31879b8b7a10fd2f544c4ca268ecc6793923583"),
            }
        import _hashlib
        test_string = b"Nobody inspects the spammish repetition"
        for hash_name, expected in sorted(expected_results.items()):
            try:
                m = _hashlib.new(hash_name)
            except ValueError as e:
                print('skipped %s: %s' % (hash_name, e))
                continue
            m.update(test_string)
            got = m.hexdigest()
            assert got and type(got) is str and len(got) % 2 == 0
            if expected is not None:
                assert got == expected

    def test_pbkdf2(self):
        try:
            from _hashlib import pbkdf2_hmac
        except ImportError:
            skip("Requires OpenSSL >= 1.1")
        out = pbkdf2_hmac('sha1', b'password', b'salt', 1)
        assert type(out) is bytes
        assert out == '0c60c80f961f0e71f3a9b524af6012062fe037a6'.decode('hex')
        out = pbkdf2_hmac('sha1', b'password', b'salt', 2, None)
        assert out == 'ea6c014dc72d6f8ccd1ed92ace1d41f0d8de8957'.decode('hex')
        raises(TypeError, pbkdf2_hmac, 'sha1', 'password', b'salt', 1)
        raises(TypeError, pbkdf2_hmac, 'sha1', b'password', 'salt', 1)
