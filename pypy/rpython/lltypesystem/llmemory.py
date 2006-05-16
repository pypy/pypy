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

    def raw_malloc(self, rest):
        raise NotImplementedError("raw_malloc(%r, %r)" % (self, rest))


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

    def __neg__(self):
        return ItemOffset(self.TYPE, -self.repeat)

    def ref(self, firstitemref):
        assert isinstance(firstitemref, _arrayitemref)
        array = firstitemref.array
        assert lltype.typeOf(array).TO.OF == self.TYPE
        index = firstitemref.index + self.repeat
        return _arrayitemref(array, index)

    def raw_malloc(self, rest):
        assert not rest
        if (isinstance(self.TYPE, lltype.ContainerType)
            and self.TYPE._gcstatus()):
            assert self.repeat == 1
            p = lltype.malloc(self.TYPE)
            return cast_ptr_to_adr(p)
        else:
            T = lltype.FixedSizeArray(self.TYPE, self.repeat)
            p = lltype.malloc(T, immortal=True)
            array_adr = cast_ptr_to_adr(p)
            return array_adr + ArrayItemsOffset(T)


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

    def raw_malloc(self, rest, parenttype=None):
        if self.fldname != self.TYPE._arrayfld:
            return AddressOffset.raw_malloc(self, rest)   # for the error msg
        assert rest
        return rest[0].raw_malloc(rest[1:], parenttype=parenttype or self.TYPE)


class CompositeOffset(AddressOffset):

    def __new__(cls, *offsets):
        lst = []
        for item in offsets:
            if isinstance(item, CompositeOffset):
                lst.extend(item.offsets)
            else:
                lst.append(item)
        for i in range(len(lst)-2, -1, -1):
            if (isinstance(lst[i], ItemOffset) and
                isinstance(lst[i+1], ItemOffset) and
                lst[i].TYPE == lst[i+1].TYPE):
                lst[i:i+2] = [ItemOffset(lst[i].TYPE,
                                         lst[i].repeat + lst[i+1].repeat)]
        if len(lst) == 1:
            return lst[0]
        else:
            self = object.__new__(cls)
            self.offsets = lst
            return self

    def __repr__(self):
        return '< %s >' % (' + '.join([repr(item) for item in self.offsets]),)

    def __neg__(self):
        ofs = [-item for item in self.offsets]
        ofs.reverse()
        return CompositeOffset(*ofs)

    def ref(self, ref):
        for item in self.offsets:
            ref = item.ref(ref)
        return ref

    def raw_malloc(self, rest):
        return self.offsets[0].raw_malloc(self.offsets[1:] + rest)


class ArrayItemsOffset(AddressOffset):

    def __init__(self, TYPE):
        self.TYPE = TYPE

    def __repr__(self):
        return '< ArrayItemsOffset %r >' % (self.TYPE,)

    def ref(self, arrayref):
        array = arrayref.get()
        assert lltype.typeOf(array).TO == self.TYPE
        return _arrayitemref(array, index=0)

    def raw_malloc(self, rest, parenttype=None):
        if rest:
            assert len(rest) == 1
            assert isinstance(rest[0], ItemOffset)
            assert self.TYPE.OF == rest[0].TYPE
            count = rest[0].repeat
        else:
            count = 0
        if self.TYPE._hints.get('isrpystring'):
            count -= 1  # because malloc() will give us the extra char for free
        p = lltype.malloc(parenttype or self.TYPE, count,
                          immortal = not self.TYPE._gcstatus())
        return cast_ptr_to_adr(p)


class ArrayLengthOffset(AddressOffset):

    def __init__(self, TYPE):
        self.TYPE = TYPE

    def __repr__(self):
        return '< ArrayLengthOffset %r >' % (self.TYPE,)

    def ref(self, arrayref):
        array = arrayref.get()
        assert lltype.typeOf(array).TO == self.TYPE
        return _arraylenref(array)


class GCHeaderOffset(AddressOffset):
    def __init__(self, minimal_layout):
        self.minimal_layout = minimal_layout

    def __repr__(self):
        return '< GCHeaderOffset >'

    def __neg__(self):
        return GCHeaderAntiOffset(self.minimal_layout)

    def ref(self, headerref):
        header = headerref.get()
        gcobj = _gc_header2struct[header._obj]
        return _obref(lltype._ptr(lltype.Ptr(gcobj._TYPE), gcobj))

    def raw_malloc(self, rest):
        assert rest
        if isinstance(rest[0], GCHeaderAntiOffset):
            return rest[1].raw_malloc(rest[2:])    # just for fun
        gcobjadr = rest[0].raw_malloc(rest[1:])
        return gcobjadr - self


