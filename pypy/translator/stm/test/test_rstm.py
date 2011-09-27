import py
from pypy.translator.stm._rffi_stm import *
from pypy.translator.stm.rstm import *
from pypy.rpython.annlowlevel import llhelper


A = lltype.Struct('A', ('x', lltype.Signed), ('y', lltype.Signed))

def callback1(a):
    a = rffi.cast(lltype.Ptr(A), a)
    assert a.x == -611
    assert stm_getfield(a, 'x') == -611
    p = lltype.direct_fieldptr(a, 'x')
    p = rffi.cast(rffi.VOIDPP, p)
    stm_write_word(p, rffi.cast(rffi.VOIDP, 42 * a.y))
    assert stm_getfield(a, 'x') == 42 * a.y
    assert a.x == -611 # xxx still the old value when reading non-transact.
    if a.y < 10:
        a.y += 1    # non-transactionally
        abort_and_retry()
    return lltype.nullptr(rffi.VOIDP.TO)

def test_stm_getfield():
    a = lltype.malloc(A, flavor='raw')
    a.x = -611
    a.y = 0
    descriptor_init()
    perform_transaction(llhelper(CALLBACK, callback1),
                        rffi.cast(rffi.VOIDP, a))
    descriptor_done()
    assert a.x == 420
    lltype.free(a, flavor='raw')

def callback2(a):
    a = rffi.cast(lltype.Ptr(A), a)
    assert a.x == -611
    assert stm_getfield(a, 'x') == -611
    stm_setfield(a, 'x', 42 * a.y)
    assert stm_getfield(a, 'x') == 42 * a.y
    assert a.x == -611 # xxx still the old value when reading non-transact.
    if a.y < 10:
        a.y += 1    # non-transactionally
        abort_and_retry()
    return lltype.nullptr(rffi.VOIDP.TO)

def test_stm_setfield():
    a = lltype.malloc(A, flavor='raw')
    a.x = -611
    a.y = 0
    descriptor_init()
    perform_transaction(llhelper(CALLBACK, callback2),
                        rffi.cast(rffi.VOIDP, a))
    descriptor_done()
    assert a.x == 420
    lltype.free(a, flavor='raw')

# ____________________________________________________________

from pypy.translator.translator import TranslationContext
from pypy.annotation.listdef import s_list_of_strings
from pypy.translator.c.genc import CStandaloneBuilder

class StmTests(object):
    config = None

    def compile(self, entry_point):
        t = TranslationContext(self.config)
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper().specialize()
        cbuilder = CStandaloneBuilder(t, entry_point, t.config)
        cbuilder.generate_source(defines=cbuilder.DEBUG_DEFINES)
        cbuilder.compile()
        return t, cbuilder


class TestRStm(StmTests):

    def test_compiled_stm_getfield(self):
        def entry_point(argv):
            test_stm_getfield()
            print 'ok!'
            return 0
        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('')
        assert data == 'ok!\n'

    def test_compiled_stm_setfield(self):
        def entry_point(argv):
            test_stm_setfield()
            print 'ok!'
            return 0
        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('')
        assert data == 'ok!\n'
