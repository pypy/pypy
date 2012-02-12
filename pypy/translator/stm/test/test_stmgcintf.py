import py, random
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.stm.stmgcintf import StmOperations
from pypy.rpython.memory.gc import stmgc

WORD = stmgc.WORD

stm_operations = StmOperations()

DEFAULT_TLS = lltype.Struct('DEFAULT_TLS')

S1 = lltype.Struct('S1', ('hdr', stmgc.StmGC.HDR),
                         ('x', lltype.Signed),
                         ('y', lltype.Signed))

# xxx a lot of casts to convince rffi to give us a regular integer :-(
SIZEOFHDR = rffi.cast(lltype.Signed, rffi.cast(rffi.SHORT,
                                               rffi.sizeof(S1.hdr)))


def test_set_get_del():
    # assume that they are really thread-local; not checked here
    s = lltype.malloc(lltype.Struct('S'), flavor='raw')
    a = llmemory.cast_ptr_to_adr(s)
    stm_operations.set_tls(a, 1)
    assert stm_operations.get_tls() == a
    stm_operations.del_tls()
    lltype.free(s, flavor='raw')


class TestStmGcIntf:
    _in_transaction = False

    def setup_method(self, meth):
        TLS = getattr(meth, 'TLS', DEFAULT_TLS)
        s = lltype.malloc(TLS, flavor='raw', immortal=True)
        self.tls = s
        a = llmemory.cast_ptr_to_adr(s)
        in_transaction = getattr(meth, 'in_transaction', False)
        in_main_thread = getattr(meth, 'in_main_thread', not in_transaction)
        stm_operations.set_tls(a, int(in_main_thread))
        if in_transaction:
            stm_operations._activate_transaction(1)
            self._in_transaction = True

    def teardown_method(self, meth):
        if self._in_transaction:
            stm_operations._activate_transaction(0)
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
    test_tldict.in_transaction = True

    def test_tldict_large(self):
        content = {}
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
    test_tldict_large.in_transaction = True

    def get_callback_enum(self):
        def callback(tls, key, value):
            assert tls == llmemory.cast_ptr_to_adr(self.tls)
            seen.append((key, value))
        seen = []
        p_callback = llhelper(StmOperations.CALLBACK_ENUM, callback)
        return p_callback, seen

    def test_enum_tldict_empty(self):
        p_callback, seen = self.get_callback_enum()
        stm_operations.tldict_enum(p_callback)
        assert seen == []

    def test_enum_tldict_nonempty(self):
        a1 = rffi.cast(llmemory.Address, 0x4020)
        a2 = rffi.cast(llmemory.Address, 10002)
        a3 = rffi.cast(llmemory.Address, 0x4028)
        a4 = rffi.cast(llmemory.Address, 10004)
        #
        stm_operations.tldict_add(a1, a2)
        stm_operations.tldict_add(a3, a4)
        p_callback, seen = self.get_callback_enum()
        stm_operations.tldict_enum(p_callback)
        assert (seen == [(a1, a2), (a3, a4)] or
                seen == [(a3, a4), (a1, a2)])
    test_enum_tldict_nonempty.in_transaction = True

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
        reader = getattr(stm_operations, 'stm_read_int%d' % WORD)
        res = reader(llmemory.cast_ptr_to_adr(s1), SIZEOFHDR)   # 'x'
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
    test_stm_read_word_transactional_thread.in_transaction = True

    def stm_read_intX(self, TYPE, sizesuffix):
        print TYPE, sizesuffix
        S2 = lltype.Struct('S2', ('hdr', stmgc.StmGC.HDR),
                                 ('c1', TYPE),
                                 ('c2', TYPE),
                                 ('c3', TYPE))
        s2 = lltype.malloc(S2, flavor='raw')
        s2.hdr.tid = stmgc.GCFLAG_GLOBAL | stmgc.GCFLAG_WAS_COPIED
        s2.hdr.version = llmemory.NULL
        s2.c1 = A = rffi.cast(TYPE, -65)
        s2.c2 = B = rffi.cast(TYPE, -66)
        s2.c3 = C = rffi.cast(TYPE, -67)
        size = rffi.sizeof(TYPE)
        assert sizesuffix in (size, '%df' % size)
        reader = getattr(stm_operations, 'stm_read_int%s' % sizesuffix)
        r1 = reader(llmemory.cast_ptr_to_adr(s2), SIZEOFHDR + 0 * size)  # c1
        r2 = reader(llmemory.cast_ptr_to_adr(s2), SIZEOFHDR + 1 * size)  # c2
        r3 = reader(llmemory.cast_ptr_to_adr(s2), SIZEOFHDR + 2 * size)  # c3
        lltype.free(s2, flavor='raw')
        assert r1 == A and r2 == B and r3 == C

    def test_stm_read_int(self):
        for size, TYPE in StmOperations.PRIMITIVE_SIZES.items():
            yield self.stm_read_intX, TYPE, size

    def test_stm_size_getter(self):
        def getsize(addr):
            dont_call_me
        getter = llhelper(StmOperations.GETSIZE, getsize)
        stm_operations.setup_size_getter(getter)
        # ^^^ just tests that the function is really defined

    def test_stm_copy_transactional_to_raw(self):
        # doesn't test STM behavior, but just that it appears to work
        s1 = lltype.malloc(S1, flavor='raw')
        s1.hdr.tid = stmgc.GCFLAG_GLOBAL
        s1.hdr.version = llmemory.NULL
        s1.x = 909
        s1.y = 808
        s2 = lltype.malloc(S1, flavor='raw')
        s2.hdr.tid = -42    # non-initialized
        s2.x = -42          # non-initialized
        s2.y = -42          # non-initialized
        #
        s1_adr = llmemory.cast_ptr_to_adr(s1)
        s2_adr = llmemory.cast_ptr_to_adr(s2)
        size   = llmemory.sizeof(S1)
        stm_operations.stm_copy_transactional_to_raw(s1_adr, s2_adr, size)
        #
        assert s2.hdr.tid == -42    # not touched
        assert s2.x == 909
        assert s2.y == 808
        #
        lltype.free(s2, flavor='raw')
        lltype.free(s1, flavor='raw')
    test_stm_copy_transactional_to_raw.in_transaction = True

    def test_in_transaction(self):
        assert stm_operations.in_transaction()
    test_in_transaction.in_transaction = True

    def test_not_in_transaction(self):
        assert not stm_operations.in_transaction()
    test_not_in_transaction.in_main_thread = False

    def test_not_in_transaction_main(self):
        assert not stm_operations.in_transaction()
    test_not_in_transaction.in_main_thread = True

    def test_stm_perform_transaction(self):
        def callback1(x, retry_counter):
            return rffi.cast(rffi.VOIDP, -123)
        x = stm_operations.perform_transaction(
            llhelper(StmOperations.CALLBACK_TX, callback1),
            lltype.nullptr(rffi.VOIDP.TO))
        assert x == rffi.cast(rffi.VOIDP, -123)

    def test_stm_try_inevitable(self):
        # not really testing anything more than the presence of the function
        stm_operations.try_inevitable()
    test_stm_try_inevitable.in_transaction = True

    def test_thread_id_main(self):
        assert stm_operations.thread_id() == 0
    test_thread_id_main.in_main_thread = True

    def test_thread_id_nonmain(self):
        assert stm_operations.thread_id() != 0
    test_thread_id_nonmain.in_main_thread = False

    def test_abort_and_retry(self):
        def callback1(x, retry_counter):
            assert 0 <= retry_counter <= 10
            if retry_counter == 10:
                return rffi.cast(rffi.VOIDP, -42)
            stm_operations.abort_and_retry()
            assert 0   # not reachable
        x = stm_operations.perform_transaction(
            llhelper(StmOperations.CALLBACK_TX, callback1),
            lltype.nullptr(rffi.VOIDP.TO))
        assert x == rffi.cast(rffi.VOIDP, -42)

    def test_debug_get_state_main_thread(self):
        st = stm_operations._debug_get_state()
        assert st == stm_operations.STATE_MAIN_THREAD
    test_debug_get_state_main_thread.in_main_thread = True

    def test_debug_get_state_inactive(self):
        st = stm_operations._debug_get_state()
        assert st == stm_operations.STATE_INACTIVE
    test_debug_get_state_inactive.in_main_thread = False

    def test_debug_get_state_active(self):
        def callback1(x, retry_counter):
            st = stm_operations._debug_get_state()
            return rffi.cast(rffi.VOIDP, st)
        x = stm_operations.perform_transaction(
            llhelper(StmOperations.CALLBACK_TX, callback1),
            lltype.nullptr(rffi.VOIDP.TO))
        assert rffi.cast(lltype.Signed, x) == stm_operations.STATE_ACTIVE
    test_debug_get_state_active.in_main_thread = False

    def test_debug_get_state_active_inevitable(self):
        def callback1(x, retry_counter):
            stm_operations.try_inevitable()
            st = stm_operations._debug_get_state()
            return rffi.cast(rffi.VOIDP, st)
        x = stm_operations.perform_transaction(
            llhelper(StmOperations.CALLBACK_TX, callback1),
            lltype.nullptr(rffi.VOIDP.TO))
        assert (rffi.cast(lltype.Signed, x) ==
                stm_operations.STATE_ACTIVE_INEVITABLE)
    test_debug_get_state_active_inevitable.in_main_thread = False


def test_debug_get_state_not_initialized():
    st = stm_operations._debug_get_state()
    assert st == stm_operations.STATE_NOT_INITIALIZED
