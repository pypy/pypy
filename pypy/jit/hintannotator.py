from pypy.annotation.annrpython import RPythonAnnotator, _registeroperations
from pypy.jit import hintmodel
from pypy.jit.hintbookkeeper import HintBookkeeper


class HintAnnotator(RPythonAnnotator):

    def __init__(self, translator, policy=None):
        RPythonAnnotator.__init__(self, translator, policy=policy)
        self.bookkeeper = HintBookkeeper(self) # XXX

    def consider_op_malloc(self, hs_TYPE):
        TYPE = hs_TYPE.const
        vstructdef = self.bookkeeper.getvirtualcontainerdef(TYPE)
        return hintmodel.SomeLLAbstractContainer(vstructdef)

    def consider_op_malloc_varsize(self, hs_TYPE, hs_length):
        TYPE = hs_TYPE.const
        vcontainerdef = self.bookkeeper.getvirtualcontainerdef(TYPE)
        return hintmodel.SomeLLAbstractContainer(vcontainerdef)


_registeroperations(HintAnnotator.__dict__, hintmodel)
