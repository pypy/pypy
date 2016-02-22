from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rlib.objectmodel import CDefinedIntSymbolic, stm_ignored
from rpython.rlib.rarithmetic import r_uint
from rpython.rlib.nonconst import NonConstant
from rpython.rlib import rgc
from rpython.rtyper.lltypesystem import lltype, rffi, rstr, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rlib.jit import dont_look_inside

class CFlexSymbolic(CDefinedIntSymbolic):
    _compare_by_id_ = True


TID = rffi.UINT
STMFLAGS = rffi.UINT
tid_offset = CFlexSymbolic('offsetof(struct rpyobj_s, tid)')
stmflags_offset = CFlexSymbolic('offsetof(struct rpyobj_s, lib)')
stm_nb_segments = CFlexSymbolic('STM_NB_SEGMENTS')
adr_nursery_free = CFlexSymbolic('((long)&STM_SEGMENT->nursery_current)')
adr_nursery_top  = CFlexSymbolic('((long)&STM_SEGMENT->nursery_end)')
adr_nursery_mark = CFlexSymbolic('((long)&STM_SEGMENT->nursery_mark)')
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
adr_write_slowpath_card = (
    CFlexSymbolic('((long)&_stm_write_slowpath_card)'))

CARD_MARKED = CFlexSymbolic('_STM_CARD_MARKED')
CARD_BITS   = CFlexSymbolic('_STM_CARD_BITS')
CARD_SIZE   = CFlexSymbolic('_STM_CARD_SIZE')

GCFLAG_CARDS_SET = CFlexSymbolic('_STM_GCFLAG_CARDS_SET')
GCFLAG_WRITE_BARRIER = CFlexSymbolic('_STM_GCFLAG_WRITE_BARRIER')
FAST_ALLOC = CFlexSymbolic('_STM_FAST_ALLOC')

adr_pypy__rewind_jmp_copy_stack_slice = (
    CFlexSymbolic('((long)&pypy__rewind_jmp_copy_stack_slice)'))
adr_stm_detached_inevitable_from_thread = (
    CFlexSymbolic('((long)&_stm_detached_inevitable_from_thread)'))
adr_stm_thread_local_self_or_0_if_atomic = (
    CFlexSymbolic('((long)&stm_thread_local.self_or_0_if_atomic)'))
adr_stm_leave_noninevitable_transactional_zone = (
    CFlexSymbolic('((long)&_stm_leave_noninevitable_transactional_zone)'))
adr_stm_reattach_transaction = (
    CFlexSymbolic('((long)&_stm_reattach_transaction)'))


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
            return True
    return False

def hint_commit_soon():
    """As the name says, just a hint. Maybe calling it
    several times in a row is more persuasive"""
    llop.stm_hint_commit_soon(lltype.Void)

@dont_look_inside
def become_inevitable():
    llop.stm_become_inevitable(lltype.Void)

@dont_look_inside
def stop_all_other_threads():
    llop.stm_stop_all_other_threads(lltype.Void)

@dont_look_inside
def resume_all_other_threads():
    llop.stm_resume_all_other_threads(lltype.Void)

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
        llop.stm_leave_transactional_zone(lltype.Void)
before_external_call._dont_reach_me_in_del_ = True
before_external_call._transaction_break_ = True

@dont_look_inside
def after_external_call():
    if we_are_translated():
        llop.stm_enter_transactional_zone(lltype.Void)
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

@specialize.argtype(1)
def push_marker(odd_num, object):
    llop.stm_push_marker(lltype.Void, odd_num, object)

def update_marker_num(odd_num):
    llop.stm_update_marker_num(lltype.Void, odd_num)

def pop_marker():
    llop.stm_pop_marker(lltype.Void)

@dont_look_inside
def stm_count():
    return llop.stm_count(lltype.Signed)

@specialize.ll()
def allocate_preexisting(p):
    """Return a copy of p, which must be a Ptr(GcStruct), which
    we pretend existed all along (including in other transactions).
    Used in cases where other concurrent transactions have a non-
    official way to get a pointer to that object even before we commit.
    The copied content should be the "default initial" state which
    the current transaction can then proceed to change normally.  This
    initial state must not contain GC pointers to any other uncommitted
    object."""
    # XXX is this buggy?
    TP = lltype.typeOf(p)
    size = llmemory.sizeof(TP.TO)
    return llop.stm_allocate_preexisting(TP, size, p)

