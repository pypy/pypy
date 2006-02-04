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
        self._canonical_reprs = {}

    def fixedrepr(self, lowleveltype):
        key = True, lowleveltype
        try:
            repr =  self._canonical_reprs[key]
        except KeyError:
            hs = hintmodel.SomeLLAbstractConstant(lowleveltype, {})
            hs.eager_concrete = True
            repr = self._canonical_reprs[key] = self.getrepr(hs)
        return repr

# register operations from model
HintTyper._registeroperations(hintmodel)

# import reprs
from pypy.jit import hintrconstant
