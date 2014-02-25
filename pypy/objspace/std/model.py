from pypy.interpreter.baseobjspace import W_Root


IDTAG_INT     = 1
IDTAG_LONG    = 3
IDTAG_FLOAT   = 5
IDTAG_COMPLEX = 7


CMP_OPS = dict(lt='<', le='<=', eq='==', ne='!=', gt='>', ge='>=')
BINARY_BITWISE_OPS = {'and': '&', 'lshift': '<<', 'or': '|', 'rshift': '>>',
                      'xor': '^'}
BINARY_OPS = dict(add='+', div='/', floordiv='//', mod='%', mul='*', sub='-',
                  truediv='/', **BINARY_BITWISE_OPS)
COMMUTATIVE_OPS = ('add', 'mul', 'and', 'or', 'xor')


# ____________________________________________________________

W_ANY = W_Root

class W_Object(W_Root):
    "Parent base class for wrapped objects provided by the StdObjSpace."
    # Note that not all wrapped objects in the interpreter inherit from
    # W_Object.  (They inherit from W_Root.)
    __slots__ = ()

    def __repr__(self):
        name = getattr(self, 'name', '')
        if not isinstance(name, str):
            name = ''
        s = '%s(%s)' % (self.__class__.__name__, name)
        w_cls = getattr(self, 'w__class__', None)
        if w_cls is not None and w_cls is not self:
            s += ' instance of %s' % self.w__class__
        return '<%s>' % s
