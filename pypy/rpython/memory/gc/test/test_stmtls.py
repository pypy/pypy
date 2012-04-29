import py
from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup
from pypy.rpython.memory.gc.stmtls import StmGCTLS, WORD
from pypy.rpython.memory.gc.test.test_stmgc import StmGCTests
from pypy.rpython.memory.support import get_address_stack, get_address_deque
from pypy.rpython.memory.gcheader import GCHeaderBuilder


NULL = llmemory.NULL
S = lltype.GcStruct('S', ('a', lltype.Signed), ('b', lltype.Signed),
                         ('c', lltype.Signed))
SR = lltype.GcForwardReference()
SR.become(lltype.GcStruct('SR', ('s1', lltype.Ptr(S)),
                                ('sr2', lltype.Ptr(SR)),
                                ('sr3', lltype.Ptr(SR))))


class FakeStmOperations:
    def set_tls(self, tlsaddr, num):
        pass
    def del_tls(self, tlsaddr):
        pass

class FakeSharedArea:
    pass

class FakeRootWalker:
    current_stack = ()
    prebuilt_nongc = ()
    prebuilt_threadlocal = ()

    def collect_list(self, lst):
        A = lltype.Array(llmemory.Address)
        roots = lltype.malloc(A, len(lst), flavor='raw')
        for i in range(len(lst)):
            roots[i] = llmemory.cast_ptr_to_adr(lst[i])
        for i in range(len(lst)):
            root = lltype.direct_ptradd(lltype.direct_arrayitems(roots), i)
            root = llmemory.cast_ptr_to_adr(root)
            yield root
        for i in range(len(lst)):
            P = lltype.typeOf(lst[i])
            lst[i] = llmemory.cast_adr_to_ptr(roots[i], P)
        lltype.free(roots, flavor='raw')

    def walk_current_stack_roots(self, callback, arg):
        for root in self.collect_list(self.current_stack):
            callback(arg, root)

    def collect_field_list(self, lst):
        for structptr, field in lst:
            root = lltype.direct_fieldptr(structptr, field)
            root = llmemory.cast_ptr_to_adr(root)
            yield root

    def walk_current_nongc_roots(self, callback, arg):
        for root in self.collect_field_list(self.prebuilt_nongc):
            callback(arg, root)

    def walk_current_thrloc_roots(self, callback, arg):
        for root in self.collect_field_list(self.prebuilt_threadlocal):
            callback(arg, root)

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
        elif TYPE == SR:
            ofslist = [llmemory.offsetof(SR, 's1'),
                       llmemory.offsetof(SR, 'sr2'),
                       llmemory.offsetof(SR, 'sr3')]
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
            s1 = self.malloc(S)
            s1.a = i
            self.stack_add(s1)
        for i in range(100)[::-1]:
            s2 = self.stack_pop()
            assert s2.a == i

    def test_alloc_chain(self):
        srlist = lltype.nullptr(SR)
        for i in range(100):
            self.stack_add(srlist)
            sr1 = self.malloc(SR)
            srlist = self.stack_pop()
            sr1.sr2 = srlist
            srlist = sr1
            #
            for j in range(i, -1, -1):
                assert sr1
                sr1 = sr1.sr2
            assert not sr1