@dont_look_inside
@specialize.ll()
def allocate_noconflict(GCTYPE, n=None):
    """Return a new instance of GCTYPE that never generates conflicts when
    reading or writing to it. However, modifications may get lost
    and are not guaranteed to propagate."""
    if not we_are_translated(): # for tests
        return lltype.malloc(GCTYPE, n=n)
    #
    if n is None:
        return llop.stm_malloc_noconflict(lltype.Ptr(GCTYPE))
    else:
        return llop.stm_malloc_noconflict_varsize(lltype.Ptr(GCTYPE), n)

@specialize.ll()
def allocate_nonmovable(GCTYPE):
    return llop.stm_malloc_nonmovable(lltype.Ptr(GCTYPE))

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
_STM_HASHTABLE_TABLE_P = rffi.COpaquePtr('stm_hashtable_table_t')

_STM_HASHTABLE_ENTRY = lltype.GcStruct('HASHTABLE_ENTRY',
                                       ('index', lltype.Unsigned),
                                       ('object', llmemory.GCREF))
_STM_HASHTABLE_ENTRY_P = lltype.Ptr(_STM_HASHTABLE_ENTRY)
_STM_HASHTABLE_ENTRY_PP = rffi.CArrayPtr(_STM_HASHTABLE_ENTRY_P)
_STM_HASHTABLE_ENTRY_ARRAY = lltype.GcArray(_STM_HASHTABLE_ENTRY_P)

@dont_look_inside
def _ll_hashtable_get(h, key):
    # 'key' must be a plain integer.  Returns a GCREF.
    return llop.stm_hashtable_read(llmemory.GCREF, h, h.ll_raw_hashtable, key)

@dont_look_inside
def _ll_hashtable_set(h, key, value):
    llop.stm_hashtable_write(lltype.Void, h, h.ll_raw_hashtable, key, value)

@dont_look_inside
def _ll_hashtable_len(h):
    return llop.stm_hashtable_list(lltype.Signed, h, h.ll_raw_hashtable,
                                   lltype.nullptr(_STM_HASHTABLE_ENTRY_ARRAY))

@dont_look_inside
def _ll_hashtable_len_estimate(h):
    return llop.stm_hashtable_length_upper_bound(lltype.Signed,
                                                 h.ll_raw_hashtable)

@dont_look_inside
def _ll_hashtable_list(h):
    upper_bound = llop.stm_hashtable_length_upper_bound(lltype.Signed,
                                                        h.ll_raw_hashtable)
    array = lltype.malloc(_STM_HASHTABLE_ENTRY_ARRAY, upper_bound)
    # 'array' is newly allocated, thus we don't need to do a manual
    # write_barrier for stm as requested by stm_hashtable_list
    count = llop.stm_hashtable_list(lltype.Signed, h, h.ll_raw_hashtable,
                                    lltype.direct_arrayitems(array))
    return (array, count)

@dont_look_inside
def _ll_hashtable_lookup(h, key):
    return llop.stm_hashtable_lookup(_STM_HASHTABLE_ENTRY_P,
                                     h, h.ll_raw_hashtable, key)

@dont_look_inside
def _ll_hashtable_writeobj(h, entry, value):
    llop.stm_hashtable_write_entry(lltype.Void, h, entry, value)

@dont_look_inside
def _ll_hashtable_iterentries(h):
    rgc.register_custom_trace_hook(_HASHTABLE_ITER_OBJ,
                                   lambda_hashtable_iter_trace)
    table = llop.stm_hashtable_iter(_STM_HASHTABLE_TABLE_P, h.ll_raw_hashtable)
    hiter = lltype.malloc(_HASHTABLE_ITER_OBJ)
    hiter.hashtable = h    # for keepalive
    hiter.table = table
    hiter.prev = lltype.nullptr(_STM_HASHTABLE_ENTRY_PP.TO)
    return hiter

@dont_look_inside
def _ll_hashiter_next(hiter):
    entrypp = llop.stm_hashtable_iter_next(_STM_HASHTABLE_ENTRY_PP,
                                           hiter.hashtable,
                                           hiter.table,
                                           hiter.prev)
    if not entrypp:
        raise StopIteration
    hiter.prev = entrypp
    return entrypp[0]

