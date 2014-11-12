from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rlib.objectmodel import CDefinedIntSymbolic
from rpython.rlib.nonconst import NonConstant
from rpython.rlib import rgc
from rpython.rtyper.lltypesystem import lltype, rffi, rstr, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rlib.jit import dont_look_inside

class CFlexSymbolic(CDefinedIntSymbolic):
    _compare_by_id_ = True


TID = rffi.UINT
tid_offset = CFlexSymbolic('offsetof(struct rpyobj_s, tid)')
stm_nb_segments = CFlexSymbolic('STM_NB_SEGMENTS')
adr_nursery_free = CFlexSymbolic('((long)&STM_SEGMENT->nursery_current)')
adr_nursery_top  = CFlexSymbolic('((long)&STM_SEGMENT->nursery_end)')
adr_pypy_stm_nursery_low_fill_mark = (
    CFlexSymbolic('((long)&pypy_stm_nursery_low_fill_mark)'))
adr_rjthread_head = (
    CFlexSymbolic('((long)&stm_thread_local.rjthread.head)'))
adr_rjthread_moved_off_base = (
    CFlexSymbolic('((long)&stm_thread_local.rjthread.moved_off_base)'))
adr_transaction_read_version = (
    CFlexSymbolic('((long)&STM_SEGMENT->transaction_read_version)'))
adr_segment_base = (
    CFlexSymbolic('((long)&STM_SEGMENT->segment_base)'))
adr_write_slowpath = CFlexSymbolic('((long)&_stm_write_slowpath)')
adr_write_slowpath_card_extra = (
    CFlexSymbolic('((long)&_stm_write_slowpath_card_extra)'))
adr__stm_write_slowpath_card_extra_base = (
   CFlexSymbolic('(_stm_write_slowpath_card_extra_base()-0x4000000000000000L)'))
CARD_MARKED = CFlexSymbolic('_STM_CARD_MARKED')
CARD_SIZE   = CFlexSymbolic('_STM_CARD_SIZE')

adr_pypy__rewind_jmp_copy_stack_slice = (
    CFlexSymbolic('((long)&pypy__rewind_jmp_copy_stack_slice)'))
adr_pypy_stm_commit_if_not_atomic = (
    CFlexSymbolic('((long)&pypy_stm_commit_if_not_atomic)'))
adr_pypy_stm_start_if_not_atomic = (
    CFlexSymbolic('((long)&pypy_stm_start_if_not_atomic)'))


def rewind_jmp_frame():
    """At some key places, like the entry point of the thread and in the
    function with the interpreter's dispatch loop, this must be called
    (it turns into a marker in the caller's function).  There is one
    automatically in any jit.jit_merge_point()."""
    # special-cased below: the emitted operation must be placed
    # directly in the caller's graph

@specialize.arg(0)
def possible_transaction_break(keep):
    """ keep: should be True for checks that are absolutely
    needed. False means the JIT only keeps the check if it
    thinks that it helps """
    if rgc.stm_is_enabled():
        if llop.stm_should_break_transaction(lltype.Bool, keep):
            break_transaction()

def hint_commit_soon():
    """As the name says, just a hint. Maybe calling it
    several times in a row is more persuasive"""
    llop.stm_hint_commit_soon(lltype.Void)

@dont_look_inside
def become_inevitable():
    llop.stm_become_inevitable(lltype.Void)

@dont_look_inside
def stop_all_other_threads():
    llop.stm_become_globally_unique_transaction(lltype.Void)

def partial_commit_and_resume_other_threads():
    pass    # for now

@specialize.arg(0)
def should_break_transaction(keep):
    # 'keep' should be true at the end of the loops, and false otherwise
    # (it only matters for the JIT)
    return we_are_translated() and (
        llop.stm_should_break_transaction(lltype.Bool, keep))

@dont_look_inside
def break_transaction():
    llop.stm_transaction_break(lltype.Void)

@dont_look_inside
def set_transaction_length(fraction):
    llop.stm_set_transaction_length(lltype.Void, float(fraction))

@dont_look_inside
def increment_atomic():
    llop.stm_increment_atomic(lltype.Void)

@dont_look_inside
def decrement_atomic():
    llop.stm_decrement_atomic(lltype.Void)

@dont_look_inside
def is_atomic():
    return llop.stm_get_atomic(lltype.Signed)

@dont_look_inside
def is_inevitable():
    return llop.stm_is_inevitable(lltype.Signed)

@dont_look_inside
def abort_and_retry():
    llop.stm_abort_and_retry(lltype.Void)

@dont_look_inside
def before_external_call():
    if we_are_translated():
        # this tries to commit, or becomes inevitable if atomic
        llop.stm_commit_if_not_atomic(lltype.Void)
