from pypy.rpython.llinterp import LLFrame


class ForbiddenInstructionInSTMMode(Exception):
    pass


def eval_stm_graph(llinterp, graph, values):
    llinterp.frame_class = LLSTMFrame
    try:
        return llinterp.eval_graph(graph, values)
    finally:
        llinterp.frame_class = LLFrame


class LLSTMFrame(LLFrame):

    ALLOW_OPERATIONS = set([
        'int_*',
        ])

    def getoperationhandler(self, opname):
        ophandler = getattr(self, 'opstm_' + opname, None)
        if ophandler is None:
            self._validate_stmoperation_handler(opname)
            ophandler = LLFrame.getoperationhandler(self, opname)
            setattr(self, 'opstm_' + opname, ophandler)
        return ophandler

    def _validate_stmoperation_handler(self, opname):
        OK = self.ALLOW_OPERATIONS
        if opname in OK:
            return
        for i in range(len(opname)-1, -1, -1):
            if (opname[:i] + '*') in OK:
                return
        raise ForbiddenInstructionInSTMMode(opname, self.graph)
