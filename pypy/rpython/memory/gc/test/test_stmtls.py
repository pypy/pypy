import py
from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup, rffi
from pypy.rpython.memory.gc.stmtls import StmGCTLS, WORD
from pypy.rpython.memory.gc.test.test_stmgc import StmGCTests


S = lltype.GcStruct('S', ('a', lltype.Signed), ('b', lltype.Signed),
                         ('c', lltype.Signed))


class TestStmGCTLS(StmGCTests):
    current_stack = ()

    def stack_add(self, p):
        if self.current_stack == ():
            self.current_stack = []
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
