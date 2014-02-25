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