before_external_call._dont_reach_me_in_del_ = True
before_external_call._transaction_break_ = True

@dont_look_inside
def after_external_call():
    if we_are_translated():
        # starts a new transaction if we are not atomic already
        llop.stm_start_if_not_atomic(lltype.Void)
after_external_call._dont_reach_me_in_del_ = True
after_external_call._transaction_break_ = True

@dont_look_inside
def enter_callback_call(rjbuf):
    if we_are_translated():
        return llop.stm_enter_callback_call(lltype.Signed, rjbuf)
enter_callback_call._dont_reach_me_in_del_ = True
enter_callback_call._transaction_break_ = True

@dont_look_inside
def leave_callback_call(rjbuf, token):
    if we_are_translated():
        llop.stm_leave_callback_call(lltype.Void, rjbuf, token)
leave_callback_call._dont_reach_me_in_del_ = True
leave_callback_call._transaction_break_ = True

def register_invoke_around_extcall():
    """Initialize the STM system.
    Called automatically by rthread.start_new_thread()."""
    from rpython.rlib.objectmodel import invoke_around_extcall
    invoke_around_extcall(before_external_call, after_external_call,
                          enter_callback_call, leave_callback_call)

@specialize.argtype(1)
def push_marker(odd_num, object):
    llop.stm_push_marker(lltype.Void, odd_num, object)

def update_marker_num(odd_num):
    llop.stm_update_marker_num(lltype.Void, odd_num)

def pop_marker():
    llop.stm_pop_marker(lltype.Void)

def stm_count():
    return llop.stm_count(lltype.Signed)

# ____________________________________________________________

class _Entry(ExtRegistryEntry):
    _about_ = rewind_jmp_frame

    def compute_result_annotation(self):
        pass

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        if hop.rtyper.annotator.translator.config.translation.stm:
            hop.genop('stm_rewind_jmp_frame', [], resulttype=lltype.Void)

# ____________________________________________________________

_STM_HASHTABLE_P = rffi.COpaquePtr('stm_hashtable_t')

_STM_HASHTABLE_ENTRY = lltype.GcStruct('HASHTABLE_ENTRY',
                                       ('index', lltype.Unsigned),
                                       ('object', llmemory.GCREF))

def ll_hashtable_get(h, key):
    # 'key' must be a plain integer.  Returns a GCREF.
    return llop.stm_hashtable_read(llmemory.GCREF, h, h.ll_raw_hashtable, key)

def ll_hashtable_set(h, key, value):
    llop.stm_hashtable_write(lltype.Void, h, h.ll_raw_hashtable, key, value)

_HASHTABLE_OBJ = lltype.GcStruct('HASHTABLE_OBJ',
                                 ('ll_raw_hashtable', _STM_HASHTABLE_P),
                                 adtmeths={'get': ll_hashtable_get,
                                           'set': ll_hashtable_set})

def ll_hashtable_trace(gc, obj, callback, arg):
    from rpython.memory.gctransform.stmframework import get_visit_function
    visit_fn = get_visit_function(callback, arg)
    addr = obj + llmemory.offsetof(_HASHTABLE_OBJ, 'll_raw_hashtable')
    llop.stm_hashtable_tracefn(lltype.Void, addr.address[0], visit_fn)
lambda_hashtable_trace = lambda: ll_hashtable_trace

def create_hashtable():
    if not we_are_translated():
        return HashtableForTest()      # for tests
    # Pass a null pointer to _STM_HASHTABLE_ENTRY to stm_hashtable_create().
    # Make sure we see a malloc() of it, so that its typeid is correctly
    # initialized.  It can be done in a NonConstant(False) path so that
    # the C compiler will actually drop it.
    if NonConstant(False):
        p = lltype.malloc(_STM_HASHTABLE_ENTRY)
    else:
        p = lltype.nullptr(_STM_HASHTABLE_ENTRY)
    rgc.register_custom_trace_hook(_HASHTABLE_OBJ, lambda_hashtable_trace)
    h = lltype.malloc(_HASHTABLE_OBJ)
    h.ll_raw_hashtable = llop.stm_hashtable_create(_STM_HASHTABLE_P, p)
    return h

NULL_GCREF = lltype.nullptr(llmemory.GCREF.TO)

class HashtableForTest(object):
    def __init__(self):
        self._content = {}      # dict {integer: GCREF}

    def _cleanup_(self):
        raise Exception("cannot translate a prebuilt rstm.Hashtable object")

    def get(self, key):
        assert type(key) is int
        return self._content.get(key, NULL_GCREF)

    def set(self, key, value):
        assert type(key) is int
        assert lltype.typeOf(value) == llmemory.GCREF
        if value:
            self._content[key] = value
        else:
            try:
                del self._content[key]
            except KeyError:
                pass
