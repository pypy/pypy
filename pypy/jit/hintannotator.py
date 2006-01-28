from pypy.annotation.annrpython import RPythonAnnotator, _registeroperations
from pypy.jit import hintmodel
from pypy.jit.hintbookkeeper import HintBookkeeper


class HintAnnotator(RPythonAnnotator):

    def __init__(self):
        RPythonAnnotator.__init__(self)
        self.bookkeeper = HintBookkeeper() # XXX

    def consider_op_malloc(self, hs_TYPE):
        TYPE = hs_TYPE.const
        vstructdef = self.bookkeeper.getvirtualstructdef(TYPE)
        return hintmodel.SomeLLAbstractContainer(vstructdef)
        
        


_registeroperations(HintAnnotator.__dict__, hintmodel)