_HASHTABLE_OBJ = lltype.GcStruct('HASHTABLE_OBJ',
                                 ('ll_raw_hashtable', _STM_HASHTABLE_P),
                                 hints={'immutable': True},
                                 rtti=True,
                                 adtmeths={'get': _ll_hashtable_get,
                                           'set': _ll_hashtable_set,
                                           'len': _ll_hashtable_len,
                                  'len_estimate': _ll_hashtable_len_estimate,
                                          'list': _ll_hashtable_list,
                                        'lookup': _ll_hashtable_lookup,
                                      'writeobj': _ll_hashtable_writeobj,
                                   'iterentries': _ll_hashtable_iterentries})
NULL_HASHTABLE = lltype.nullptr(_HASHTABLE_OBJ)

_HASHTABLE_ITER_OBJ = lltype.GcStruct('HASHTABLE_ITER_OBJ',
                                      ('hashtable', lltype.Ptr(_HASHTABLE_OBJ)),
                                      ('table', _STM_HASHTABLE_TABLE_P),
                                      ('prev', _STM_HASHTABLE_ENTRY_PP),
                                      adtmeths={'next': _ll_hashiter_next})

def _ll_hashtable_trace(gc, obj, callback, arg):
    from rpython.memory.gctransform.stmframework import get_visit_function
    visit_fn = get_visit_function(callback, arg)
    addr = obj + llmemory.offsetof(_HASHTABLE_OBJ, 'll_raw_hashtable')
    llop.stm_hashtable_tracefn(lltype.Void, obj, addr.address[0], visit_fn)
lambda_hashtable_trace = lambda: _ll_hashtable_trace

def _ll_hashtable_finalizer(h):
    if h.ll_raw_hashtable:
        llop.stm_hashtable_free(lltype.Void, h.ll_raw_hashtable)
lambda_hashtable_finlz = lambda: _ll_hashtable_finalizer

def _ll_hashtable_iter_trace(gc, obj, callback, arg):
    from rpython.memory.gctransform.stmframework import get_visit_function
    addr = obj + llmemory.offsetof(_HASHTABLE_ITER_OBJ, 'hashtable')
    gc._trace_callback(callback, arg, addr)
    visit_fn = get_visit_function(callback, arg)
    addr = obj + llmemory.offsetof(_HASHTABLE_ITER_OBJ, 'table')
    llop.stm_hashtable_iter_tracefn(lltype.Void, addr.address[0], visit_fn)
lambda_hashtable_iter_trace = lambda: _ll_hashtable_iter_trace

_false = CDefinedIntSymbolic('0', default=0)    # remains in the C code

@dont_look_inside
def create_hashtable():
    if not we_are_translated():
        return HashtableForTest()      # for tests
    rgc.register_custom_light_finalizer(_HASHTABLE_OBJ, lambda_hashtable_finlz)
    rgc.register_custom_trace_hook(_HASHTABLE_OBJ, lambda_hashtable_trace)
    # Pass a null pointer to _STM_HASHTABLE_ENTRY to stm_hashtable_create().
    # Make sure we see a malloc() of it, so that its typeid is correctly
    # initialized.  It can be done in a NonConstant(False) path so that
    # the C compiler will actually drop it.
    if _false:
        p = lltype.malloc(_STM_HASHTABLE_ENTRY)
    else:
        p = lltype.nullptr(_STM_HASHTABLE_ENTRY)
    h = lltype.malloc(_HASHTABLE_OBJ, zero=True)
    h.ll_raw_hashtable = llop.stm_hashtable_create(_STM_HASHTABLE_P, p)
    return h

NULL_GCREF = lltype.nullptr(llmemory.GCREF.TO)

class HashtableForTest(object):
    def __init__(self):
        self._content = {}      # dict {integer: Entry(obj=GCREF)}

    def _cleanup_(self):
        raise Exception("cannot translate a prebuilt rstm.Hashtable object")

    def get(self, key):
        assert type(key) is int
        return self.lookup(key).object
        # return self._content.get(key, NULL_GCREF)

    def set(self, key, value):
        assert type(key) is int
        assert lltype.typeOf(value) == llmemory.GCREF
        if value:
            entry = self.lookup(key)
            entry._obj = value
            # self._content[key] = value
        else:
            try:
                # set entry to value (since somebody may still have
                # a reference to it), then delete it from the table,
                # as that may happen *anytime* if _obj==NULL
                entry = self.lookup(key)
                entry._obj = value
                del self._content[key]
            except KeyError:
                pass

    def len(self):
        items = [self.lookup(key) for key, v in self._content.items() if v.object != NULL_GCREF]
        return len(items)

    def len_estimate(self):
        return len(self._content)

    def list(self):
        items = [self.lookup(key) for key, v in self._content.items() if v.object != NULL_GCREF]
        count = len(items)
        for i in range(3):
            items.append("additional garbage for testing")
        return items, count

    def lookup(self, key):
        assert type(key) is int
        return self._content.setdefault(key, EntryObjectForTest(self, key))

    def writeobj(self, entry, nvalue):
        assert isinstance(entry, EntryObjectForTest)
        self.set(entry.key, nvalue)

    def iterentries(self):
        return IterEntriesForTest(self, self._content.itervalues())

