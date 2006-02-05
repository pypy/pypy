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
        self._fixed_reprs = {}
        # insert the precomputed fixed reprs
        for key, value in hintrconstant.__dict__.items():
            if isinstance(value, hintrconstant.LLFixedConstantRepr):
                self._fixed_reprs[value.lowleveltype] = value

# register operations from model
HintTyper._registeroperations(hintmodel)

# import reprs
from pypy.jit import hintrconstant
