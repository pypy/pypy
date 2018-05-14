from pypy.interpreter.baseobjspace import W_Root


class Ellipsis(W_Root):
    def descr__repr__(self, space):
        return space.newtext('Ellipsis')


class NotImplemented(W_Root):
    def descr__repr__(self, space):
        return space.newtext('NotImplemented')
