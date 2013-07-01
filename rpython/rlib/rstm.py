from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.extregistry import ExtRegistryEntry


def become_inevitable():
    llop.stm_become_inevitable(lltype.Void)

def should_break_transaction():
    return we_are_translated() and (
        llop.stm_should_break_transaction(lltype.Bool))

def set_transaction_length(length):
    llop.stm_set_transaction_length(lltype.Void, length)

def increment_atomic():
    llop.stm_change_atomic(lltype.Signed, +1)

def decrement_atomic():
    llop.stm_change_atomic(lltype.Signed, -1)

def is_atomic():
    return llop.stm_get_atomic(lltype.Signed)

def abort_info_push(instance, fieldnames):
    "Special-cased below."

def abort_info_pop(count):
    if we_are_translated():
        stmgcintf.StmOperations.abort_info_pop(count)

def charp_inspect_abort_info():
    return stmgcintf.StmOperations.inspect_abort_info()

def abort_and_retry():
    stmgcintf.StmOperations.abort_and_retry()

def before_external_call():
    llop.stm_commit_transaction(lltype.Void)
before_external_call._dont_reach_me_in_del_ = True
before_external_call._transaction_break_ = True

def after_external_call():
    llop.stm_begin_inevitable_transaction(lltype.Void)
after_external_call._dont_reach_me_in_del_ = True
after_external_call._transaction_break_ = True

def enter_callback_call():
    # XXX assumes that we're not called in a fresh new thread
    llop.stm_begin_inevitable_transaction(lltype.Void)
    return 0
enter_callback_call._dont_reach_me_in_del_ = True
enter_callback_call._transaction_break_ = True

def leave_callback_call(ignored):
    llop.stm_commit_transaction(lltype.Void)
leave_callback_call._dont_reach_me_in_del_ = True
leave_callback_call._transaction_break_ = True

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
            else:
                raise NotImplementedError(
                    "abort_info_push(%s, %r): field of type %r"
                    % (STRUCT.__name__, fieldname, TYPE))
            lst.append(kind)
            lst.append(llmemory.offsetof(STRUCT, fieldname))
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
