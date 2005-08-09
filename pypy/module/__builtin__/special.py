from pypy.interpreter import gateway
from pypy.rpython import rarithmetic

def _isfake(space, w_obj): 
    return space.wrap(bool(w_obj.typedef.fakedcpytype))
    #return space.wrap(bool(getattr(w_obj.typedef, 'fakedcpytype', None)))


def _formatd(space, fmt, x):
    return space.wrap(rarithmetic.formatd(fmt, x))
_formatd.unwrap_spec = [gateway.ObjSpace, str, float]
