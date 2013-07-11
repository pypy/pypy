from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib import jit

from pypy.interpreter import unpack, error

class W_Root(object):
    type = None

    from pypy.interpreter.unpack import generic_unpack_into as unpack_into

    def next(self):
        raise NotImplementedError
    def iter(self):
        raise NotImplementedError

class W_Type(W_Root):
    pass
W_Type.type = W_Type()

class W_List(W_Root):
    type = W_Type()
    def __init__(self, l):
        self.l = l

    def iter(self):
        return W_Iter(self.l)

class W_Iter(W_Root):
    type = W_Type()
    def __init__(self, l):
        self.l = l
        self.i = 0

    def next(self):
        i = self.i
        if i >= len(self.l):
            raise error.OperationError(StopIteration, None)
        self.i += 1
        return self.l[i]

class W_Int(W_Root):
    type = W_Type()

    def __init__(self, value):
        self.value = value

class W_String(W_Root):
    type = W_Type()

    def __init__(self, value):
        self.value = value

class FakeSpace(object):
    w_StopIteration = StopIteration
    w_ValueError = ValueError

    def iter(self, w_obj):
        return w_obj.iter()

    def next(self, w_obj):
        return w_obj.next()

    def type(self, w_obj):
        return w_obj.type

    def length_hint(self, w_obj, x):
        return 7

    def exception_match(self, w_obj, w_cls):
        return w_obj is w_cls

    def wrap(self, string):
        return W_String(string)

    def _freeze_(self):
        return True

space = FakeSpace()


class TestUnpackJIT(LLJitMixin):
    def test_jit_unpack(self):
        def f(i):
            l = [W_Int(x) for x in range(100 + i)]
            l.append(W_Int(i))

            w_l = W_List(l)
            res = 0
            target = unpack.FixedSizeUnpackTarget(space, len(l))
            if i < 0:
                w_l.unpack_into(space, target, unroll=True)
            else:
                w_l.unpack_into(space, target)
            res += len(target.items_w)
            target = unpack.InterpListUnpackTarget(space, w_l)
            w_l.unpack_into(space, target)
            return len(target.items_w) + res
        assert f(4) == 210

        result = self.meta_interp(f, [4], listops=True, backendopt=True, listcomp=True)
        assert result == 210
        self.check_trace_count(2)

    def test_unroll(self):
        unpack_into_driver = jit.JitDriver(greens=[], reds='auto')
        def f(i):
            l = [W_Int(x) for x in range(i)]
            l.append(W_Int(i))

            w_l = W_List(l)
            res = 0
            for i in range(100):
                unpack_into_driver.jit_merge_point()
                target = unpack.FixedSizeUnpackTarget(space, len(l))
                if i < 0:
                    w_l.unpack_into(space, target)
                else:
                    w_l.unpack_into(space, target, unroll=True)
                res += len(target.items_w)
            return res
        assert f(4) == 500

        result = self.meta_interp(f, [4], listops=True, backendopt=True, listcomp=True)
        assert result == 500
        self.check_resops(getarrayitem_gc=10, setarrayitem_gc=10,
                call_may_force=0)
