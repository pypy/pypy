import py
from pypy.config.translationoption import IS_64_BITS
from pypy.rpython.test import test_rclass


def setup_module(mod):
    if not IS_64_BITS:
        py.test.skip("for 64-bits only")


class MixinCompressed64(object):
    def _get_config(self):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.compressptr = True
        return config

    def interpret(self, *args, **kwds):
        kwds['config'] = self._get_config()
        return super(MixinCompressed64, self).interpret(*args, **kwds)

    def interpret_raises(self, *args, **kwds):
        kwds['config'] = self._get_config()
        return super(MixinCompressed64, self).interpret_raises(*args, **kwds)


class TestLLtype64(MixinCompressed64, test_rclass.TestLLtype):
    pass
