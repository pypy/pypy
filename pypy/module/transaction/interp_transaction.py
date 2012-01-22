from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.module.transaction import threadintf
from pypy.rlib import rstm


NUM_THREADS_DEFAULT = 4     # by default


class State(object):

    def _freeze_(self):
        self.__dict__.clear()
        self.running = False
        self.num_threads = NUM_THREADS_DEFAULT
        self.pending = []
        self.pending_lists = {0: self.pending}
        self.ll_lock = threadintf.null_ll_lock
        self.ll_no_tasks_pending_lock = threadintf.null_ll_lock
        self.ll_unfinished_lock = threadintf.null_ll_lock

    def startup(self, space):
        self.space = space
        w_module = space.getbuiltinmodule('transaction')
        self.w_error = space.getattr(w_module, space.wrap('TransactionError'))
        #
        self.ll_lock = threadintf.allocate_lock()
        self.ll_no_tasks_pending_lock = threadintf.allocate_lock()
        self.ll_unfinished_lock = threadintf.allocate_lock()
        self.lock_unfinished()
        self.main_thread_id = threadintf.thread_id()
        self.pending_lists = {self.main_thread_id: self.pending}

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


state = State()
state._freeze_()


@unwrap_spec(num=int)
def set_num_threads(space, num):
    if num < 1:
        num = 1
    state.set_num_threads(num)


class Pending:
    _alloc_nonmovable_ = True

    def __init__(self, w_callback, args):
        self.w_callback = w_callback
        self.args = args

    def register(self):
        id = threadintf.thread_id()
        state.pending_lists[id].append(self)

    def run(self):
        rstm.perform_transaction(Pending._run_in_transaction, Pending, self)

    @staticmethod
    def _run_in_transaction(pending, retry_counter):
        if retry_counter > 0:
            pending.register() # retrying: will be done later, try others first
            return
        if state.got_exception is not None:
            return   # return early if there is already a 'got_exception'
        try:
            space = state.space
            space.call_args(pending.w_callback, pending.args)
        except Exception, e:
            state.got_exception = e


def add(space, w_callback, __args__):
    Pending(w_callback, __args__).register()


def add_list(new_pending_list):
    if len(new_pending_list) == 0:
        return
    was_empty = len(state.pending) == 0
    state.pending += new_pending_list
    del new_pending_list[:]
    if was_empty:
        state.unlock_no_tasks_pending()


def _run_thread():
    state.lock()
    my_pending_list = []
    my_thread_id = threadintf.thread_id()
    state.pending_lists[my_thread_id] = my_pending_list
    rstm.descriptor_init()
    #
    while True:
        if len(state.pending) == 0:
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
            pending = state.pending.pop(0)
            if len(state.pending) == 0:
                state.lock_no_tasks_pending()
            state.unlock()
            pending.run()
            state.lock()
            add_list(my_pending_list)
    #
    rstm.descriptor_done()
    del state.pending_lists[my_thread_id]
    if state.num_waiting_threads == 0:    # only the last thread to leave
        state.unlock_unfinished()
    state.unlock()


def run(space):
    if state.running:
        raise OperationError(
            state.w_error,
            space.wrap("recursive invocation of transaction.run()"))
    assert not state.is_locked_no_tasks_pending()
    if len(state.pending) == 0:
        return
    state.num_waiting_threads = 0
    state.finished = False
    state.running = True
    state.got_exception = None
    #
    for i in range(state.num_threads):
        threadintf.start_new_thread(_run_thread, ())
    #
    state.lock_unfinished()  # wait for all threads to finish
    #
    assert state.num_waiting_threads == 0
    assert len(state.pending) == 0
    assert state.pending_lists.keys() == [state.main_thread_id]
    assert not state.is_locked_no_tasks_pending()
    state.running = False
    #
    # now re-raise the exception that we got in a transaction
    if state.got_exception is not None:
        e = state.got_exception
        state.got_exception = None
        raise e