class GCHeaderAntiOffset(AddressOffset):
    def __init__(self, minimal_layout):
        self.minimal_layout = minimal_layout

    def __repr__(self):
        return '< GCHeaderAntiOffset >'

    def __neg__(self):
        return GCHeaderOffset(self.minimal_layout)

    def ref(self, gcptrref):
        gcptr = gcptrref.get()
        try:
            headerobj = _gc_struct2header[gcptr._obj]
        except KeyError:
            # sanity checks
            HDR = self.minimal_layout
            gcobj = gcptr._obj
            assert isinstance(gcobj._TYPE, lltype.GC_CONTAINER)
            assert not gcobj._parentstructure()
            
            headerobj = lltype.malloc(HDR, immortal=True)._obj
            # make uninitialized access explode
            for fldname in HDR._names:
                getattr(type(headerobj), fldname).__set__(headerobj, None)
            _gc_struct2header[gcptr._obj] = headerobj
            _gc_header2struct[headerobj] = gcobj
        p = lltype._ptr(lltype.Ptr(headerobj._TYPE), headerobj, True)
        return _obref(p)

    def raw_malloc(self, rest):
        assert rest
        assert isinstance(rest[0], GCHeaderOffset)
        return rest[1].raw_malloc(rest[2:])


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
        if value != len(self.array):
            raise Exception("can't change the length of an array")
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
        assert not isinstance(ob, lltype._parentable)
        self.ob = ob or None    # replace null pointers with None
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
            res = fakeaddress(self.ob, offset)
            #res.ref() # sanity check
            return res
        if other == 0:
            return self
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, AddressOffset):
            return self + (-other)
        if other == 0:
            return self
        return NotImplemented

    def __nonzero__(self):
        return self.ob is not None

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
        if not self:
            raise NullAddressError
        ref = _obref(self.ob)
        if self.offset is not None:
            ref = self.offset.ref(ref)
        return ref

    def get(self):
        return self.ref().get()

    def set(self, value):
        self.ref().set(value)

    def _cast_to_ptr(self, EXPECTED_TYPE):
        if not self:
            return lltype.nullptr(EXPECTED_TYPE.TO)
        ref = self.ref()
        if (isinstance(ref, _arrayitemref) and
            isinstance(EXPECTED_TYPE.TO, lltype.FixedSizeArray) and
            ref.type() == EXPECTED_TYPE.TO.OF):
            # special case that requires direct_arrayitems
            p_items = lltype.direct_arrayitems(ref.array)
            return lltype.direct_ptradd(p_items, ref.index)
        elif (isinstance(ref, _structfieldref) and
              isinstance(EXPECTED_TYPE.TO, lltype.FixedSizeArray) and
              ref.type() == EXPECTED_TYPE.TO.OF):
            # special case that requires direct_fieldptr
            return lltype.direct_fieldptr(ref.struct,
                                          ref.fieldname)
        else:
            result = ref.get()
            if (isinstance(EXPECTED_TYPE.TO, lltype.OpaqueType) or
                isinstance(lltype.typeOf(result).TO, lltype.OpaqueType)):
                return lltype.cast_opaque_ptr(EXPECTED_TYPE, result)
            else:
                # regular case
                return lltype.cast_pointer(EXPECTED_TYPE, result)

    def _cast_to_int(self):
        if self:
            return self.get()._cast_to_int()
        else:
            return 0

# ____________________________________________________________

class NullAddressError(Exception):
    pass

NULL = fakeaddress(None)
NULL.intaddress = 0      # this is to make memory.lladdress more happy
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

    def convert(self, value):
        # hack to try to interpret the items of an array of bytes as chars
        if lltype.typeOf(value) == lltype.Signed:
            value = chr(value)
        assert lltype.typeOf(value) == lltype.Char
        return value

class _address_fakeaccessor(_fakeaccessor):
    TYPE = Address

    def convert(self, value):
        if isinstance(value, lltype._ptr):
            return fakeaddress(value)
        elif lltype.typeOf(value) == Address:
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

# ____________________________________________________________

import weakref
_gc_struct2header = weakref.WeakKeyDictionary()
_gc_header2struct = weakref.WeakKeyDictionary()

def raw_malloc(size):
    if not isinstance(size, AddressOffset):
        raise NotImplementedError(size)
    return size.raw_malloc([])

def raw_free(adr):
    pass   # for now

def raw_malloc_usage(size):
    if isinstance(size, AddressOffset):
        # ouah
        from pypy.rpython.memory.lltypelayout import convert_offset_to_int
        size = convert_offset_to_int(size)
    return size

# ____________________________________________________________

class _arena(object):

    def __init__(self, rng):
        self.rng = rng
        self.items = []

class ArenaItem(AddressOffset):
    
    def __init__(self, nr):
        self.nr = nr

    def ref(self, ref):
        assert isinstance(ref, _obref)
        assert isinstance(ref.ob, _arena)
        arena = ref.ob
        itemadr = arena.items[self.nr]
        return itemadr.ref()
        
class ArenaRange(AddressOffset):
    def __init__(self, unitsize, n):
        self.unitsize = unitsize
        self.n = n

    def raw_malloc(self, rest):
        assert not rest
        return fakeaddress(_arena(self), ArenaItem(0))
        
def arena(TYPE, n):
    return ArenaRange(sizeof(TYPE), n)

def bump(adr, size):
    assert isinstance(adr.ob, _arena)
    assert isinstance(adr.offset, ArenaItem)
    arena = adr.ob
    nr = adr.offset.nr
    if len(arena.items) == nr: # reserve
        # xxx check that we are not larger than unitsize*n
        itemadr = raw_malloc(size)
        arena.items.append(itemadr)
    else:
        assert nr < len(arena.items)
        # xxx check that size matches
    return fakeaddress(arena, ArenaItem(nr+1))
