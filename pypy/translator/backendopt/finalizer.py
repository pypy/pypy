
from pypy.translator.backendopt import graphanalyze
from pypy.rpython.lltypesystem import lltype

class FinalizerAnalyzer(graphanalyze.BoolGraphAnalyzer):
    """ Analyzer that determines whether a finalizer is lightweight enough
    so it can be called without all the complicated logic in the garbage
    collector. The set of operations here is restrictive for a good reason
    - it's better to be safe. Specifically disallowed operations:

    * anything that escapes self
    * anything that can allocate
    """
    ok_operations = ['ptr_nonzero', 'free', 'same_as',
                     'direct_ptradd', 'force_cast', 'track_allocation']
    
    def analyze_simple_operation(self, op, graphinfo):
        if op.opname in self.ok_operations:
            return self.bottom_result()
        if (op.opname.startswith('int_') or op.opname.startswith('float_')
            or op.opname.startswith('cast_')):
            return self.bottom_result()
        if op.opname == 'setfield' or op.opname == 'bare_setfield':
            TP = op.args[2].concretetype
            if not isinstance(TP, lltype.Ptr) or TP.TO._gckind == 'raw':
                # primitive type
                return self.bottom_result()
        if op.opname == 'getfield':
            TP = op.result.concretetype
            if not isinstance(TP, lltype.Ptr) or TP.TO._gckind == 'raw':
                # primitive type
                return self.bottom_result()            
        return self.top_result()
