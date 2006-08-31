import py
from pypy.conftest import gettestobjspace

py.test.skip("XXX missing _random.sample()")

class AppTestRandom:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_random'])

    def test_dict(self):
        import _random
        _random.__dict__  # crashes if entries in __init__.py can't be resolved

    # XXX MISSING TESTS XXX
    # XXX MISSING TESTs XXX
    # XXX MISSING TESTS XXX
