from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.module.transaction import threadintf


NUM_THREADS_DEFAULT = 4     # by default


class State(object):

    def _freeze_(self):
        self.__dict__.clear()
        self.running = False
        self.num_threads = NUM_THREADS_DEFAULT

    def startup(self, space):
        self.space = space
        self.pending = []
        self.ll_lock = threadintf.allocate_lock()
        self.ll_no_tasks_pending_lock = threadintf.allocate_lock()
        self.ll_unfinished_lock = threadintf.allocate_lock()
        self.w_error = space.new_exception_class(
            "transaction.TransactionError")
        self.lock_no_tasks_pending()
        self.lock_unfinished()

    def set_num_threads(self, num):
        if self.running:
            space = self.space
            raise OperationError(space.w_ValueError,
                                 space.wrap("cannot change the number of "
                                            "threads when transaction.run() "
                                            "is active"))
        self.num_threads = num_threads

    def lock(self):
        # XXX think about the interaction between locks and the GC
        threadintf.acquire(self.ll_lock, True)

    def unlock(self):
        threadintf.release(self.ll_lock)

    def lock_no_tasks_pending(self):
        threadintf.acquire(self.ll_no_tasks_pending_lock, True)

    def unlock_no_tasks_pending(self):
        threadintf.release(self.ll_no_tasks_pending_lock)

    def assert_locked_no_tasks_pending(self):
        just_locked = threadintf.acquire(self.ll_no_tasks_pending_lock, False)
        assert not just_locked

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
    def __init__(self, w_callback, args):
        self.w_callback = w_callback
        self.args = args

    def run(self):
        space = state.space
        space.call_args(self.w_callback, self.args)
        # xxx exceptions?


def add(space, w_callback, __args__):
    state.lock()
    was_empty = len(state.pending) == 0
    state.pending.append(Pending(w_callback, __args__))
    if was_empty:
        state.unlock_no_tasks_pending()
    state.unlock()


def _run_thread():
    state.lock()
    #
    while True:
        if len(state.pending) == 0:
            state.assert_locked_no_tasks_pending()
            state.num_waiting_threads += 1
            if state.num_waiting_threads == state.num_threads:
                state.finished = True
                state.unlock_unfinished()
                state.unlock_no_tasks_pending()
            state.unlock()
            #
            state.lock_no_tasks_pending()
            state.unlock_no_tasks_pending()
            #
            state.lock()
            if state.finished:
                break
            state.num_waiting_threads -= 1
        else:
            pending = state.pending.pop(0)
            if len(state.pending) == 0:
                state.lock_no_tasks_pending()
            state.unlock()
            pending.run()
            state.lock()
    #
    state.unlock()


def run(space):
    if state.running:
        raise OperationError(
            state.w_error,
            space.wrap("recursive invocation of transaction.run()"))
    state.num_waiting_threads = 0
    state.finished = False
    state.running = True
    #
    for i in range(state.num_threads):
        threadintf.start_new_thread(_run_thread, ())
    #
    state.lock_unfinished()
    assert state.num_waiting_threads == state.num_threads
    assert len(state.pending) == 0
    state.lock_no_tasks_pending()
    state.running = False
