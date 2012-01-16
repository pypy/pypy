from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLFrame, LLException
##from pypy.translator.stm import rstm
from pypy.translator.stm.transform import op_in_set, ALWAYS_ALLOW_OPERATIONS


class ForbiddenInstructionInSTMMode(Exception):
    pass

class ReturnWithTransactionActive(Exception):
    pass


def eval_stm_graph(llinterp, graph, values, stm_mode="not_in_transaction",
                   final_stm_mode=Ellipsis, automatic_promotion=False):
    llinterp.frame_class = LLSTMFrame
    try:
        llinterp.stm_mode = stm_mode
        llinterp.stm_automatic_promotion = automatic_promotion
        llinterp.last_transaction_started_in_frame = None
        res = llinterp.eval_graph(graph, values)
        if final_stm_mode is Ellipsis:
            final_stm_mode = stm_mode
        assert llinterp.stm_mode == final_stm_mode, (
            "llinterp.stm_mode is %r after eval_graph, but should be %r" % (
            llinterp.stm_mode, final_stm_mode))
        return res
    finally:
        llinterp.frame_class = LLFrame


class LLSTMFrame(LLFrame):

    def eval(self):
        try:
            res = LLFrame.eval(self)
        except LLException, e:
            self.returning_from_frame_now()
            raise e
        self.returning_from_frame_now()
        return res

    def returning_from_frame_now(self):
        if (self.llinterpreter.stm_mode == "regular_transaction" and
                self.llinterpreter.last_transaction_started_in_frame is self):
            if self.llinterpreter.stm_automatic_promotion:
                self.llinterpreter.stm_mode = "inevitable_transaction"
            else:
                raise ReturnWithTransactionActive(self.graph)

    def getoperationhandler(self, opname):
        ophandler = getattr(self, 'opstm_' + opname, None)
        if ophandler is None:
            ophandler = LLFrame.getoperationhandler(self, opname)
            if op_in_set(opname, ALWAYS_ALLOW_OPERATIONS):
                # always allow this, so store it back on 'self'
                setattr(self, 'opstm_' + opname, ophandler)
            else:
                # only allow this if we're not in the "regular_transaction"
                # mode; check every time, so don't store it on self.__class__
                if self.llinterpreter.stm_mode == "regular_transaction":
                    raise ForbiddenInstructionInSTMMode(opname, self.graph)
        return ophandler

    # ---------- operations that are sometimes safe ----------

    def opstm_getfield(self, struct, fieldname):
        STRUCT = lltype.typeOf(struct).TO
        if STRUCT._immutable_field(fieldname):
            # immutable field reads are always allowed
            return LLFrame.op_getfield(self, struct, fieldname)
        elif STRUCT._gckind == 'raw':
            # raw getfields are allowed outside a regular transaction
            self.check_stm_mode(lambda m: m != "regular_transaction")
            return LLFrame.op_getfield(self, struct, fieldname)
        else:
            # mutable 'getfields' are always forbidden for now
            self.check_stm_mode(lambda m: False)
            assert 0

    def opstm_setfield(self, struct, fieldname, newvalue):
        STRUCT = lltype.typeOf(struct).TO
        if STRUCT._immutable_field(fieldname):
            # immutable field writes (i.e. initializing writes) should
            # always be fine, because they should occur into newly malloced
            # structures
            LLFrame.op_setfield(self, struct, fieldname, newvalue)
        elif STRUCT._gckind == 'raw':
            # raw setfields are allowed outside a regular transaction
            self.check_stm_mode(lambda m: m != "regular_transaction")
            LLFrame.op_setfield(self, struct, fieldname, newvalue)
        else:
            # mutable 'setfields' are always forbidden for now
            self.check_stm_mode(lambda m: False)
            assert 0

    def opstm_getarrayitem(self, array, index):
        ARRAY = lltype.typeOf(array).TO
        if ARRAY._immutable_field():
            # immutable item reads are always allowed
            return LLFrame.op_getarrayitem(self, array, index)
        elif ARRAY._gckind == 'raw':
            # raw getfields are allowed outside a regular transaction
            self.check_stm_mode(lambda m: m != "regular_transaction")
            return LLFrame.op_getarrayitem(self, array, index)
        else:
            # mutable 'getarrayitems' are always forbidden for now
            self.check_stm_mode(lambda m: False)
            assert 0

    def opstm_setarrayitem(self, array, index, newvalue):
        ARRAY = lltype.typeOf(struct).TO
        if ARRAY._immutable_field():
            # immutable item writes (i.e. initializing writes) should
            # always be fine, because they should occur into newly malloced
            # arrays
            LLFrame.op_setarrayitem(self, array, index, newvalue)
        elif ARRAY._gckind == 'raw':
            # raw setarrayitems are allowed outside a regular transaction
            self.check_stm_mode(lambda m: m != "regular_transaction")
            LLFrame.op_setarrayitem(self, array, index, newvalue)
        else:
            # mutable 'setarrayitems' are always forbidden for now
            self.check_stm_mode(lambda m: False)
            assert 0

    def opstm_malloc(self, TYPE, flags):
        # non-GC must not occur in a regular transaction,
        # but can occur in inevitable mode or outside a transaction
        if flags['flavor'] != 'gc':
            self.check_stm_mode(lambda m: m != "regular_transaction")
        return LLFrame.op_malloc(self, TYPE, flags)

    def opstm_malloc_varsize(self, TYPE, flags, size):
        if flags['flavor'] != 'gc':
            self.check_stm_mode(lambda m: m != "regular_transaction")
        return LLFrame.op_malloc_varsize(self, TYPE, flags, size)

    # ---------- stm-only operations ----------
    # Note that for these tests we assume no real multithreading,
    # so that we just emulate the operations the easy way

    def check_stm_mode(self, checker):
        stm_mode = self.llinterpreter.stm_mode
        if not checker(stm_mode):
            raise ForbiddenInstructionInSTMMode(stm_mode, self.graph)

    def opstm_stm_getfield(self, struct, fieldname):
        self.check_stm_mode(lambda m: m != "not_in_transaction")
        return LLFrame.op_getfield(self, struct, fieldname)

    def opstm_stm_setfield(self, struct, fieldname, value):
        self.check_stm_mode(lambda m: m != "not_in_transaction")
        LLFrame.op_setfield(self, struct, fieldname, value)

    def opstm_stm_getarrayitem(self, array, index):
        self.check_stm_mode(lambda m: m != "not_in_transaction")
        return LLFrame.op_getarrayitem(self, array, index)

    def opstm_stm_setarrayitem(self, array, index, value):
        self.check_stm_mode(lambda m: m != "not_in_transaction")
        LLFrame.op_setarrayitem(self, array, index, value)

    def opstm_stm_getinteriorfield(self, obj, *offsets):
        self.check_stm_mode(lambda m: m != "not_in_transaction")
        return LLFrame.op_getinteriorfield(self, obj, *offsets)

    def opstm_stm_setinteriorfield(self, obj, *fieldnamesval):
        self.check_stm_mode(lambda m: m != "not_in_transaction")
        LLFrame.op_setinteriorfield(self, obj, *fieldnamesval)

    def opstm_stm_begin_transaction(self):
        self.check_stm_mode(lambda m: m == "not_in_transaction")
        self.llinterpreter.stm_mode = "regular_transaction"
        self.llinterpreter.last_transaction_started_in_frame = self

    def opstm_stm_commit_transaction(self):
        self.check_stm_mode(lambda m: m != "not_in_transaction")
        self.llinterpreter.stm_mode = "not_in_transaction"

    def opstm_stm_transaction_boundary(self):
        self.check_stm_mode(lambda m: m != "not_in_transaction")
        self.llinterpreter.stm_mode = "regular_transaction"
        self.llinterpreter.last_transaction_started_in_frame = self

    def opstm_stm_try_inevitable(self, why):
        self.check_stm_mode(lambda m: m != "not_in_transaction")
        self.llinterpreter.stm_mode = "inevitable_transaction"
        print why
