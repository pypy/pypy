from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.lltypesystem.lloperation import llop

from rpython.memory.test import test_minimark_gc

class TestIncrementalMiniMarkGC(test_minimark_gc.TestMiniMarkGC):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass
    WREF_IS_INVALID_BEFORE_DEL_IS_CALLED = True

    def test_weakref_not_in_stack(self):
        import weakref
        class A(object):
            pass
        class B(object):
            def __init__(self, next):
                self.next = next
        def g():
            a = A()
            a.x = 5
            wr = weakref.ref(a)
            llop.gc__collect(lltype.Void)   # make everything old
            assert wr() is not None
            assert a.x == 5
            return wr
        def f():
            ref = g()
            llop.gc__collect(lltype.Void, 1)    # start a major cycle
            # at this point the stack is scanned, and the weakref points
            # to an object not found, but still reachable:
            b = ref()
            llop.debug_print(lltype.Void, b)
            assert b is not None
            llop.gc__collect(lltype.Void)   # finish the major cycle
            # assert does not crash, because 'b' is still kept alive
            b.x = 42
            return ref() is b
        res = self.interpret(f, [])
        assert res == True
