
from pypy.interpreter.baseobjspace import Wrappable

class Ellipsis(Wrappable):
    def __init__(self, space):
        self.space = space 
    def descr__repr__(self):
        return self.space.wrap('Ellipsis')

class NotImplemented(Wrappable): 
    def __init__(self, space):
        self.space = space 
    def descr__repr__(self):
        return self.space.wrap('NotImplemented')

