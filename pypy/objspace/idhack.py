"""Example usage:

    $ python interpreter/py.py -o idhack
    >>> x = 6
    >>> id(x)
    12345678
    >>> become(x, 7)
    >>> x
    7
    >>> id(x)
    12345678

"""

from pypy.objspace import std
from pypy.interpreter import gateway

# ____________________________________________________________

def idhack(w_obj):
    try:
        w_obj = w_obj.__unified_with[-1]
    except AttributeError:
        pass
    return id(w_obj)  # XXX call the inherited space.id(), maybe


class IdHackSpace(std.Space):

    def initialize(self):
        super(IdHackSpace, self).initialize()
        self.setitem(self.builtin.w_dict, self.wrap('become'),
                     self.wrap(app_become))

    def is_(self, w_one, w_two):
        if idhack(w_one) == idhack(w_two):
            return self.w_True
        return self.w_False

    def id(self, w_obj):
        return self.wrap(idhack(w_obj))


Space = IdHackSpace

# ____________________________________________________________

def become(space, w_target, w_source):
    try:
        targetfamily = w_target.__unified_with
    except AttributeError:
        targetfamily = [w_target]
    w_source.__unified_with = targetfamily
    targetfamily.append(w_source)
    for w_obj in targetfamily:
        w_obj.__class__ = w_source.__class__
        w_obj.__dict__  = w_source.__dict__
    return space.w_None
app_become = gateway.interp2app(become)
