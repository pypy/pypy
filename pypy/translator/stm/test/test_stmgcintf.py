import random
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.stm.stmgcintf import StmOperations, CALLBACK, GETSIZE

stm_operations = StmOperations()

DEFAULT_TLS = lltype.Struct('DEFAULT_TLS')


def test_set_get_del():
    # assume that they are really thread-local; not checked here
    s = lltype.malloc(lltype.Struct('S'), flavor='raw')
    a = llmemory.cast_ptr_to_adr(s)
    stm_operations.set_tls(a, lltype.nullptr(GETSIZE.TO))
    assert stm_operations.get_tls() == a
    stm_operations.del_tls()
    lltype.free(s, flavor='raw')


class TestStmGcIntf:

    def setup_method(self, meth):
        TLS = getattr(meth, 'TLS', DEFAULT_TLS)
        s = lltype.malloc(TLS, flavor='raw', immortal=True)
        self.tls = s
        a = llmemory.cast_ptr_to_adr(s)
        getsize = llhelper(GETSIZE, self.getsize)
        stm_operations.set_tls(a, getsize)

    def teardown_method(self, meth):
        stm_operations.del_tls()

    def getsize(self, obj):
        xxx

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
