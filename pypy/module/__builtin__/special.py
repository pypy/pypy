from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.rpython import rarithmetic

def _isfake(space, w_obj): 
    return space.wrap(bool(w_obj.typedef.fakedcpytype))
    #return space.wrap(bool(getattr(w_obj.typedef, 'fakedcpytype', None)))


def _formatd(space, alt, prec, kind, x):
    formatd_max_length = rarithmetic.formatd_max_length
    if ((kind == 'g' and formatd_max_length <= 10+prec) or
        (kind == 'f' and formatd_max_length <= 53+prec)):
        raise OperationError(space.w_OverflowError,
                             space.wrap("formatted float is too long (precision too large?)"))    
    if alt:
        alt = '#'
    else:
        alt = ''

    fmt = "%%%s.%d%s" % (alt, prec, kind)
    
    return space.wrap(rarithmetic.formatd(fmt, x))
_formatd.unwrap_spec = [gateway.ObjSpace, int, int, str, float]


def __pdb():
    import pdb
    pdb.set_trace()
__pdb._annspecialcase_ = 'override:ignore'

def _pdb(space):
    __pdb()
