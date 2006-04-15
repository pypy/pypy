# this file contains the definitions and most extremely faked
# implementations of things relating to the description of the layout
# of objects in memeory.

# sizeof, offsetof

from pypy.rpython.objectmodel import Symbolic
from pypy.rpython.lltypesystem import lltype

class AddressOffset(Symbolic):

    def annotation(self):
        from pypy.annotation import model
        return model.SomeInteger()

    def lltype(self):
        return lltype.Signed

    def __add__(self, other):
        if not isinstance(other, AddressOffset):
            return NotImplemented
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

    def ref(self, firstitemref):
        assert isinstance(firstitemref, _arrayitemref)
        array = firstitemref.array
        assert lltype.typeOf(array).TO.OF == self.TYPE
        index = firstitemref.index + self.repeat
        return _arrayitemref(array, index)


class FieldOffset(AddressOffset):

    def __init__(self, TYPE, fldname):
        self.TYPE = TYPE
        self.fldname = fldname

    def __repr__(self):
        return "<FieldOffset %r %r>" % (self.TYPE, self.fldname)

    def ref(self, containerref):
        struct = containerref.get()
        assert lltype.typeOf(struct).TO == self.TYPE
        return _structfieldref(struct, self.fldname)


class CompositeOffset(AddressOffset):

    def __init__(self, first, second):
        self.first = first
        self.second = second

    def __repr__(self):
        return '< %r + %r >'%(self.first, self.second)

    def ref(self, containerref):
        return self.second.ref(self.first.ref(containerref))


class ArrayItemsOffset(AddressOffset):

    def __init__(self, TYPE):
        self.TYPE = TYPE

    def __repr__(self):
        return '< ArrayItemsOffset >'

    def ref(self, arrayref):
        array = arrayref.get()
        assert lltype.typeOf(array).TO == self.TYPE
        return _arrayitemref(array, index=0)

class ArrayLengthOffset(AddressOffset):

    def __init__(self, TYPE):
        self.TYPE = TYPE

    def __repr__(self):
        return '< ArrayLengthOffset >'

    def ref(self, arrayref):
        array = arrayref.get()
        assert lltype.typeOf(array).TO == self.TYPE
        return _arraylenref(array)


class _arrayitemref(object):
    def __init__(self, array, index):
        self.array = array
        self.index = index
    def get(self):
        return self.array[self.index]
    def set(self, value):
        self.array[self.index] = value
    def type(self):
        return lltype.typeOf(self.array).TO.OF

class _arraylenref(object):
    def __init__(self, array):
        self.array = array
    def get(self):
        return len(self.array)
    def set(self, value):
        raise Exception("can't assign to an array's length")
    def type(self):
        return lltype.Signed

class _structfieldref(object):
    def __init__(self, struct, fieldname):
        self.struct = struct
        self.fieldname = fieldname
    def get(self):
        return getattr(self.struct, self.fieldname)
    def set(self, value):
        setattr(self.struct, self.fieldname, value)
    def type(self):
        return getattr(lltype.typeOf(self.struct).TO, self.fieldname)

class _obref(object):
    def __init__(self, ob):
        self.ob = ob
    def get(self):
        return self.ob
    def set(self, value):
        raise Exception("can't assign to whole object")
    def type(self):
        return lltype.typeOf(self.ob)

# ____________________________________________________________

def sizeof(TYPE, n=None):
    if n is None:
        assert not TYPE._is_varsize()
        return ItemOffset(TYPE)
    else:
        if isinstance(TYPE, lltype.Array):
            return itemoffsetof(TYPE, n)
        elif isinstance(TYPE, lltype.Struct):
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

    def __repr__(self):
        if self.ob is None:
            s = 'NULL'
        else:
            s = str(self.ob)
        if self.offset is not None:
            s = '%s + %r' % (s, self.offset)
        return '<fakeaddr %s>' % (s,)

    def __add__(self, other):
        if isinstance(other, AddressOffset):
            if self.offset is None:
                offset = other
            else:
                offset = self.offset + other
            return fakeaddress(self.ob, offset)
        return NotImplemented

    def __eq__(self, other):
        if not isinstance(other, fakeaddress):
            return False
        if self.ob is None:
            return other.ob is None
        if other.ob is None:
            return False
        ref1 = self.ref()
        ref2 = other.ref()
        return (ref1.__class__ is ref2.__class__ and
                ref1.__dict__ == ref2.__dict__)

    def __ne__(self, other):
        return not (self == other)

    def ref(self):
        ref = _obref(self.ob)
        if self.offset is not None:
            ref = self.offset.ref(ref)
        return ref

    def get(self):
        return self.ref().get()

    def set(self, value):
        self.ref().set(value)

    def _cast_to_ptr(self, EXPECTED_TYPE):
        ref = self.ref()
        if (isinstance(ref, _arrayitemref) and
            isinstance(EXPECTED_TYPE.TO, lltype.FixedSizeArray) and
            ref.type() == EXPECTED_TYPE.TO.OF):
            # special case that requires cast_subarray_pointer
            return lltype.cast_subarray_pointer(EXPECTED_TYPE,
                                                ref.array,
                                                ref.index)
        elif (isinstance(ref, _structfieldref) and
              isinstance(EXPECTED_TYPE.TO, lltype.FixedSizeArray) and
              ref.type() == EXPECTED_TYPE.TO.OF):
            # special case that requires cast_structfield_pointer
            return lltype.cast_structfield_pointer(EXPECTED_TYPE,
                                                   ref.struct,
                                                   ref.fieldname)
        else:
            # regular case
            return lltype.cast_pointer(EXPECTED_TYPE, ref.get())

    def _cast_to_int(self):
        return self.get()._cast_to_int()

# ____________________________________________________________

NULL = fakeaddress(None) # XXX this should be the same as memory.lladdress.NULL
Address = lltype.Primitive("Address", NULL)


class _fakeaccessor(object):
    def __init__(self, addr):
        self.addr = addr
    def __getitem__(self, index):
        addr = self.addr
        if index != 0:
            addr += ItemOffset(addr.ref().type(), index)
        return self.convert(addr.get())

    def __setitem__(self, index, value):
        addr = self.addr
        if index != 0:
            addr += ItemOffset(addr.ref().type(), index)
        addr.set(value)

    def convert(self, value):
        assert lltype.typeOf(value) == self.TYPE
        return value


class _signed_fakeaccessor(_fakeaccessor):
    TYPE = lltype.Signed

class _char_fakeaccessor(_fakeaccessor):
    TYPE = lltype.Char

class _address_fakeaccessor(_fakeaccessor):
    TYPE = Address

    def convert(self, value):
        if isinstance(value, lltype._ptr):
            return fakeaddress(value)
        elif isinstance(value, Address):
            return value
        else:
            raise TypeError(value)


fakeaddress.signed = property(_signed_fakeaccessor)
fakeaddress.char = property(_char_fakeaccessor)
fakeaddress.address = property(_address_fakeaccessor)
fakeaddress._TYPE = Address

# the obtained address will not keep the object alive. e.g. if the object is
# only reachable through an address, it might get collected
def cast_ptr_to_adr(obj):
    assert isinstance(lltype.typeOf(obj), lltype.Ptr)
    return obj._cast_to_adr()

def cast_adr_to_ptr(adr, EXPECTED_TYPE):
    return adr._cast_to_ptr(EXPECTED_TYPE)

def cast_adr_to_int(adr):
    return adr._cast_to_int()

