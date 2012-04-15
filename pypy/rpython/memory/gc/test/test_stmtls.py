import py
from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup
from pypy.rpython.memory.gc.stmtls import StmGCTLS, WORD
from pypy.rpython.memory.gc.test.test_stmgc import StmGCTests
from pypy.rpython.memory.support import get_address_stack, get_address_deque
from pypy.rpython.memory.gcheader import GCHeaderBuilder


NULL = llmemory.NULL
S = lltype.GcStruct('S', ('a', lltype.Signed), ('b', lltype.Signed),
                         ('c', lltype.Signed))


class FakeStmOperations:
    def set_tls(self, tlsaddr, num):
        pass
    def del_tls(self, tlsaddr):
        pass

class FakeSharedArea:
    pass

class FakeRootWalker:
    def walk_roots(self, f1, f2, f3, arg):
        if f1 is not None:
            A = lltype.Array(llmemory.Address)
            roots = lltype.malloc(A, len(self.current_stack), flavor='raw')
            for i in range(len(self.current_stack)):
                roots[i] = llmemory.cast_ptr_to_adr(self.current_stack[i])
            for i in range(len(self.current_stack)):
                root = lltype.direct_ptradd(lltype.direct_arrayitems(roots), i)
                root = llmemory.cast_ptr_to_adr(root)
                f1(arg, root)
            for i in range(len(self.current_stack)):
                P = lltype.typeOf(self.current_stack[i])
                self.current_stack[i] = llmemory.cast_adr_to_ptr(roots[i], P)
            lltype.free(roots, flavor='raw')
        assert f2 is None
        assert f3 is None

class FakeGC:
    from pypy.rpython.memory.support import AddressDict, null_address_dict
    AddressStack = get_address_stack()
    AddressDeque = get_address_deque()
    nursery_size = 128
    stm_operations = FakeStmOperations()
    sharedarea = FakeSharedArea()
    root_walker = FakeRootWalker()
    HDR = lltype.Struct('header', ('tid', lltype.Signed),
                                  ('version', llmemory.Address))
    gcheaderbuilder = GCHeaderBuilder(HDR)

    def header(self, addr):
        addr -= self.gcheaderbuilder.size_gc_header
        return llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))

    def get_size(self, addr):
        return llmemory.sizeof(lltype.typeOf(addr.ptr).TO)

    def trace(self, obj, callback, arg):
        TYPE = obj.ptr._TYPE.TO
        if TYPE == S:
            ofslist = []     # no pointers in S
        else:
            assert 0
        for ofs in ofslist:
            addr = obj + ofs
            if addr.address[0]:
                callback(addr, arg)


class TestStmGCTLS(object):

    def setup_method(self, meth):
        self.current_stack = []
        self.gc = FakeGC()
        self.gc.sharedarea.gc = self.gc
        self.gctls_main = StmGCTLS(self.gc, in_main_thread=True)
        self.gctls_thrd = StmGCTLS(self.gc, in_main_thread=False)
        self.gc.main_thread_tls = self.gctls_main
        self.gctls_main.start_transaction()
        self.gc.root_walker.current_stack = self.current_stack

    def stack_add(self, p):
        self.current_stack.append(p)

    def stack_pop(self):
        return self.current_stack.pop()

    def malloc(self, STRUCT):
        size = llarena.round_up_for_allocation(llmemory.sizeof(STRUCT))
        size_gc_header = self.gc.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        tls = self.gc.main_thread_tls
        adr = tls.allocate_bump_pointer(totalsize)
        #
        llarena.arena_reserve(adr, totalsize)
        obj = adr + size_gc_header
        hdr = self.gc.header(obj)
        hdr.tid = 0
        hdr.version = NULL
        return llmemory.cast_adr_to_ptr(obj, lltype.Ptr(STRUCT))

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
        s1 = self.malloc(S); s1.a = 111
        s2 = self.malloc(S); s2.a = 222
        self.stack_add(s2)
        self.gc.main_thread_tls.local_collection()
        s3 = self.stack_pop()
        assert s3.a == 222
        py.test.raises(RuntimeError, "s1.a")
        py.test.raises(RuntimeError, "s2.a")

    def test_alloc_a_lot_nonkept(self):
        for i in range(100):
            self.malloc(S)

    def test_alloc_a_lot_kept(self):
        for i in range(100):
            self.stack_add(self.malloc(S))
