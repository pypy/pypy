from pypy.interpreter.error import oefmt
from pypy.objspace.std.tupleobject import W_AbstractTupleObject
from pypy.objspace.std.util import negate
from rpython.rlib.objectmodel import compute_hash, specialize
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.unroll import unrolling_iterable
from rpython.tool.sourcetools import func_with_new_name
from rpython.rlib.longlong2float import float2longlong


class NotSpecialised(Exception):
    pass


def make_specialised_class(typetuple):
    assert type(typetuple) == tuple
    wraps = []
    for typ in typetuple:
        if typ == int:
            wraps.append(lambda space, x: space.newint(x))
        elif typ == float:
            wraps.append(lambda space, x: space.newfloat(x))
        elif typ == object:
            wraps.append(lambda space, w_x: w_x)
        else:
            assert 0

    typelen = len(typetuple)
    iter_n = unrolling_iterable(range(typelen))

    class cls(W_AbstractTupleObject):
        _immutable_fields_ = ['value%s' % i for i in iter_n]

        def __init__(self, space, *values_w):
            self.space = space
            assert len(values_w) == typelen
            for i in iter_n:
                w_obj = values_w[i]
                val_type = typetuple[i]
                if val_type == int:
                    unwrapped = w_obj.int_w(space)
                elif val_type == float:
                    unwrapped = w_obj.float_w(space)
                elif val_type == str:
                    unwrapped = w_obj.str_w(space)
                elif val_type == object:
                    unwrapped = w_obj
                else:
                    raise AssertionError
                setattr(self, 'value%s' % i, unwrapped)

        def length(self):
            return typelen

        def tolist(self):
            list_w = [None] * typelen
            for i in iter_n:
                value = getattr(self, 'value%s' % i)
                value = wraps[i](self.space, value)
                list_w[i] = value
            return list_w

        # same source code, but builds and returns a resizable list
        getitems_copy = func_with_new_name(tolist, 'getitems_copy')

        def descr_hash(self, space):
            mult = 1000003
            x = 0x345678
            z = typelen
            for i in iter_n:
                value = getattr(self, 'value%s' % i)
                if typetuple[i] == object:
                    y = space.int_w(space.hash(value))
                elif typetuple[i] == int:
                    # mimic cpythons behavior of a hash value of -2 for -1
                    y = value
                    if y == -1:
                        y = -2
                elif typetuple[i] == float:
                    # get the correct hash for float which is an
                    # integer & other less frequent cases
                    from pypy.objspace.std.floatobject import _hash_float
                    y = _hash_float(space, value)
                else:
                    y = compute_hash(value)
                x = (x ^ y) * mult
                z -= 1
                mult += 82520 + z + z
            x += 97531
            return space.newint(intmask(x))

        def descr_eq(self, space, w_other):
            if not isinstance(w_other, W_AbstractTupleObject):
                return space.w_NotImplemented
            if not isinstance(w_other, cls):
                if typelen != w_other.length():
                    return space.w_False
                for i in iter_n:
                    myval = getattr(self, 'value%s' % i)
                    otherval = w_other.getitem(space, i)
                    myval = wraps[i](self.space, myval)
                    if not space.eq_w(myval, otherval):
                        return space.w_False
                return space.w_True

            for i in iter_n:
                myval = getattr(self, 'value%s' % i)
                otherval = getattr(w_other, 'value%s' % i)
                if typetuple[i] == object:
                    if not self.space.eq_w(myval, otherval):
                        return space.w_False
                else:
                    if myval != otherval:
                        if typetuple[i] == float:
                            # issue with NaNs, which should be equal here
                            if (float2longlong(myval) ==
                                float2longlong(otherval)):
                                continue
                        return space.w_False
            return space.w_True

        descr_ne = negate(descr_eq)

        def getitem(self, space, index):
            if index < 0:
                index += typelen
            for i in iter_n:
                if index == i:
                    value = getattr(self, 'value%s' % i)
                    value = wraps[i](self.space, value)
                    return value
            raise oefmt(space.w_IndexError, "tuple index out of range")

    cls.__name__ = ('W_SpecialisedTupleObject_' +
                    ''.join([t.__name__[0] for t in typetuple]))
    _specialisations.append(cls)
    return cls

