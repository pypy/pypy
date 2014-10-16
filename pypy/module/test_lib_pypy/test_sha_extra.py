"""Testing sha module (NIST's Secure Hash Algorithm)

use the three examples from Federal Information Processing Standards
Publication 180-1, Secure Hash Standard,  1995 April 17
http://www.itl.nist.gov/div897/pubs/fip180-1.htm
"""
from pypy.module.test_lib_pypy.support import import_lib_pypy


class AppTestSHA:
    spaceconfig = dict(usemodules=('struct',))

    def setup_class(cls):
        cls.w__sha = import_lib_pypy(cls.space, '_sha')

    def w_check(self, data, digest):
        computed = self._sha.new(data).hexdigest()
        assert computed == digest

    def test_case_1(self):
        self.check("abc",
                   "a9993e364706816aba3e25717850c26c9cd0d89d")

    def test_case_2(self):
        self.check("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
                   "84983e441c3bd26ebaae4aa1f95129e5e54670f1")

    def disabled_too_slow_test_case_3(self):
        self.check("a" * 1000000,
                   "34aa973cd4c4daa4f61eeb2bdbad27316534016f")

    def test_attributes(self):
        _sha = self._sha
        assert _sha.digest_size == 20
        assert _sha.digestsize == 20
        assert _sha.blocksize == 1
        assert _sha.new().digest_size == 20
        assert _sha.new().digestsize == 20
        assert _sha.new().block_size == 64
