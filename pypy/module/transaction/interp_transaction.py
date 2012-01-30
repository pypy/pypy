from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.module.transaction import threadintf
from pypy.module.transaction.fifo import Fifo
from pypy.rlib import rstm


NUM_THREADS_DEFAULT = 4     # by default

MAIN_THREAD_ID = 0


class State(object):

    def initialize(self, space):
        self.space = space
        self.running = False
        self.num_threads = NUM_THREADS_DEFAULT
        #
        self.w_error = None
        self.ll_lock = threadintf.null_ll_lock
        self.ll_no_tasks_pending_lock = threadintf.null_ll_lock
        self.ll_unfinished_lock = threadintf.null_ll_lock
        self.threadobjs = {}      # empty during translation
        self.pending = Fifo()

    def _freeze_(self):
        self.threadobjs.clear()
        return False

    def startup(self, space, w_module):
        assert space is self.space
        if w_module is not None:     # for tests
            self.w_error = space.getattr(w_module,
                                         space.wrap('TransactionError'))
        self.ll_lock = threadintf.allocate_lock()
        self.ll_no_tasks_pending_lock = threadintf.allocate_lock()
        self.ll_unfinished_lock = threadintf.allocate_lock()
        self.lock_unfinished()
        self.startup_run()

    def startup_run(self):
        # this is called at the start of run() too, in order to make
        # test_checkmodule happy
        main_ec = self.space.getexecutioncontext()    # create it if needed
        main_ec._transaction_pending = self.pending

    def add_thread(self, id, ec):
        # register a new transaction thread
        assert id not in self.threadobjs
        ec._transaction_pending = Fifo()
        self.threadobjs[id] = ec

    def del_thread(self, id):
        # un-register a transaction thread
        del self.threadobjs[id]

    # ---------- interface for ThreadLocals ----------
    # This works really like a thread-local, which may have slightly
    # strange consequences in multiple transactions, because you don't
    # know on which thread a transaction will run.  The point of this is
    # to let every thread get its own ExecutionContext; otherwise, they
    # conflict with each other e.g. when setting the 'topframeref'
    # attribute.

    def getvalue(self):
        id = rstm.thread_id()
        return self.threadobjs.get(id, None)

    def setvalue(self, value):
        id = rstm.thread_id()
        assert id == MAIN_THREAD_ID   # should not be used from a transaction
        self.threadobjs[id] = value

    def getmainthreadvalue(self):
        return self.threadobjs[0]

    def getallvalues(self):
        return self.threadobjs

    # ----------

    def set_num_threads(self, num):
        if self.running:
            space = self.space
            raise OperationError(space.w_ValueError,
                                 space.wrap("cannot change the number of "
                                            "threads when transaction.run() "
                                            "is active"))
        self.num_threads = num

    def lock(self):
        # XXX think about the interaction between locks and the GC
        threadintf.acquire(self.ll_lock, True)

    def unlock(self):
        threadintf.release(self.ll_lock)

    def lock_no_tasks_pending(self):
        threadintf.acquire(self.ll_no_tasks_pending_lock, True)

    def unlock_no_tasks_pending(self):
        threadintf.release(self.ll_no_tasks_pending_lock)

    def is_locked_no_tasks_pending(self):
        just_locked = threadintf.acquire(self.ll_no_tasks_pending_lock, False)
        if just_locked:
            threadintf.release(self.ll_no_tasks_pending_lock)
        return not just_locked

    def lock_unfinished(self):
        threadintf.acquire(self.ll_unfinished_lock, True)

    def unlock_unfinished(self):
        threadintf.release(self.ll_unfinished_lock)

    def init_exceptions(self):
        self._reraise_exception = None

    def has_exception(self):
        return self._reraise_exception is not None

    def must_reraise_exception(self, reraise_callback):
        self._reraise_exception = reraise_callback

    def close_exceptions(self):
        if self._reraise_exception is not None:
            self._reraise_exception()


state = State()


@unwrap_spec(num=int)
def set_num_threads(space, num):
    if num < 1:
        num = 1
    state.set_num_threads(num)


class AbstractPending(object):
    _alloc_nonmovable_ = True

    def register(self):
        ec = state.getvalue()
        ec._transaction_pending.append(self)

    def run(self):
        # may also be overridden
        rstm.perform_transaction(AbstractPending._run_in_transaction,
                                 AbstractPending, self)

    @staticmethod
    def _run_in_transaction(pending, retry_counter):
        if retry_counter > 0:
            pending.register() # retrying: will be done later, try others first
            return
        if state.has_exception():
            return   # return early if there is already an exception to reraise
        try:
            pending.run_in_transaction(state.space)
        except Exception, e:
            state.got_exception_applevel = e
            state.must_reraise_exception(_reraise_from_applevel)


class Pending(AbstractPending):
    def __init__(self, w_callback, args):
        self.w_callback = w_callback
        self.args = args

    def run_in_transaction(self, space):
        space.call_args(self.w_callback, self.args)


def _reraise_from_applevel():
    e = state.got_exception_applevel
    state.got_exception_applevel = None
    raise e


def add(space, w_callback, __args__):
    Pending(w_callback, __args__).register()


def _add_list(new_pending_list):
    if new_pending_list.is_empty():
        return
    was_empty = state.pending.is_empty()
    state.pending.steal(new_pending_list)
    if was_empty:
        state.unlock_no_tasks_pending()


def _run_thread():
    state.lock()
    rstm.descriptor_init()
    my_thread_id = rstm.thread_id()
    my_ec = state.space.createexecutioncontext()
    state.add_thread(my_thread_id, my_ec)
    #
    while True:
        if state.pending.is_empty():
            assert state.is_locked_no_tasks_pending()
            state.num_waiting_threads += 1
            if state.num_waiting_threads == state.num_threads:
                state.finished = True
                state.unlock_no_tasks_pending()
            state.unlock()
            #
            state.lock_no_tasks_pending()
            state.unlock_no_tasks_pending()
            #
            state.lock()
            state.num_waiting_threads -= 1
            if state.finished:
                break
        else:
            pending = state.pending.popleft()
            if state.pending.is_empty():
                state.lock_no_tasks_pending()
            state.unlock()
            pending.run()
            state.lock()
            _add_list(my_ec._transaction_pending)
    #
    state.del_thread(my_thread_id)
    rstm.descriptor_done()
    if state.num_waiting_threads == 0:    # only the last thread to leave
        state.unlock_unfinished()
    state.unlock()


def run(space):
    if state.running:
        raise OperationError(
            state.w_error,
            space.wrap("recursive invocation of transaction.run()"))
    state.startup_run()
    assert not state.is_locked_no_tasks_pending()
    if state.pending.is_empty():
        return
    state.num_waiting_threads = 0
    state.finished = False
    state.running = True
    state.init_exceptions()
    #
    for i in range(state.num_threads):
        threadintf.start_new_thread(_run_thread, ())
    #
    state.lock_unfinished()  # wait for all threads to finish
    #
    assert state.num_waiting_threads == 0
    assert state.pending.is_empty()
    assert state.threadobjs.keys() == [MAIN_THREAD_ID]
    assert not state.is_locked_no_tasks_pending()
    state.running = False
    #
    # now re-raise the exception that we got in a transaction
    state.close_exceptions()
