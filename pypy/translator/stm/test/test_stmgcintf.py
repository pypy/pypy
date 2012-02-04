import random
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.stm.stmgcintf import StmOperations, CALLBACK, GETSIZE
from pypy.rpython.memory.gc import stmgc

stm_operations = StmOperations()

DEFAULT_TLS = lltype.Struct('DEFAULT_TLS')

S1 = lltype.Struct('S1', ('hdr', stmgc.StmGC.HDR),
                         ('x', lltype.Signed),
                         ('y', lltype.Signed))


def test_set_get_del():
    # assume that they are really thread-local; not checked here
    s = lltype.malloc(lltype.Struct('S'), flavor='raw')
    a = llmemory.cast_ptr_to_adr(s)
    stm_operations.set_tls(a, 1)
    assert stm_operations.get_tls() == a
    stm_operations.del_tls()
    lltype.free(s, flavor='raw')


class TestStmGcIntf:

    def setup_method(self, meth):
        TLS = getattr(meth, 'TLS', DEFAULT_TLS)
        s = lltype.malloc(TLS, flavor='raw', immortal=True)
        self.tls = s
        a = llmemory.cast_ptr_to_adr(s)
        in_main_thread = getattr(meth, 'in_main_thread', True)
        stm_operations.set_tls(a, int(in_main_thread))

    def teardown_method(self, meth):
        stm_operations.del_tls()

    def test_set_get_del(self):
        a = llmemory.cast_ptr_to_adr(self.tls)
        assert stm_operations.get_tls() == a

    def test_tldict(self):
        a1 = rffi.cast(llmemory.Address, 0x4020)
        a2 = rffi.cast(llmemory.Address, 10002)
        a3 = rffi.cast(llmemory.Address, 0x4028)
        a4 = rffi.cast(llmemory.Address, 10004)
        #
        assert stm_operations.tldict_lookup(a1) == llmemory.NULL
        stm_operations.tldict_add(a1, a2)
        assert stm_operations.tldict_lookup(a1) == a2
        #
        assert stm_operations.tldict_lookup(a3) == llmemory.NULL
        stm_operations.tldict_add(a3, a4)
        assert stm_operations.tldict_lookup(a3) == a4
        assert stm_operations.tldict_lookup(a1) == a2

    def test_tldict_large(self):
        content = {}
        WORD = rffi.sizeof(lltype.Signed)
        for i in range(12000):
            key = random.randrange(1000, 2000) * WORD
            a1 = rffi.cast(llmemory.Address, key)
            a2 = stm_operations.tldict_lookup(a1)
            if key in content:
                assert a2 == content[key]
            else:
                assert a2 == llmemory.NULL
                a2 = rffi.cast(llmemory.Address, random.randrange(2000, 9999))
                stm_operations.tldict_add(a1, a2)
                content[key] = a2
        return content

    def get_callback(self):
        def callback(key, value):
            seen.append((key, value))
        seen = []
        p_callback = llhelper(CALLBACK, callback)
        return p_callback, seen

    def test_enum_tldict_empty(self):
        p_callback, seen = self.get_callback()
        stm_operations.tldict_enum(p_callback)
        assert seen == []

    def stm_read_case(self, flags, copied=False):
        # doesn't test STM behavior, but just that it appears to work
        s1 = lltype.malloc(S1, flavor='raw')
        s1.hdr.tid = stmgc.GCFLAG_GLOBAL | flags
        s1.hdr.version = llmemory.NULL
        s1.x = 42042
        if copied:
            s2 = lltype.malloc(S1, flavor='raw')
            s2.hdr.tid = stmgc.GCFLAG_WAS_COPIED
            s2.hdr.version = llmemory.NULL
            s2.x = 84084
            a1 = llmemory.cast_ptr_to_adr(s1)
            a2 = llmemory.cast_ptr_to_adr(s2)
            stm_operations.tldict_add(a1, a2)
        res = stm_operations.stm_read_word(llmemory.cast_ptr_to_adr(s1),
                                           rffi.sizeof(S1.hdr))  # 'x'
        lltype.free(s1, flavor='raw')
        if copied:
            lltype.free(s2, flavor='raw')
        return res

    def test_stm_read_word_main_thread(self):
        res = self.stm_read_case(0)                        # not copied
        assert res == 42042
        res = self.stm_read_case(stmgc.GCFLAG_WAS_COPIED)  # but ignored
        assert res == 42042

    def test_stm_read_word_transactional_thread(self):
        res = self.stm_read_case(0)                        # not copied
        assert res == 42042
        res = self.stm_read_case(stmgc.GCFLAG_WAS_COPIED)  # but ignored
        assert res == 42042
        res = self.stm_read_case(stmgc.GCFLAG_WAS_COPIED, copied=True)
        assert res == 84084
    test_stm_read_word_transactional_thread.in_main_thread = False

    def test_stm_size_getter(self):
        def getsize(addr):
            xxx
        getter = llhelper(GETSIZE, getsize)
        stm_operations.setup_size_getter(getter)
        # just tests that the function is really defined