# ---------- current specialized versions ----------

_specialisations = []
Cls_ii = make_specialised_class((int, int))
Cls_oo = make_specialised_class((object, object))
Cls_ff = make_specialised_class((float, float))

def makespecialisedtuple(space, list_w):
    from pypy.objspace.std.intobject import W_IntObject
    from pypy.objspace.std.floatobject import W_FloatObject
    if len(list_w) == 2:
        w_arg1, w_arg2 = list_w
        if type(w_arg1) is W_IntObject:
            if type(w_arg2) is W_IntObject:
                return Cls_ii(space, w_arg1, w_arg2)
        elif type(w_arg1) is W_FloatObject:
            if type(w_arg2) is W_FloatObject:
                return Cls_ff(space, w_arg1, w_arg2)
        return Cls_oo(space, w_arg1, w_arg2)
    else:
        raise NotSpecialised

# --------------------------------------------------
# Special code based on list strategies to implement zip(),
# here with two list arguments only.  This builds a zipped
# list that differs from what the app-level code would build:
# if the source lists contain sometimes ints/floats and
# sometimes not, here we will use uniformly 'Cls_oo' instead
# of using 'Cls_ii' or 'Cls_ff' for the elements that match.
# This is a trade-off, but it looks like a good idea to keep
# the list uniform for the JIT---not to mention, it is much
# faster to move the decision out of the loop.

@specialize.arg(1)
def _build_zipped_spec(space, Cls, lst1, lst2, wrap1, wrap2):
    length = min(len(lst1), len(lst2))
    return [Cls(space, wrap1(lst1[i]),
                       wrap2(lst2[i])) for i in range(length)]

def _build_zipped_spec_oo(space, w_list1, w_list2):
    strat1 = w_list1.strategy
    strat2 = w_list2.strategy
    length = min(strat1.length(w_list1), strat2.length(w_list2))
    return [Cls_oo(space, strat1.getitem(w_list1, i),
                          strat2.getitem(w_list2, i)) for i in range(length)]

def _build_zipped_unspec(space, w_list1, w_list2):
    strat1 = w_list1.strategy
    strat2 = w_list2.strategy
    length = min(strat1.length(w_list1), strat2.length(w_list2))
    return [space.newtuple([strat1.getitem(w_list1, i),
                            strat2.getitem(w_list2, i)]) for i in range(length)]

def specialized_zip_2_lists(space, w_list1, w_list2):
    from pypy.objspace.std.listobject import W_ListObject
    if type(w_list1) is not W_ListObject or type(w_list2) is not W_ListObject:
        raise oefmt(space.w_TypeError, "expected two exact lists")

    if space.config.objspace.std.withspecialisedtuple:
        intlist1 = w_list1.getitems_int()
        if intlist1 is not None:
            intlist2 = w_list2.getitems_int()
            if intlist2 is not None:
                lst_w = _build_zipped_spec(
                        space, Cls_ii, intlist1, intlist2,
                        space.newint, space.newint)
                return space.newlist(lst_w)
        else:
            floatlist1 = w_list1.getitems_float()
            if floatlist1 is not None:
                floatlist2 = w_list2.getitems_float()
                if floatlist2 is not None:
                    lst_w = _build_zipped_spec(
                        space, Cls_ff, floatlist1, floatlist2, space.newfloat,
                        space.newfloat)
                    return space.newlist(lst_w)

        lst_w = _build_zipped_spec_oo(space, w_list1, w_list2)
        return space.newlist(lst_w)

    else:
        lst_w = _build_zipped_unspec(space, w_list1, w_list2)
        return space.newlist(lst_w)
