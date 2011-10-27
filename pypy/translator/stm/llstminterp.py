from pypy.rpython.llinterp import LLFrame
from pypy.translator.stm import rstm


class ForbiddenInstructionInSTMMode(Exception):
    pass


def eval_stm_graph(llinterp, graph, values, stm_mode="not_in_transaction"):
    llinterp.frame_class = LLSTMFrame
    try:
        llinterp.stm_mode = stm_mode
        return llinterp.eval_graph(graph, values)
    finally:
        llinterp.frame_class = LLFrame


class LLSTMFrame(LLFrame):

    ALWAYS_ALLOW_OPERATIONS = set([
        'int_*',
        ])
    ALLOW_WHEN_NOT_IN_TRANSACTION = set([
        'stm_begin_transaction',
        ])
    ALLOW_WHEN_REGULAR_TRANSACTION = set([
        'stm_getfield', 'stm_setfield',
        'stm_commit_transaction',
        ])
    ALLOW_WHEN_INEVITABLE_TRANSACTION = ALLOW_WHEN_REGULAR_TRANSACTION.union(
        set([
        ]))

    def getoperationhandler(self, opname):
        stm_mode = self.llinterpreter.stm_mode
        attrname = '_opstm_%s__%s' % (stm_mode, opname)
        ophandler = getattr(self, attrname, None)
        if ophandler is None:
            self._validate_stmoperation_handler(stm_mode, opname)
            ophandler = LLFrame.getoperationhandler(self, opname)
            setattr(self, attrname, ophandler)
        return ophandler

    def _op_in_set(self, opname, set):
        if opname in set:
            return True
        for i in range(len(opname)-1, -1, -1):
            if (opname[:i] + '*') in set:
                return True
        return False

    def _validate_stmoperation_handler(self, stm_mode, opname):
        if self._op_in_set(opname, self.ALWAYS_ALLOW_OPERATIONS):
            return
        allow = getattr(self, 'ALLOW_WHEN_' + stm_mode.upper())
        if self._op_in_set(opname, allow):
            return
        raise ForbiddenInstructionInSTMMode(stm_mode, opname, self.graph)

    # ---------- stm-only operations ----------
    # Note that for these tests we assume no real multithreading,
    # so that we just emulate the operations the easy way

    def op_stm_getfield(self, struct, fieldname):
        return self.op_getfield(struct, fieldname)

    def op_stm_setfield(self, struct, fieldname, value):
        self.op_setfield(struct, fieldname, value)

    def op_stm_begin_transaction(self):
        assert self.llinterpreter.stm_mode == "not_in_transaction"
        self.llinterpreter.stm_mode = "regular_transaction"

    def op_stm_commit_transaction(self):
        assert self.llinterpreter.stm_mode != "not_in_transaction"
        self.llinterpreter.stm_mode = "not_in_transaction"
