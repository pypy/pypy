from pypy.objspace.std.objspace import W_Object, OperationError
from pypy.objspace.std.objspace import registerimplementation, register_all
from pypy.objspace.std.model import WITHSET
from pypy.objspace.std.stdtypedef import StdObjSpaceMultiMethod
from pypy.rpython.objectmodel import r_dict
from pypy.interpreter import gateway

def _set_init(w_self, space, wrappeditems):
    W_Object.__init__(w_self, space)
    w_self.data = data = r_dict(space.eq_w, space.hash_w)
    if space.is_true(space.isinstance(wrappeditems, space.w_frozenset)):
        data.update(wrappeditems.data)
    elif space.is_true(space.isinstance(wrappeditems, space.w_set)):
        data.update(wrappeditems.data)
    else:
        iterable_w = space.unpackiterable(wrappeditems)
        for w_item in iterable_w:
            w_self.data[w_item] = space.w_True


class W_SetObject(W_Object):
    from pypy.objspace.std.settype import set_typedef as typedef

    def __init__(w_self, space, wrappeditems):
        _set_init(w_self, space, wrappeditems)

    def __repr__(w_self):
        """representation for debugging purposes"""
        reprlist = [repr(w_item) for w_item in w_self.data.keys()]
        return "<%s(%s)>" % (w_self.__class__.__name__, ', '.join(reprlist))

class W_FrozensetObject(W_Object):
    from pypy.objspace.std.settype import frozenset_typedef as typedef

    def __init__(w_self, space, wrappeditems):
        _set_init(w_self, space, wrappeditems)

registerimplementation(W_SetObject)
registerimplementation(W_FrozensetObject)

app = gateway.applevel("""
    def and__Set_Set(s, o):
        return s.intersection(o)

    def ne__Set_Set(s, o):
        return not s == o

    def ge__Set_Set(s, o):
        return s.issuperset(o)

    def gt__Set_Set(s, o):
        return s != o and s.issuperset(o)

    def le__Set_Set(s, o):
        return s.issubset(o)

    def lt__Set_Set(s, o):
        return s != o and s.issubset(o)

    def cmp__Set_Set(s, o):
        raise TypeError('cannot compare sets using cmp()')

    def or__Set_Set(s, o):
        return s.union(o)

    def xor__Set_Set(s, o):
        return s.symmetric_difference(o)

    def repr__Set(s):
        return 'set(%s)' % [x for x in s]

    def repr__Frozenset(s):
        return 'frozenset(%s)' % [x for x in s]

    def sub__Set_Set(s, o):
        return s.difference(o)

    def isub__Set_Set(s, o):
        s.difference_update(o)
        return s

    def ior__Set_Set(s, o):
        s.update(o)
        return s

    def iand__Set_Set(s, o):
        s.intersection_update(o)
        return s

    def ixor__Set_Set(s, o):
        s.symmetric_difference_update(o)
        return s

""", filename=__file__)

and__Set_Set = app.interphook("and__Set_Set")
and__Set_Frozenset = and__Set_Set
and__Frozenset_Set = and__Set_Set
and__Frozenset_Frozenset = and__Set_Set

ne__Set_Set = app.interphook("ne__Set_Set")
ne__Set_Frozenset = ne__Set_Set
ne__Frozenset_Set = ne__Set_Set
ne__Frozenset_Frozenset = ne__Set_Set

ge__Set_Set = app.interphook("ge__Set_Set")
ge__Set_Frozenset = ge__Set_Set
ge__Frozenset_Set = ge__Set_Set
ge__Frozenset_Frozenset = ge__Set_Set

le__Set_Set = app.interphook("le__Set_Set")
le__Set_Frozenset = le__Set_Set
le__Frozenset_Set = le__Set_Set
le__Frozenset_Frozenset = le__Set_Set

gt__Set_Set = app.interphook("gt__Set_Set")
gt__Set_Frozenset = gt__Set_Set
gt__Frozenset_Set = gt__Set_Set
gt__Frozenset_Frozenset = gt__Set_Set

lt__Set_Set = app.interphook("lt__Set_Set")
lt__Set_Frozenset = lt__Set_Set
lt__Frozenset_Set = lt__Set_Set
lt__Frozenset_Frozenset = lt__Set_Set

cmp__Set_Set = app.interphook("cmp__Set_Set")
cmp__Set_Frozenset = cmp__Set_Set
cmp__Frozenset_Frozenset = cmp__Set_Set
cmp__Frozenset_Set = cmp__Set_Set

or__Set_Set = app.interphook("or__Set_Set")
or__Set_Frozenset = or__Set_Set
or__Frozenset_Set = or__Set_Set
or__Frozenset_Frozenset = or__Set_Set

xor__Set_Set = app.interphook("xor__Set_Set")
xor__Set_Frozenset = xor__Set_Set
xor__Frozenset_Set = xor__Set_Set
xor__Frozenset_Frozenset = xor__Set_Set

repr__Set = app.interphook('repr__Set')
repr__Frozenset = app.interphook('repr__Frozenset')

sub__Set_Set = app.interphook('sub__Set_Set')
sub__Set_Frozenset = sub__Set_Set
sub__Frozenset_Set = sub__Set_Set
sub__Frozenset_Frozenset = sub__Set_Set

inplace_sub__Set_Set = app.interphook('isub__Set_Set')
inplace_sub__Set_Frozenset = inplace_sub__Set_Set

inplace_or__Set_Set = app.interphook('ior__Set_Set')
inplace_or__Set_Frozenset = inplace_or__Set_Set

inplace_and__Set_Set = app.interphook('iand__Set_Set')
inplace_and__Set_Frozenset = inplace_and__Set_Set

inplace_xor__Set_Set = app.interphook('ixor__Set_Set')
inplace_xor__Set_Frozenset = inplace_xor__Set_Set

register_all(vars())
