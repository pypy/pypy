from pypy.objspace.flow.model import Block, Constant, flatten
from pypy.translator.backendopt.support import log, all_operations
import pypy.rpython.raisingops
log = log.raisingop2directcall

def raisingop2direct_call(translator):
    """search for operations that could raise an exception and change that
    operation into a direct_call to a function from the raisingops directory.
    This function also needs to be annotated.
    """
    for op in all_operations(translator):
        s = op.opname
        if not s.startswith('int_') and not s.startswith('uint_') and not s.startswith('float_'):
            continue
        if not s.endswith('_zer') and not s.endswith('_ovf') and not s.endswith('_val'):
            continue
        log(s)
        op.args.insert(0, s)
        op.opname = 'direct_call'
