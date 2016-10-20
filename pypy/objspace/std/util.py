from rpython.rlib.rstring import InvalidBaseError

from pypy.interpreter.error import OperationError, oefmt

IDTAG_SHIFT   = 4

IDTAG_INT     = 1
IDTAG_LONG    = 3
IDTAG_FLOAT   = 5
IDTAG_COMPLEX = 7
IDTAG_METHOD  = 9
IDTAG_SPECIAL = 11    # -1 - (-maxunicode-1): unichar
                      # 0 - 255: char
                      # 256: empty string
                      # 257: empty unicode
                      # 258: empty tuple
                      # 259: empty frozenset

CMP_OPS = dict(lt='<', le='<=', eq='==', ne='!=', gt='>', ge='>=')
BINARY_BITWISE_OPS = {'and': '&', 'lshift': '<<', 'or': '|', 'rshift': '>>',
                      'xor': '^'}
BINARY_OPS = dict(add='+', div='/', floordiv='//', mod='%', mul='*', sub='-',
                  truediv='/', **BINARY_BITWISE_OPS)
COMMUTATIVE_OPS = ('add', 'mul', 'and', 'or', 'xor')


def negate(f):
    """Create a function which calls `f` and negates its result.  When the
    result is ``space.w_NotImplemented``, ``space.w_NotImplemented`` is
    returned. This is useful for complementing e.g. the __ne__ descriptor if
    your type already defines a __eq__ descriptor.
    """
    def _negator(self, space, w_other):
        # no need to use space.is_ / space.not_
        tmp = f(self, space, w_other)
        if tmp is space.w_NotImplemented:
            return space.w_NotImplemented
        return space.newbool(tmp is space.w_False)
    _negator.func_name = 'negate-%s' % f.func_name
    return _negator

def get_positive_index(where, length):
    if where < 0:
        where += length
        if where < 0:
            where = 0
    elif where > length:
        where = length
    assert where >= 0
    return where


def wrap_parsestringerror(space, e, w_source):
    if isinstance(e, InvalidBaseError):
        raise OperationError(space.w_ValueError, space.newtext(e.msg))
    else:
        raise oefmt(space.w_ValueError, '%s: %s',
                    e.msg, space.str_w(space.repr(w_source)))
