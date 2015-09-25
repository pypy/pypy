import py

from rpython.jit.metainterp.warmspot import ll_meta_interp, get_stats
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.jit.codewriter.policy import StopAtXPolicy
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp import history
from rpython.rlib.jit import JitDriver, hint, set_param
from rpython.rlib.objectmodel import compute_hash
from rpython.rlib import rfloat
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rlib.rawstorage import (alloc_raw_storage, raw_storage_setitem,
                                     free_raw_storage, raw_storage_getitem)

def malloc(T,n):
    return lltype.malloc(T, n, flavor='raw', zero=True)
def free(mem):
    lltype.free(mem, flavor='raw')

class VectorizeTests:
    enable_opts = 'intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unroll'

    def setup_method(self, method):
        print "RUNNING", method.__name__

    def meta_interp(self, f, args, policy=None, vec=True, vec_all=False):
        return ll_meta_interp(f, args, enable_opts=self.enable_opts,
                              policy=policy,
                              CPUClass=self.CPUClass,
                              type_system=self.type_system,
                              vec=vec, vec_all=vec_all)

    @py.test.mark.parametrize('i',[3,4,5,6,7,8,9,50])
    def test_vectorize_simple_load_arith_store_int_add_index(self,i):
        myjitdriver = JitDriver(greens = [],
                                reds = 'auto',
                                vectorize=True)
        def f(d):
            bc = d*rffi.sizeof(rffi.SIGNED)
            va = alloc_raw_storage(bc, zero=True)
            vb = alloc_raw_storage(bc, zero=True)
            vc = alloc_raw_storage(bc, zero=True)
            x = 1
            for i in range(d):
                j = i*rffi.sizeof(rffi.SIGNED)
                raw_storage_setitem(va, j, rffi.cast(rffi.SIGNED,i))
                raw_storage_setitem(vb, j, rffi.cast(rffi.SIGNED,i))
            i = 0
            while i < bc:
                myjitdriver.jit_merge_point()
                a = raw_storage_getitem(rffi.SIGNED,va,i)
                b = raw_storage_getitem(rffi.SIGNED,vb,i)
                c = a+b
                raw_storage_setitem(vc, i, rffi.cast(rffi.SIGNED,c))
                i += 1*rffi.sizeof(rffi.SIGNED)
            res = 0
            for i in range(d):
                res += raw_storage_getitem(rffi.SIGNED,vc,i*rffi.sizeof(rffi.SIGNED))

            free_raw_storage(va)
            free_raw_storage(vb)
            free_raw_storage(vc)
            return res
        res = self.meta_interp(f, [i])
        assert res == f(i)

    @py.test.mark.parametrize('i',[1,2,3,8,17,128,130,131,142,143])
    def test_vectorize_array_get_set(self,i):
        myjitdriver = JitDriver(greens = [],
                                reds = 'auto',
                                vectorize=True)
        T = lltype.Array(rffi.INT, hints={'nolength': True})
        def f(d):
            i = 0
            va = lltype.malloc(T, d, flavor='raw', zero=True)
            vb = lltype.malloc(T, d, flavor='raw', zero=True)
            vc = lltype.malloc(T, d, flavor='raw', zero=True)
            for j in range(d):
                va[j] = rffi.r_int(j)
                vb[j] = rffi.r_int(j)
            while i < d:
                myjitdriver.jit_merge_point()

                a = va[i]
                b = vb[i]
                ec = intmask(a)+intmask(b)
                vc[i] = rffi.r_int(ec)

                i += 1
            res = 0
            for j in range(d):
                res += intmask(vc[j])
            lltype.free(va, flavor='raw')
            lltype.free(vb, flavor='raw')
            lltype.free(vc, flavor='raw')
            return res
        res = self.meta_interp(f, [i])
        assert res == f(i)

    @py.test.mark.parametrize('i',[1,2,3,4,9])
    def test_vector_register_too_small_vector(self, i):
        myjitdriver = JitDriver(greens = [],
                                reds = 'auto',
                                vectorize=True)
        T = lltype.Array(rffi.SHORT, hints={'nolength': True})

        def g(d, va, vb):
            i = 0
            while i < d:
                myjitdriver.jit_merge_point()
                a = va[i]
                b = vb[i]
                ec = intmask(a) + intmask(b)
                va[i] = rffi.r_short(ec)
                i += 1

        def f(d):
            i = 0
            va = lltype.malloc(T, d+100, flavor='raw', zero=True)
            vb = lltype.malloc(T, d+100, flavor='raw', zero=True)
            for j in range(d+100):
                va[j] = rffi.r_short(1)
                vb[j] = rffi.r_short(2)

            g(d+100, va, vb)
            g(d, va, vb) # this iteration might not fit into the vector register

            res = intmask(va[d])
            lltype.free(va, flavor='raw')
            lltype.free(vb, flavor='raw')
            return res
        res = self.meta_interp(f, [i])
        assert res == f(i) == 3

    def test_vectorize_max(self):
        myjitdriver = JitDriver(greens = [],
                                reds = 'auto',
                                vectorize=True)
        def fmax(v1, v2):
            return v1 if v1 >= v2 or rfloat.isnan(v2) else v2
        T = lltype.Array(rffi.DOUBLE, hints={'nolength': True})
        def f(d):
            i = 0
            va = lltype.malloc(T, d, flavor='raw', zero=True)
            for j in range(d):
                va[j] = float(j)
            va[13] = 128.0
            m = -128.0
            while i < d:
                myjitdriver.jit_merge_point()
                a = va[i]
                m = fmax(a, m)
                i += 1
            lltype.free(va, flavor='raw')
            return m
        res = self.meta_interp(f, [30])
        assert res == f(30) == 128

    @py.test.mark.parametrize('type,func,init,insert,at,count,breaks',
            # all
           [(rffi.DOUBLE, lambda x: not bool(x), 1.0, None, -1,32, False),
            (rffi.DOUBLE, lambda x: x == 0.0,    1.0, None, -1,33, False),
            (rffi.DOUBLE, lambda x: x == 0.0,    1.0, 0.0,  33,34, True),
            (lltype.Signed, lambda x: not bool(x), 1, None, -1,32, False),
            (lltype.Signed, lambda x: x == 0,      1, None, -1,33, False),
            (lltype.Signed, lambda x: x == 0,      1, 0,  33,34, True),
            # any
            (rffi.DOUBLE, lambda x: x != 0.0,    0.0, 1.0,  33,35, True),
            (rffi.DOUBLE, lambda x: x != 0.0,    0.0, 1.0,  -1,36, False),
            (rffi.DOUBLE, lambda x: bool(x),     0.0, 1.0,  33,37, True),
            (rffi.DOUBLE, lambda x: bool(x),     0.0, 1.0,  -1,38, False),
            (lltype.Signed, lambda x: x != 0,    0, 1,  33,35, True),
            (lltype.Signed, lambda x: x != 0,    0, 1,  -1,36, False),
            (lltype.Signed, lambda x: bool(x),   0, 1,  33,37, True),
            (lltype.Signed, lambda x: bool(x),   0, 1,  -1,38, False),
            (rffi.INT, lambda x: intmask(x) != 0,    rffi.r_int(0), rffi.r_int(1),  33,35, True),
            (rffi.INT, lambda x: intmask(x) != 0,    rffi.r_int(0), rffi.r_int(1),  -1,36, False),
            (rffi.INT, lambda x: bool(intmask(x)),   rffi.r_int(0), rffi.r_int(1),  33,37, True),
            (rffi.INT, lambda x: bool(intmask(x)),   rffi.r_int(0), rffi.r_int(1),  -1,38, False),
           ])
    def test_bool_reduction(self, type, func, init, insert, at, count, breaks):
        myjitdriver = JitDriver(greens = [], reds = 'auto', vectorize=True)
        T = lltype.Array(type, hints={'nolength': True})
        def f(d):
            va = lltype.malloc(T, d, flavor='raw', zero=True)
            for i in range(d): va[i] = init
            if at != -1:
                va[at] = insert
            i = 0 ; nobreak = False
            while i < d:
                myjitdriver.jit_merge_point()
                if func(va[i]):
                    break
                i += 1
            else:
                nobreak = True
            lltype.free(va, flavor='raw')
            return not nobreak
        res = self.meta_interp(f, [count])
        assert res == f(count) == breaks

    def test_sum(self):
        myjitdriver = JitDriver(greens = [], reds = 'auto', vectorize=True)
        T = lltype.Array(rffi.DOUBLE, hints={'nolength': True})
        def f(d):
            va = lltype.malloc(T, d, flavor='raw', zero=True)
            for j in range(d):
                va[j] = float(j)
            i = 0
            accum = 0
            while i < d:
                myjitdriver.jit_merge_point()
                accum += va[i]
                i += 1
            lltype.free(va, flavor='raw')
            return accum
        res = self.meta_interp(f, [60])
        assert res == f(60) == sum(range(60))

    def test_constant_expand(self):
        myjitdriver = JitDriver(greens = [], reds = 'auto', vectorize=True)
        T = lltype.Array(rffi.DOUBLE, hints={'nolength': True})
        def f(d):
            va = lltype.malloc(T, d, flavor='raw', zero=True)
            i = 0
            while i < d:
                myjitdriver.jit_merge_point()
                va[i] = va[i] + 34.5
                i += 1
            val = va[0]
            lltype.free(va, flavor='raw')
            return val
        res = self.meta_interp(f, [60])
        assert res == f(60) == 34.5

    def test_constant_expand_vec_all(self):
        myjitdriver = JitDriver(greens = [], reds = 'auto')
        T = lltype.Array(rffi.DOUBLE, hints={'nolength': True})
        def f(d):
            va = lltype.malloc(T, d, flavor='raw', zero=True)
            i = 0
            while i < d:
                myjitdriver.jit_merge_point()
                if not (i < d):
                    raise IndexError
                va[i] = va[i] + 34.5
                i += 1
            val = va[0]
            lltype.free(va, flavor='raw')
            return val
        res = self.meta_interp(f, [60], vec_all=True)
        assert res == f(60) == 34.5

    def test_variable_expand(self):
        myjitdriver = JitDriver(greens = [], reds = 'auto', vectorize=True)
        T = lltype.Array(rffi.DOUBLE, hints={'nolength': True})
        def f(d,variable):
            va = lltype.malloc(T, d, flavor='raw', zero=True)
            i = 0
            while i < d:
                myjitdriver.jit_merge_point()
                va[i] = va[i] + variable
                i += 1
            val = va[0]
            lltype.free(va, flavor='raw')
            return val
        res = self.meta_interp(f, [60,58.4547])
        assert res == f(60,58.4547) == 58.4547

    @py.test.mark.parametrize('vec,vec_all',[(False,True),(True,False),(True,True),(False,False)])
    def test_accum(self, vec, vec_all):
        myjitdriver = JitDriver(greens = [], reds = 'auto', vectorize=vec)
        T = lltype.Array(rffi.DOUBLE)
        def f(d, value):
            va = lltype.malloc(T, d, flavor='raw', zero=True)
            for i in range(d):
                va[i] = value
            r = 0
            i = 0
            k = d + 2
            # in this case a guard k <= d is inserted which fails right away!
            while i < d:
                myjitdriver.jit_merge_point()
                if not(i < k):
                    k -= 1
                r += va[i]
                i += 1
            lltype.free(va, flavor='raw')
            return r
        res = self.meta_interp(f, [60,0.5], vec=vec, vec_all=vec_all)
        assert res == f(60,0.5) == 60*0.5


    @py.test.mark.parametrize('i',[15])
    def test_array_bounds_check_elimination(self,i):
        myjitdriver = JitDriver(greens = [],
                                reds = 'auto',
                                vectorize=True)
        T = lltype.Array(rffi.INT, hints={'nolength': True})
        def f(d):
            va = lltype.malloc(T, d, flavor='raw', zero=True)
            vb = lltype.malloc(T, d, flavor='raw', zero=True)
            for j in range(d):
                va[j] = rffi.r_int(j)
                vb[j] = rffi.r_int(j)
            i = 0
            while i < d:
                myjitdriver.jit_merge_point()

                if i < 0:
                    raise IndexError
                if i >= d:
                    raise IndexError
                a = va[i]
                if i < 0:
                    raise IndexError
                if i >= d:
                    raise IndexError
                b = vb[i]
                ec = intmask(a)+intmask(b)
                if i < 0:
                    raise IndexError
                if i >= d:
                    raise IndexError
                va[i] = rffi.r_int(ec)

                i += 1
            lltype.free(va, flavor='raw')
            lltype.free(vb, flavor='raw')
            return 0
        res = self.meta_interp(f, [i])
        assert res == f(i)

    @py.test.mark.parametrize('i,v1,v2',[(25,2.5,0.3),(25,2.5,0.3)])
    def test_list_vectorize(self,i,v1,v2):
        myjitdriver = JitDriver(greens = [],
                                reds = 'auto')
        class ListF(object):
            def __init__(self, size, init):
                self.list = [init] * size
            def __getitem__(self, key):
                return self.list[key]
            def __setitem__(self, key, value):
                self.list[key] = value
        def f(d, v1, v2):
            a = ListF(d, v1)
            b = ListF(d, v2)
            i = 0
            while i < d:
                myjitdriver.jit_merge_point()
                a[i] = a[i] + b[i]
                i += 1
            s = 0
            for i in range(d):
                s += a[i]
            return s
        res = self.meta_interp(f, [i,v1,v2], vec_all=True)
        # sum helps to generate the rounding error of floating points
        # return 69.999 ... instead of 70, (v1+v2)*i == 70.0
        assert res == f(i,v1,v2) == sum([v1+v2]*i)

    @py.test.mark.parametrize('size',[12])
    def test_body_multiple_accesses(self, size):
        myjitdriver = JitDriver(greens = [], reds = 'auto')
        T = lltype.Array(rffi.CHAR, hints={'nolength': True})
        def f(size):
            vector_a = malloc(T, size)
            vector_b = malloc(T, size)
            i = 0
            while i < size:
                myjitdriver.jit_merge_point()
                # should unroll and group them correctly
                c1 = vector_a[i]
                c2 = vector_a[i+1]
                c3 = vector_a[i+2]
                #
                vector_b[i] = c1
                vector_b[i+1] = c2
                vector_b[i+2] = c3
                i += 3
            free(vector_a)
            free(vector_b)
            return 0
        res = self.meta_interp(f, [size], vec_all=True)
        assert res == f(size)

class TestLLtype(LLJitMixin, VectorizeTests):
    pass
