from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.gc.stmgc import StmGC
from pypy.rpython.memory.gc.stmgc import GCFLAG_GLOBAL, GCFLAG_WAS_COPIED


S = lltype.GcStruct('S', ('a', lltype.Signed), ('b', lltype.Signed))
ofs_a = llmemory.offsetof(S, 'a')


class FakeStmOperations:
    threadnum = 0          # 0 = main thread; 1,2,3... = transactional threads

    def set_tls(self, gc, tls):
        assert lltype.typeOf(tls) == llmemory.Address
        if self.threadnum == 0:
            assert not hasattr(self, '_tls_dict')
            assert not hasattr(self, '_gc')
            self._tls_dict = {0: tls}
            self._tldicts = {0: {}}
            self._gc = gc
            self._transactional_copies = []
        else:
            assert self._gc is gc
            self._tls_dict[self.threadnum] = tls
            self._tldicts[self.threadnum] = {}

    def get_tls(self):
        return self._tls_dict[self.threadnum]

    def tldict_lookup(self, obj):
        assert lltype.typeOf(obj) == llmemory.Address
        assert obj
        tldict = self._tldicts[self.threadnum]
        return tldict.get(obj, llmemory.NULL)

    def tldict_add(self, obj, localobj):
        assert lltype.typeOf(obj) == llmemory.Address
        tldict = self._tldicts[self.threadnum]
        assert obj not in tldict
        tldict[obj] = localobj

    class stm_read_word:
        def __init__(self, obj, offset):
            self.obj = obj
            self.offset = offset
        def __repr__(self):
            return 'stm_read_word(%r, %r)' % (self.obj, self.offset)
        def __eq__(self, other):
            return (type(self) is type(other) and
                    self.__dict__ == other.__dict__)
        def __ne__(self, other):
            return not (self == other)

    def stm_copy_transactional_to_raw(self, srcobj, dstobj, size):
        sizehdr = self._gc.gcheaderbuilder.size_gc_header
        srchdr = srcobj - sizehdr
        dsthdr = dstobj - sizehdr
        llmemory.raw_memcopy(srchdr, dsthdr, sizehdr)
        llmemory.raw_memcopy(srcobj, dstobj, size)
        self._transactional_copies.append((srcobj, dstobj))


def fake_get_size(obj):
    TYPE = obj.ptr._TYPE.TO
    if isinstance(TYPE, lltype.GcStruct):
        return llmemory.sizeof(TYPE)
    else:
        assert 0


class TestBasic:
    GCClass = StmGC

    def setup_method(self, meth):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True).translation
        self.gc = self.GCClass(config, FakeStmOperations(),
                               translated_to_c=False)
        self.gc.DEBUG = True
        self.gc.get_size = fake_get_size
        self.gc.setup()

    def teardown_method(self, meth):
        for key in self.gc.stm_operations._tls_dict.keys():
            if key != 0:
                self.gc.stm_operations.threadnum = key
                self.gc.teardown_thread()

    # ----------
    # test helpers
    def malloc(self, STRUCT):
        gcref = self.gc.malloc_fixedsize_clear(123, llmemory.sizeof(STRUCT))
        realobj = lltype.cast_opaque_ptr(lltype.Ptr(STRUCT), gcref)
        addr = llmemory.cast_ptr_to_adr(realobj)
        return realobj, addr
    def select_thread(self, threadnum):
        self.gc.stm_operations.threadnum = threadnum
        if threadnum not in self.gc.stm_operations._tls_dict:
            self.gc.setup_thread(False)

    def test_gc_creation_works(self):
        pass

    def test_allocate_bump_pointer(self):
        a3 = self.gc.allocate_bump_pointer(3)
        a4 = self.gc.allocate_bump_pointer(4)
        a5 = self.gc.allocate_bump_pointer(5)
        a6 = self.gc.allocate_bump_pointer(6)
        assert a4 - a3 == 3
        assert a5 - a4 == 4
        assert a6 - a5 == 5

    def test_malloc_fixedsize_clear(self):
        gcref = self.gc.malloc_fixedsize_clear(123, llmemory.sizeof(S))
        s = lltype.cast_opaque_ptr(lltype.Ptr(S), gcref)
        assert s.a == 0
        assert s.b == 0
        gcref2 = self.gc.malloc_fixedsize_clear(123, llmemory.sizeof(S))
        assert gcref2 != gcref

    def test_malloc_main_vs_thread(self):
        gcref = self.gc.malloc_fixedsize_clear(123, llmemory.sizeof(S))
        obj = llmemory.cast_ptr_to_adr(gcref)
        assert self.gc.header(obj).tid & GCFLAG_GLOBAL != 0
        #
        self.select_thread(1)
        gcref = self.gc.malloc_fixedsize_clear(123, llmemory.sizeof(S))
        obj = llmemory.cast_ptr_to_adr(gcref)
        assert self.gc.header(obj).tid & GCFLAG_GLOBAL == 0

    def test_reader_direct(self):
        s, s_adr = self.malloc(S)
        assert self.gc.header(s_adr).tid & GCFLAG_GLOBAL != 0
        s.a = 42
        value = self.gc.read_signed(s_adr, ofs_a)
        assert value == FakeStmOperations.stm_read_word(s_adr, ofs_a)
        #
        self.select_thread(1)
        s, s_adr = self.malloc(S)
        assert self.gc.header(s_adr).tid & GCFLAG_GLOBAL == 0
        self.gc.header(s_adr).tid |= GCFLAG_WAS_COPIED   # should be ignored
        s.a = 42
        value = self.gc.read_signed(s_adr, ofs_a)
        assert value == 42

    def test_reader_through_dict(self):
        s, s_adr = self.malloc(S)
        s.a = 42
        #
        self.select_thread(1)
        t, t_adr = self.malloc(S)
        t.a = 84
        #
        self.gc.header(s_adr).tid |= GCFLAG_WAS_COPIED
        self.gc.stm_operations._tldicts[1][s_adr] = t_adr
        #
        value = self.gc.read_signed(s_adr, ofs_a)
        assert value == 84

    def test_write_barrier_exists(self):
        self.select_thread(1)
        t, t_adr = self.malloc(S)
        obj = self.gc.write_barrier(t_adr)     # local object
        assert obj == t_adr
        #
        self.select_thread(0)
        s, s_adr = self.malloc(S)
        #
        self.select_thread(1)
        self.gc.header(s_adr).tid |= GCFLAG_WAS_COPIED
        self.gc.header(t_adr).tid |= GCFLAG_WAS_COPIED
        self.gc.stm_operations._tldicts[1][s_adr] = t_adr
        obj = self.gc.write_barrier(s_adr)     # global copied object
        assert obj == t_adr
        assert self.gc.stm_operations._transactional_copies == []

    def test_write_barrier_new(self):
        self.select_thread(0)
        s, s_adr = self.malloc(S)
        s.a = 12
        s.b = 34
        #
        self.select_thread(1)
        t_adr = self.gc.write_barrier(s_adr) # global object, not copied so far
        assert t_adr != s_adr
        t = t_adr.ptr
        assert t.a == 12
        assert t.b == 34
        assert self.gc.stm_operations._transactional_copies == [(s_adr, t_adr)]
        #
        u_adr = self.gc.write_barrier(s_adr)  # again
        assert u_adr == t_adr
        #
        u_adr = self.gc.write_barrier(u_adr)  # local object
        assert u_adr == t_adr
