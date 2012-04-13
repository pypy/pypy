import py
from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup, rffi
from pypy.rpython.memory.gc.stmtls import StmGCTLS, WORD
from pypy.rpython.memory.gc.test.test_stmgc import StmGCTests
from pypy.rpython.memory.support import get_address_stack, get_address_deque


S = lltype.GcStruct('S', ('a', lltype.Signed), ('b', lltype.Signed),
                         ('c', lltype.Signed))


class FakeStmOperations:
    def set_tls(self, tlsaddr, num):
        pass
    def del_tls(self, tlsaddr):
        pass

class FakeSharedArea:
    pass

class FakeGC:
    from pypy.rpython.memory.support import AddressDict, null_address_dict
    AddressStack = get_address_stack()
    AddressDeque = get_address_deque()
    nursery_size = 128
    stm_operations = FakeStmOperations()
    sharedarea = FakeSharedArea()


class TestStmGCTLS(object):

    def setup_method(self, meth):
        self.current_stack = []
        self.gc = FakeGC()
        self.gc.sharedarea.gc = self.gc
        self.gctls_main = StmGCTLS(self.gc, in_main_thread=True)
        self.gctls_thrd = StmGCTLS(self.gc, in_main_thread=False)
        self.gc.main_thread_tls = self.gctls_main

    def stack_add(self, p):
        self.current_stack.append(p)

    def stack_pop(self):
        return self.current_stack.pop()

    # ----------

    def test_creation_works(self):
        pass

    def test_allocate_bump_pointer(self):
        tls = self.gc.main_thread_tls
        a3 = tls.allocate_bump_pointer(3)
        a4 = tls.allocate_bump_pointer(4)
        a5 = tls.allocate_bump_pointer(5)
        a6 = tls.allocate_bump_pointer(6)
        assert a4 - a3 == 3
        assert a5 - a4 == 4
        assert a6 - a5 == 5

    def test_local_collection(self):
        s1, _ = self.malloc(S); s1.a = 111
        s2, _ = self.malloc(S); s2.a = 222
        self.stack_add(s2)
        self.gc.main_thread_tls.local_collection()
        s3 = self.stack_pop()
        assert s3.a == 222
        xxxx # raises...
        s1.a
        s2.a

    def test_alloc_a_lot(self):
        for i in range(1000):
            sr1, sr1_adr = self.malloc(SR)