class EntryObjectForTest(object):
    def __init__(self, hashtable, key):
        self.hashtable = hashtable
        self.key = key
        self.index = r_uint(key)
        self._obj = NULL_GCREF

    def _getobj(self):
        return self._obj
    def _setobj(self, nvalue):
        raise Exception("can't assign to the 'object' attribute:"
                        " use h.writeobj() instead")

    object = property(_getobj, _setobj)

class IterEntriesForTest(object):
    def __init__(self, hashtable, iterator):
        self.hashtable = hashtable
        self.iterator = iterator

    def next(self):
        while 1:
            entry = next(self.iterator)
            if entry._obj:
                return entry

# ____________________________________________________________

_STM_QUEUE_P = rffi.COpaquePtr('stm_queue_t')

@dont_look_inside
def _ll_queue_get(q, timeout=-1.0):
    # Returns a GCREF.
    return llop.stm_queue_get(llmemory.GCREF, q, q.ll_raw_queue, timeout)

@dont_look_inside
def _ll_queue_put(q, newitem):
    llop.stm_queue_put(lltype.Void, q, q.ll_raw_queue, newitem)

@dont_look_inside
def _ll_queue_task_done(q):
    llop.stm_queue_task_done(lltype.Void, q.ll_raw_queue)

@dont_look_inside
def _ll_queue_join(q):
    return llop.stm_queue_join(lltype.Signed, q, q.ll_raw_queue)

_QUEUE_OBJ = lltype.GcStruct('QUEUE_OBJ',
                             ('ll_raw_queue', _STM_QUEUE_P),
                             hints={'immutable': True},
                             rtti=True,
                             adtmeths={'get': _ll_queue_get,
                                       'put': _ll_queue_put,
                                       'task_done': _ll_queue_task_done,
                                       'join': _ll_queue_join})
NULL_QUEUE = lltype.nullptr(_QUEUE_OBJ)

def _ll_queue_trace(gc, obj, callback, arg):
    from rpython.memory.gctransform.stmframework import get_visit_function
    visit_fn = get_visit_function(callback, arg)
    addr = obj + llmemory.offsetof(_QUEUE_OBJ, 'll_raw_queue')
    llop.stm_queue_tracefn(lltype.Void, addr.address[0], visit_fn)
lambda_queue_trace = lambda: _ll_queue_trace

def _ll_queue_finalizer(q):
    if q.ll_raw_queue:
        llop.stm_queue_free(lltype.Void, q.ll_raw_queue)
lambda_queue_finlz = lambda: _ll_queue_finalizer

@dont_look_inside
def create_queue():
    if not we_are_translated():
        return QueueForTest()      # for tests
    rgc.register_custom_light_finalizer(_QUEUE_OBJ, lambda_queue_finlz)
    rgc.register_custom_trace_hook(_QUEUE_OBJ, lambda_queue_trace)
    q = lltype.malloc(_QUEUE_OBJ, zero=True)
    q.ll_raw_queue = llop.stm_queue_create(_STM_QUEUE_P)
    return q

class QueueForTest(object):
    def __init__(self):
        import Queue
        self._content = Queue.Queue()
        self._Empty = Queue.Empty

    def _cleanup_(self):
        raise Exception("cannot translate a prebuilt rstm.Queue object")

    def get(self, timeout=-1.0):
        if timeout < 0.0:
            return self._content.get()
        try:
            if timeout == 0.0:
                return self._content.get(block=False)
            else:
                return self._content.get(timeout=timeout)
        except self._Empty:
            return NULL_GCREF

    def put(self, newitem):
        assert lltype.typeOf(newitem) == llmemory.GCREF
        self._content.put(newitem)

    def task_done(self):
        self._content.task_done()

    def join(self):
        self._content.join()
        return 0
