# tests that check that information is fed from the optimizer into the bridges

from rpython.rlib import jit
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.jit.metainterp.optimizeopt.bridgeopt import serialize_optimizer_knowledge
from rpython.jit.metainterp.optimizeopt.bridgeopt import deserialize_optimizer_knowledge
from rpython.jit.metainterp.resoperation import InputArgRef, InputArgInt
from rpython.jit.metainterp.resume import NumberingState
from rpython.jit.metainterp.optimizeopt.info import InstancePtrInfo

class FakeTS(object):
    def __init__(self, dct):
        self.dct = dct

    def cls_of_box(self, box):
        return self.dct[box]


class FakeCPU(object):
    def __init__(self, dct):
        self.ts = FakeTS(dct)

class FakeOptimizer(object):
    metainterp_sd = None

    def __init__(self, dct={}, cpu=None):
        self.dct = dct
        self.constant_classes = {}
        self.cpu = cpu

    def getptrinfo(self, arg):
        return self.dct.get(arg, None)

    def make_constant_class(self, arg, cls):
        self.constant_classes[arg] = cls

class FakeClass(object):
    pass

def test_simple():
    box1 = InputArgRef()
    box2 = InputArgRef()
    box3 = InputArgRef()

    cls = FakeClass()
    dct = {box1: InstancePtrInfo(known_class=cls)}
    optimizer = FakeOptimizer(dct)

    numb_state = NumberingState(4)
    numb_state.append_int(1) # vinfo
    liveboxes = [InputArgInt(), box2, box1, box3]

    serialize_optimizer_knowledge(optimizer, numb_state, liveboxes, None)

    assert numb_state.current[:numb_state._pos] == [1, 0b0100000]

    rbox1 = InputArgRef()
    rbox2 = InputArgRef()
    rbox3 = InputArgRef()
    after_optimizer = FakeOptimizer(cpu=FakeCPU({rbox1: cls}))
    deserialize_optimizer_knowledge(
        after_optimizer, numb_state.create_numbering(),
        [InputArgInt(), rbox2, rbox1, rbox3], liveboxes)
    assert box1 in after_optimizer.constant_classes
    assert box2 not in after_optimizer.constant_classes
    assert box3 not in after_optimizer.constant_classes


class TestOptBridge(LLJitMixin):
    # integration tests
    def test_bridge(self):
        myjitdriver = jit.JitDriver(greens=[], reds=['y', 'res', 'n', 'a'])
        class A(object):
            def f(self):
                return 1
        class B(A):
            def f(self):
                return 2
        def f(x, y, n):
            if x:
                a = A()
            else:
                a = B()
            a.x = 0
            res = 0
            while y > 0:
                myjitdriver.jit_merge_point(y=y, n=n, res=res, a=a)
                res += a.f()
                a.x += 1
                if y > n:
                    res += 1
                res += a.f()
                y -= 1
            return res
        res = self.meta_interp(f, [6, 32, 16])
        assert res == f(6, 32, 16)
        self.check_trace_count(3)
        self.check_resops(guard_class=1)
