from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rlib.objectmodel import CDefinedIntSymbolic
from rpython.rlib.rgc import stm_is_enabled
from rpython.rtyper.lltypesystem import lltype, rffi, rstr, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rlib.jit import dont_look_inside

class CFlexSymbolic(CDefinedIntSymbolic):
    _compare_by_id_ = True


TID = rffi.UINT
tid_offset = CFlexSymbolic('offsetof(struct rpyobj_s, tid)')
stm_nb_segments = CFlexSymbolic('STM_NB_SEGMENTS')
stm_stack_marker_new = CFlexSymbolic('STM_STACK_MARKER_NEW')
stm_stack_marker_old = CFlexSymbolic('STM_STACK_MARKER_OLD')
adr_nursery_free = CFlexSymbolic('((long)&STM_SEGMENT->nursery_current)')
adr_nursery_top  = CFlexSymbolic('((long)&STM_SEGMENT->nursery_end)')
adr_pypy_stm_nursery_low_fill_mark = (
    CFlexSymbolic('((long)&pypy_stm_nursery_low_fill_mark)'))
adr_transaction_read_version = (
    CFlexSymbolic('((long)&STM_SEGMENT->transaction_read_version)'))
adr_jmpbuf_ptr = (
    CFlexSymbolic('((long)&STM_SEGMENT->jmpbuf_ptr)'))
adr_segment_base = (
    CFlexSymbolic('((long)&STM_SEGMENT->segment_base)'))
adr_write_slowpath = CFlexSymbolic('((long)&_stm_write_slowpath)')
adr_write_slowpath_card_extra = (
    CFlexSymbolic('((long)&_stm_write_slowpath_card_extra)'))
adr__stm_write_slowpath_card_extra_base = (
   CFlexSymbolic('(_stm_write_slowpath_card_extra_base()-0x4000000000000000L)'))
CARD_MARKED = CFlexSymbolic('_STM_CARD_MARKED')
CARD_SIZE   = CFlexSymbolic('_STM_CARD_SIZE')

adr__pypy_stm_become_inevitable = (
    CFlexSymbolic('((long)&_pypy_stm_become_inevitable)'))
adr_stm_commit_transaction = (
    CFlexSymbolic('((long)&stm_commit_transaction)'))
adr_pypy_stm_start_transaction = (
    CFlexSymbolic('((long)&pypy_stm_start_transaction)'))


def rewind_jmp_frame():
    """At some key places, like the entry point of the thread and in the
    function with the interpreter's dispatch loop, this must be called
    (it turns into a marker in the caller's function).  There is one
    automatically in any jit.jit_merge_point()."""
    # special-cased below: the emitted operation must be placed
    # directly in the caller's graph

def possible_transaction_break():
    if stm_is_enabled():
        if llop.stm_should_break_transaction(lltype.Bool):
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

def should_break_transaction():
    return we_are_translated() and (
        llop.stm_should_break_transaction(lltype.Bool))

@dont_look_inside
def break_transaction():
    llop.stm_break_transaction(lltype.Void)

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

@dont_look_inside    # XXX allow looking inside this function
def longest_marker_time():
    return llop.stm_longest_marker_time(lltype.Float)

@dont_look_inside
def longest_abort_info():
    state = llop.stm_longest_marker_state(lltype.Signed)
    time = llop.stm_longest_marker_time(lltype.Float)
    cself = llop.stm_longest_marker_self(rffi.CCHARP)
    cother = llop.stm_longest_marker_other(rffi.CCHARP)
    return (state, time, rffi.charp2str(cself), rffi.charp2str(cother))

@dont_look_inside
def reset_longest_abort_info():
    llop.stm_reset_longest_marker_state(lltype.Void)

# ____________________________________________________________

class _Entry(ExtRegistryEntry):
    _about_ = rewind_jmp_frame

    def compute_result_annotation(self):
        pass

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        if hop.rtyper.annotator.translator.config.translation.stm:
            hop.genop('stm_rewind_jmp_frame', [], resulttype=lltype.Void)
