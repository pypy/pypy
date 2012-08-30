
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef

class W_FlatIterator(Wrappable):
    pass

W_FlatIterator.typedef = TypeDef(
    'flatiter',
)
