from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.typesystem import TypeSystem
from pypy.jit import hintmodel

class HintTypeSystem(TypeSystem):
    name = "hinttypesystem"

    def perform_normalizations(self, rtyper):
        pass   # for now

HintTypeSystem.instance = HintTypeSystem()

# ___________________________________________________________

class HintTyper(RPythonTyper):
    
    def __init__(self, hannotator):
    	RPythonTyper.__init__(self, hannotator, 
                              type_system=HintTypeSystem.instance)
        self._fixed_reprs = hintrconstant.PRECOMPUTED_FIXED_REPRS.copy()

# register operations from model
HintTyper._registeroperations(hintmodel)

# import reprs
from pypy.jit import hintrconstant
