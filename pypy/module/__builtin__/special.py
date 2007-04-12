from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.rlib import rarithmetic

def _formatd(space, alt, prec, kind, x):
    try:
        return space.wrap(rarithmetic.formatd_overflow(alt, prec, kind, x))
    except OverflowError:
        raise OperationError(space.w_OverflowError, space.wrap(
            "formatted float is too long (precision too large?)"))
_formatd.unwrap_spec = [gateway.ObjSpace, int, int, str, float]


