
from pypy.rlib.rvector import (vector_float_read, vector_float_write,
                               vector_float_add)
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.test_llinterp import interpret

TP = lltype.Array(lltype.Float, hints={'nolength': True})

class TestRVector(object):
    def test_direct_add(self):
        a = lltype.malloc(TP, 16, flavor='raw')
        b = lltype.malloc(TP, 16, flavor='raw')
        res = lltype.malloc(TP, 16, flavor='raw')
        a[0] = 1.2
        a[1] = 1.3
        b[0] = 0.1
        b[1] = 0.3
        a[10] = 8.3
        a[11] = 8.1
        b[10] = 7.8
        b[11] = 7.6
        f1 = vector_float_read(a, 0)
        f2 = vector_float_read(b, 0)
        vector_float_write(res, 2, vector_float_add(f1, f2))
        assert res[2] == 1.2 + 0.1
        assert res[3] == 1.3 + 0.3
        f1 = vector_float_read(a, 10)
        f2 = vector_float_read(b, 10)
        vector_float_write(res, 8, vector_float_add(f1, f2))
        assert res[8] == 8.3 + 7.8
        assert res[9] == 8.1 + 7.6
        lltype.free(a, flavor='raw')
        lltype.free(b, flavor='raw')
        lltype.free(res, flavor='raw')

    def test_interpret(self):
        def f():
            a = lltype.malloc(TP, 16, flavor='raw')
            b = lltype.malloc(TP, 16, flavor='raw')
            res = lltype.malloc(TP, 16, flavor='raw')
            try:
                a[0] = 1.2
                a[1] = 1.3
                b[0] = 0.1
                b[1] = 0.3
                f1 = vector_float_read(a, 0)
                f2 = vector_float_read(b, 0)
                vector_float_write(res, 8, vector_float_add(f1, f2))
                return res[8] * 100 + res[9]
            finally:
                lltype.free(a, flavor='raw')
                lltype.free(b, flavor='raw')
                lltype.free(res, flavor='raw')

        res = interpret(f, [])
        assert res == f()
