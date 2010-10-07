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

    def test_casts_1(self):
        class A:
            pass
        class B(A):
            pass
        def dummyfn(n):
            if n > 5:
                # this tuple is allocated as a (*, Void) tuple, and immediately
                # converted into a generic (*, *) tuple.
                x = (B(), None)
            else:
                x = (A(), A())
            return x[0]
        res = self.interpret(dummyfn, [8])
        assert self.is_of_instance_type(res)

    def test_dict_recast(self):
        from pypy.rlib.objectmodel import r_dict
        class A(object):
            pass
        def myeq(n, m):
            return n == m
        def myhash(a):
            return 42
        def fn():
            d = r_dict(myeq, myhash)
            d[4] = A()
            a = d.values()[0]
            a.x = 5
        self.interpret(fn, [])
