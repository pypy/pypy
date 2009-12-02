from pypy.rlib.rcoroutine import make_coroutine_classes
from pypy.interpreter.baseobjspace import Wrappable

d = make_coroutine_classes(Wrappable)

Coroutine = d['Coroutine']
BaseCoState = d['BaseCoState']
AbstractThunk = d['AbstractThunk']
syncstate = d['syncstate']
