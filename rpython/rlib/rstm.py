from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rlib.objectmodel import CDefinedIntSymbolic
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
adr_transaction_read_version = (
    CFlexSymbolic('((long)&STM_SEGMENT->transaction_read_version)'))
adr_jmpbuf_ptr = (
    CFlexSymbolic('((long)&STM_SEGMENT->jmpbuf_ptr)'))
adr_write_slowpath = CFlexSymbolic('((long)&_stm_write_slowpath)')

adr__pypy_stm_become_inevitable = (
    CFlexSymbolic('((long)&_pypy_stm_become_inevitable)'))
adr_stm_commit_transaction = (
    CFlexSymbolic('((long)&stm_commit_transaction)'))
adr_pypy_stm_start_transaction = (
    CFlexSymbolic('((long)&pypy_stm_start_transaction)'))


def jit_stm_transaction_break_point():
    # XXX REFACTOR AWAY
    if we_are_translated():
        llop.jit_stm_transaction_break_point(lltype.Void)

def jit_stm_should_break_transaction(if_there_is_no_other):
    # XXX REFACTOR AWAY
    # if_there_is_no_other means that we use this point only
    # if there is no other break point in the trace.
    # If it is False, the point may be used if it comes right
    # after a CALL_RELEASE_GIL
    return llop.jit_stm_should_break_transaction(lltype.Bool,
                                                 if_there_is_no_other)

@dont_look_inside
def become_inevitable():
    llop.stm_become_inevitable(lltype.Void)

@dont_look_inside
def stop_all_other_threads():
    llop.stm_become_globally_unique_transaction(lltype.Void)

def partial_commit_and_resume_other_threads():
    pass    # for now

@dont_look_inside
def should_break_transaction():
    return we_are_translated() and (
        llop.stm_should_break_transaction(lltype.Bool))

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

def abort_info_push(instance, fieldnames):
    "Special-cased below."

@dont_look_inside
def abort_info_pop(count):
    if we_are_translated():
        llop.stm_abort_info_pop(lltype.Void, count)

@dont_look_inside
def charp_inspect_abort_info():
    return llop.stm_inspect_abort_info(rffi.CCHARP)

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
        llop.stm_start_inevitable_if_not_atomic(lltype.Void)
after_external_call._dont_reach_me_in_del_ = True
after_external_call._transaction_break_ = True

@dont_look_inside
def enter_callback_call():
    if we_are_translated():
        return llop.stm_enter_callback_call(lltype.Signed)
enter_callback_call._dont_reach_me_in_del_ = True
enter_callback_call._transaction_break_ = True

@dont_look_inside
def leave_callback_call(token):
    if we_are_translated():
        llop.stm_leave_callback_call(lltype.Void, token)
leave_callback_call._dont_reach_me_in_del_ = True
leave_callback_call._transaction_break_ = True

def register_invoke_around_extcall():
    """Initialize the STM system.
    Called automatically by rthread.start_new_thread()."""
    from rpython.rlib.objectmodel import invoke_around_extcall
    invoke_around_extcall(before_external_call, after_external_call,
                          enter_callback_call, leave_callback_call)

# ____________________________________________________________

def make_perform_transaction(func, CONTAINERP):
    from rpython.rtyper.annlowlevel import llhelper
    from rpython.rtyper.annlowlevel import cast_instance_to_base_ptr
    from rpython.translator.stm.stmgcintf import CALLBACK_TX
    #
    def _stm_callback(llcontainer, retry_counter):
        llcontainer = rffi.cast(CONTAINERP, llcontainer)
        retry_counter = rffi.cast(lltype.Signed, retry_counter)
        try:
            res = func(llcontainer, retry_counter)
        except Exception, e:
            res = 0     # ends perform_transaction() and returns
            lle = cast_instance_to_base_ptr(e)
            llcontainer.got_exception = lle
        return rffi.cast(rffi.INT_real, res)
    #
    @dont_look_inside
    def perform_transaction(llcontainer):
        llcallback = llhelper(CALLBACK_TX, _stm_callback)
        llop.stm_perform_transaction(lltype.Void, llcontainer, llcallback)
    perform_transaction._transaction_break_ = True
    #
    return perform_transaction

# ____________________________________________________________

class AbortInfoPush(ExtRegistryEntry):
    _about_ = abort_info_push

    def compute_result_annotation(self, s_instance, s_fieldnames):
        from rpython.annotator.model import SomeInstance
        assert isinstance(s_instance, SomeInstance)
        assert s_fieldnames.is_constant()
        assert isinstance(s_fieldnames.const, tuple)  # tuple of names

    def specialize_call(self, hop):
        fieldnames = hop.args_s[1].const
        lst = []
        v_instance = hop.inputarg(hop.args_r[0], arg=0)
        for fieldname in fieldnames:
            if fieldname == '[':
                lst.append(-2)    # start of sublist
                continue
            if fieldname == ']':
                lst.append(-1)    # end of sublist
                continue
            fieldname = 'inst_' + fieldname
            extraofs = None
            STRUCT = v_instance.concretetype.TO
            while not hasattr(STRUCT, fieldname):
                STRUCT = STRUCT.super
            TYPE = getattr(STRUCT, fieldname)
            if TYPE == lltype.Signed:
                kind = 1
            elif TYPE == lltype.Unsigned:
                kind = 2
            elif TYPE == lltype.Ptr(rstr.STR):
                kind = 3
                extraofs = llmemory.offsetof(rstr.STR, 'chars')
            else:
                raise NotImplementedError(
                    "abort_info_push(%s, %r): field of type %r"
                    % (STRUCT.__name__, fieldname, TYPE))
            lst.append(kind)
            lst.append(llmemory.offsetof(STRUCT, fieldname))
            if extraofs is not None:
                lst.append(extraofs)
        lst.append(0)
        ARRAY = rffi.CArray(lltype.Signed)
        array = lltype.malloc(ARRAY, len(lst), flavor='raw', immortal=True)
        for i in range(len(lst)):
            array[i] = lst[i]
        c_array = hop.inputconst(lltype.Ptr(ARRAY), array)
        hop.exception_cannot_occur()
        hop.genop('stm_abort_info_push', [v_instance, c_array])

# ____________________________________________________________

class ThreadLocalReference(object):
    _COUNT = 1

    def __init__(self, Cls):
        "NOT_RPYTHON: must be prebuilt"
        import thread
        self.Cls = Cls
        self.local = thread._local()      # <- NOT_RPYTHON
        self.unique_id = ThreadLocalReference._COUNT
        ThreadLocalReference._COUNT += 1

    def _freeze_(self):
        return True

    @specialize.arg(0)
    def get(self):
        if we_are_translated():
            from rpython.rtyper.lltypesystem import rclass
            from rpython.rtyper.annlowlevel import cast_base_ptr_to_instance
            ptr = llop.stm_threadlocalref_get(rclass.OBJECTPTR, self.unique_id)
            return cast_base_ptr_to_instance(self.Cls, ptr)
        else:
            return getattr(self.local, 'value', None)

    @specialize.arg(0)
    def set(self, value):
        assert isinstance(value, self.Cls) or value is None
        if we_are_translated():
            from rpython.rtyper.annlowlevel import cast_instance_to_base_ptr
            ptr = cast_instance_to_base_ptr(value)
            llop.stm_threadlocalref_set(lltype.Void, self.unique_id, ptr)
        else:
            self.local.value = value
