from pypy.annotation.annrpython import RPythonAnnotator, _registeroperations
from pypy.jit import hintmodel
from pypy.jit.hintbookkeeper import HintBookkeeper

class HintAnnotator(RPythonAnnotator):

    def __init__(self):
        RPythonAnnotator.__init__(self)
        self.bookkeeper = HintBookkeeper() # XXX


_registeroperations(HintAnnotator.__dict__, hintmodel)
