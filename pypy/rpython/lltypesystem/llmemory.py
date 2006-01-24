# this file contains the definitions and most extremely faked
# implementations of things relating to the description of the layout
# of objects in memeory.

# sizeof, offsetof

from pypy.rpython.objectmodel import Symbolic
from pypy.rpython.lltypesystem import lltype

class AddressOffset(Symbolic):

    def annotation(self):
        from pypy.annotation import model
        return model.SomeOffset()

    def lltype(self):
        return lltype.Signed

    def __add__(self, other):
        return CompositeOffset(self, other)


class ItemOffset(AddressOffset):

    def __init__(self, TYPE, repeat=1):
        self.TYPE = TYPE
        self.repeat = repeat

    def __repr__(self):
        return "<ItemOffset %r %r>" % (self.TYPE, self.repeat)

    def __mul__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return ItemOffset(self.TYPE, self.repeat * other)

    def get(self, ob):
        return ob[self.repeat]

    def set(self, ob, value):
        ob[self.repeat] = value

    
class FieldOffset(AddressOffset):

    def __init__(self, TYPE, fldname):
        self.TYPE = TYPE
        self.fldname = fldname

    def __repr__(self):
        return "<FieldOffset %r %r>" % (self.TYPE, self.fldname)

    def get(self, ob):
        return getattr(ob, self.fldname)

    def set(self, ob, value):
        setattr(ob, self.fldname, value)


class CompositeOffset(AddressOffset):

    def __init__(self, first, second):
        self.first = first
        self.second = second

    def __repr__(self):
        return '< %r + %r >'%(self.first, self.second)

    def get(self, ob):
        return self.second.get(self.first.get(ob))

    def set(self, ob, value):
        return self.second.set(self.first.get(ob), value)


class ArrayItemsOffset(AddressOffset):

    def __init__(self, TYPE):
        self.TYPE = TYPE

    def __repr__(self):
        return '< ArrayItemsOffset >'

    def get(self, ob):
        return ob

    def set(self, ob, value):
        raise Exception("can't assign to an array's items")


def sizeof(TYPE, n=None):
    if n is None:
        assert not TYPE._is_varsize()
        return ItemOffset(TYPE)
    else:
        if isinstance(TYPE, Array):
            return itemoffsetof(TYPE, n)
        elif isinstance(TYPE, Struct):
            return FieldOffset(TYPE, TYPE._arrayfld) + \
                   itemoffsetof(TYPE._flds[TYPE._arrayfld], n)
        else:
            raise Exception("don't know how to take the size of a %r"%TYPE)
                   
def offsetof(TYPE, fldname):
    assert fldname in TYPE._flds
    return FieldOffset(TYPE, fldname)

def itemoffsetof(TYPE, n=0):
    return ArrayItemsOffset(TYPE) + ItemOffset(TYPE.OF) * n
# -------------------------------------------------------------

class fakeaddress(object):
    def __init__(self, ob, offset=None):
        self.ob = ob
        self.offset = offset

    def __add__(self, other):
        if isinstance(other, AddressOffset):
            if self.offset is None:
                offset = other
            else:
                offset = self.offset + other
            return fakeaddress(self.ob, offset)
        return NotImplemented

    def get(self):
        if self.offset is None:
            return self.ob
        else:
            return self.offset.get(self.ob)

    def set(self, value):
        if self.offset is None:
            raise Exception("can't assign to whole object")
        else:
            self.offset.set(self.ob, value)

# XXX the indexing in code like
#     addr.signed[0] = v
#     is just silly.  remove it.

class _fakeaccessor(object):
    def __init__(self, addr):
        self.addr = addr
    def __getitem__(self, index):
        assert index == 0
        return self.convert(self.addr.get())

    def __setitem__(self, index, value):
        assert index == 0
        self.addr.set(value)

        
class _signed_fakeaccessor(_fakeaccessor):
    TYPE = lltype.Signed

    def convert(self, value):
        assert lltype.typeOf(value) == self.TYPE
        return value

class _address_fakeaccessor(_fakeaccessor):
    TYPE = None

    def convert(self, value):
        # XXX is this the right check for "Ptr-ness" ?
        assert isinstance(value, lltype._ptr)
        return fakeaddress(value)


fakeaddress.signed = property(_signed_fakeaccessor)
fakeaddress.address = property(_address_fakeaccessor)

Address = lltype.Primitive("Address", fakeaddress(None))

fakeaddress._TYPE = Address
