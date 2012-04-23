from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.rlib import rstm


class State(object):
    """The shared, global state.  Warning, writes to it cause conflicts.
    XXX fix me to somehow avoid conflicts at the beginning due to setvalue()
    """

    def __init__(self, space):
        self.space = space
        self.num_threads = rstm.NUM_THREADS_DEFAULT
        self.running = False
        self.w_error = None
        self.threadobjs = {}      # empty during translation
        self.threadnums = {}      # empty during translation
        self.epolls = {}
        self.pending_before_run = []

    def startup(self, w_module):
        if w_module is not None:     # for tests
            space = self.space
            self.w_error = space.getattr(w_module,
                                         space.wrap('TransactionError'))
        main_ec = self.space.getexecutioncontext()    # create it if needed
        main_ec._transaction_pending = self.pending_before_run

    def add_thread(self, id, ec):
        # register a new transaction thread
        assert id not in self.threadobjs
        ec._transaction_pending = []
        self.threadobjs[id] = ec
        self.threadnums[id] = len(self.threadnums)

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
        if id == rstm.MAIN_THREAD_ID:
            assert len(self.threadobjs) == 0
            assert len(self.threadnums) == 0
            self.threadobjs[id] = value
            self.threadnums[id] = 0
        else:
            self.add_thread(id, value)

    def getmainthreadvalue(self):
        return self.threadobjs.get(MAIN_THREAD_ID, None)

    def getallvalues(self):
        return self.threadobjs

    def clear_all_values_apart_from_main(self):
        for id in self.threadobjs.keys():
            if id != MAIN_THREAD_ID:
                del self.threadobjs[id]
        for id in self.threadnums.keys():
            if id != MAIN_THREAD_ID:
                del self.threadnums[id]
        self.epolls.clear()

    def get_thread_number(self):
        id = rstm.thread_id()
        return self.threadnums[id]

    def get_total_number_of_threads(self):
        return 1 + self.num_threads

    def set_num_threads(self, num):
        if self.running:
            space = self.space
            raise OperationError(self.w_error,
                                 space.wrap("cannot change the number of "
                                            "threads when transaction.run() "
                                            "is active"))
        self.num_threads = num


def getstate(space):
    return space.fromcache(State)


@unwrap_spec(num=int)
def set_num_threads(space, num):
    if num < 1:
        num = 1
    getstate(space).set_num_threads(num)


class SpaceTransaction(rstm.Transaction):

    def __init__(self, space, w_callback, args):
        self.space = space
        self.state = getstate(space)
        self.w_callback = w_callback
        self.args = args

    def register(self):
        """Register this SpaceTransaction instance in the pending list
        belonging to the current thread.  If called from the main
        thread, it is the global list.  If called from a transaction,
        it is a thread-local list that will be merged with the global
        list when the transaction is done.
        NOTE: never register() the same instance multiple times.
        """
        ec = self.state.getvalue()
        ec._transaction_pending.append(self)

    def run(self):
        if self.retry_counter > 0:
            self.register() # retrying: will be done later, try others first
            return
        #
        ec = self.space.getexecutioncontext()    # create it if needed
        assert len(ec._transaction_pending) == 0
        #
        self.space.call_args(self.w_callback, self.args)
        #
        result = ec._transaction_pending
        ec._transaction_pending = []
        return result


class InitialTransaction(rstm.Transaction):

    def __init__(self, state):
        self.state = state

    def run(self):
        # initially: return the list of already-added transactions as
        # the list of transactions to run next, and clear it
        result = self.state.pending_before_run[:]
        del self.state.pending_before_run[:]
        return result


def add(space, w_callback, __args__):
    transaction = SpaceTransaction(space, w_callback, __args__)
    transaction.register()


def run(space):
    state = getstate(space)
    if state.running:
        raise OperationError(
            state.w_error,
            space.wrap("recursive invocation of transaction.run()"))
    state.running = True
    try:
        rstm.run_all_transactions(InitialTransaction(state),
                                  num_threads = state.num_threads)
    finally:
        state.running = False
        assert len(state.pending_before_run) == 0
