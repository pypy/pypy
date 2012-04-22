from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper, cast_instance_to_base_ptr
from pypy.rpython.annlowlevel import base_ptr_lltype, cast_base_ptr_to_instance
from pypy.rlib.objectmodel import keepalive_until_here, we_are_translated
from pypy.rlib.debug import ll_assert
from pypy.translator.stm.stmgcintf import StmOperations



NUM_THREADS_DEFAULT = 4     # XXX for now


class TransactionError(Exception):
    pass

class Transaction(object):
    _next_transaction = None
    retry_counter = 0

    def run(self):
        raise NotImplementedError


def stm_operations():
    if we_are_translated():
        return StmOperations
    else:
        from pypy.rlib.test.test_rstm import fake_stm_operations
        return fake_stm_operations


def in_transaction():
    return bool(stm_operations().in_transaction())


def run_all_transactions(initial_transaction,
                         num_threads = NUM_THREADS_DEFAULT):
    if in_transaction():
        raise TransactionError("nested call to rstm.run_all_transactions()")
    #
    _transactionalstate.initialize()
    #
    # Tell the GC we are entering transactional mode.  This makes
    # sure that 'initial_transaction' is flagged as GLOBAL.
    # (Actually it flags all surviving objects as GLOBAL.)
    # No more GC operation afterwards!
    llop.stm_enter_transactional_mode(lltype.Void)
    #
    # Keep alive 'initial_transaction'.  In truth we would like it to
    # survive a little bit longer, for the beginning of the C code in
    # run_all_transactions().  This should be equivalent because there
    # is no possibility of having a GC collection inbetween.
    keepalive_until_here(initial_transaction)
    #
    # The following line causes the _run_transaction() function to be
    # generated in the C source with a specific signature, where it
    # can be called by the C code.
    llhelper(StmOperations.RUN_TRANSACTION, _run_transaction)
    #
    # Tell the C code to run all transactions.
    ptr = _cast_transaction_to_voidp(initial_transaction)
    stm_operations().run_all_transactions(ptr, num_threads)
    #
    # Tell the GC we are leaving transactional mode.
    llop.stm_leave_transactional_mode(lltype.Void)
    #
    # Hack
    if not we_are_translated():
        stm_operations().leaving()
    #
    # If an exception was raised, re-raise it here.
    _transactionalstate.close_exceptions()


def _cast_transaction_to_voidp(transaction):
    if we_are_translated():
        ptr = cast_instance_to_base_ptr(transaction)
        return rffi.cast(rffi.VOIDP, ptr)
    else:
        return stm_operations().cast_transaction_to_voidp(transaction)

def _cast_voidp_to_transaction(transactionptr):
    if we_are_translated():
        ptr = rffi.cast(base_ptr_lltype(), transactionptr)
        return cast_base_ptr_to_instance(Transaction, ptr)
    else:
        return stm_operations().cast_voidp_to_transaction(transactionptr)


class _TransactionalState(object):
    """This is the class of a global singleton, seen by every transaction.
    Used for cross-transaction synchronization.  Of course writing to it
    will likely cause conflicts.  Reserved for now for storing the
    exception that must be re-raised by run_all_transactions().
    """
    # The logic ensures that once a transaction calls must_reraise_exception()
    # and commits, all uncommitted transactions will abort (because they have
    # read '_reraise_exception' when they started) and then, when they retry,
    # do nothing.  This makes the transaction committing an exception the last
    # one to commit, and it cleanly shuts down all other pending transactions.

    def initialize(self):
        self._reraise_exception = None

    def has_exception(self):
        return self._reraise_exception is not None

    def must_reraise_exception(self, got_exception):
        self._got_exception = got_exception
        self._reraise_exception = self.reraise_exception_callback
        if not we_are_translated():
            import sys; self._got_tb = sys.exc_info()[2]

    def close_exceptions(self):
        if self._reraise_exception is not None:
            self._reraise_exception()

    @staticmethod
    def reraise_exception_callback():
        self = _transactionalstate
        exc = self._got_exception
        self._got_exception = None
        if not we_are_translated() and hasattr(self, '_got_tb'):
            raise exc.__class__, exc, self._got_tb
        raise exc

_transactionalstate = _TransactionalState()


def _run_transaction(transactionptr, retry_counter):
    #
    # Tell the GC we are starting a transaction
    llop.stm_start_transaction(lltype.Void)
    #
    # Now we can use the GC
    next = None
    try:
        if _transactionalstate.has_exception():
            # a previously committed transaction raised: don't do anything
            # more in this transaction
            pass
        else:
            # run!
            next = _run_really(transactionptr, retry_counter)
        #
    except Exception, e:
        _transactionalstate.must_reraise_exception(e)
    #
    # Stop using the GC.  This will make 'next' and all transactions linked
    # from there GLOBAL objects.
    llop.stm_stop_transaction(lltype.Void)
    #
    # Mark 'next' as kept-alive-until-here.  In truth we would like to
    # keep it alive after the return, for the C code.  This should be
    # equivalent because there is no possibility of having a GC collection
    # inbetween.
    keepalive_until_here(next)
    return _cast_transaction_to_voidp(next)


def _run_really(transactionptr, retry_counter):
    # Call the RPython method run() on the Transaction instance.
    # This logic is in a sub-function because we want to catch
    # the MemoryErrors that could occur.
    transaction = _cast_voidp_to_transaction(transactionptr)
    ll_assert(transaction._next_transaction is None,
              "_next_transaction should be cleared by C code")
    transaction.retry_counter = retry_counter
    new_transactions = transaction.run()
    return _link_new_transactions(new_transactions)
_run_really._dont_inline_ = True

def _link_new_transactions(new_transactions):
    # in order to schedule the new transactions, we have to return a
    # raw pointer to the first one, with their field '_next_transaction'
    # making a linked list.  The C code reads directly from this
    # field '_next_transaction'.
    if new_transactions is None:
        return None
    n = len(new_transactions) - 1
    next = None
    while n >= 0:
        new_transactions[n]._next_transaction = next
        next = new_transactions[n]
        n -= 1
    return next
