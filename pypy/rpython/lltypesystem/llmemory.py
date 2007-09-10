# this file contains the definitions and most extremely faked
# implementations of things relating to the description of the layout
# of objects in memeory.

# sizeof, offsetof

import weakref
from pypy.rlib.objectmodel import Symbolic
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

    def _raw_malloc(self, rest, zero):
        raise NotImplementedError("_raw_malloc(%r, %r)" % (self, rest))

    def raw_memcopy(self, srcadr, dstsrc):
        raise NotImplementedError("raw_memcopy(%r)" % (self,))


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

    __rmul__ = __mul__

    def __neg__(self):
        return ItemOffset(self.TYPE, -self.repeat)

    def ref(self, firstitemptr):
        A = lltype.typeOf(firstitemptr).TO
        if A == self.TYPE:
            # for array of containers
            parent, index = lltype.parentlink(firstitemptr._obj)
            assert parent, "%r is not within a container" % (firstitemptr,)
            assert isinstance(lltype.typeOf(parent),
                              (lltype.Array, lltype.FixedSizeArray)), (
                "%r is not within an array" % (firstitemptr,))
            if isinstance(index, str):
                assert index.startswith('item')    # itemN => N
                index = int(index[4:])
            return parent.getitem(index + self.repeat)._as_ptr()
        elif isinstance(A, lltype.FixedSizeArray) and A.OF == self.TYPE:
            # for array of primitives or pointers
            return lltype.direct_ptradd(firstitemptr, self.repeat)
        else:
            raise TypeError('got %r, expected %r' % (A, self.TYPE))

    def _raw_malloc(self, rest, zero):
        assert not rest
        if (isinstance(self.TYPE, lltype.ContainerType)
            and self.TYPE._gckind == 'gc'):
            assert self.repeat == 1
            p = lltype.malloc(self.TYPE, flavor='raw', zero=zero)
            return cast_ptr_to_adr(p)
        else:
            T = lltype.FixedSizeArray(self.TYPE, self.repeat)
            p = lltype.malloc(T, flavor='raw', zero=zero)
            array_adr = cast_ptr_to_adr(p)
            return array_adr + ArrayItemsOffset(T)

    def raw_memcopy(self, srcadr, dstadr):
        repeat = self.repeat
        if repeat == 0:
            return
        from pypy.rpython.rctypes.rmodel import reccopy
        if isinstance(self.TYPE, lltype.ContainerType):
            PTR = lltype.Ptr(self.TYPE)
        else:
            PTR = lltype.Ptr(lltype.FixedSizeArray(self.TYPE, 1))
        while True:
            src = cast_adr_to_ptr(srcadr, PTR)
            dst = cast_adr_to_ptr(dstadr, PTR)
            reccopy(src, dst)
            repeat -= 1
            if repeat <= 0:
                break
            srcadr += ItemOffset(self.TYPE)
            dstadr += ItemOffset(self.TYPE)


class FieldOffset(AddressOffset):

    def __init__(self, TYPE, fldname):
        self.TYPE = TYPE
        self.fldname = fldname

    def __repr__(self):
        return "<FieldOffset %r %r>" % (self.TYPE, self.fldname)

    def ref(self, struct):
        if lltype.typeOf(struct).TO != self.TYPE:
            struct = lltype.cast_pointer(lltype.Ptr(self.TYPE), struct)
        FIELD = getattr(self.TYPE, self.fldname)
        if isinstance(FIELD, lltype.ContainerType):
            return getattr(struct, self.fldname)
        else:
            return lltype.direct_fieldptr(struct, self.fldname)

    def _raw_malloc(self, rest, parenttype=None, zero=False):
        if self.fldname != self.TYPE._arrayfld:
            # for the error msg
            return AddressOffset._raw_malloc(self, rest, zero=zero)
        assert rest
        return rest[0]._raw_malloc(rest[1:], parenttype=parenttype or self.TYPE,
                                            zero=zero)

    def raw_memcopy(self, srcadr, dstadr):
        if self.fldname != self.TYPE._arrayfld:
            return AddressOffset.raw_memcopy(srcadr, dstadr) #for the error msg
        PTR = lltype.Ptr(self.TYPE)
        src = cast_adr_to_ptr(srcadr, PTR)
        dst = cast_adr_to_ptr(dstadr, PTR)
        from pypy.rpython.rctypes.rmodel import reccopy
        reccopy(src, dst)


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

    def ref(self, ptr):
        for item in self.offsets:
            ptr = item.ref(ptr)
        return ptr

    def _raw_malloc(self, rest, zero):
        return self.offsets[0]._raw_malloc(self.offsets[1:] + rest, zero=zero)

    def raw_memcopy(self, srcadr, dstadr):
        for o in self.offsets[:-1]:
            o.raw_memcopy(srcadr, dstadr)
            srcadr += o
            dstadr += o
        o = self.offsets[-1]
        o.raw_memcopy(srcadr, dstadr)


class ArrayItemsOffset(AddressOffset):

    def __init__(self, TYPE):
        self.TYPE = TYPE

    def __repr__(self):
        return '< ArrayItemsOffset %r >' % (self.TYPE,)

    def ref(self, arrayptr):
        assert lltype.typeOf(arrayptr).TO == self.TYPE
        if isinstance(self.TYPE.OF, lltype.ContainerType):
            return arrayptr[0]
        else:
            return lltype.direct_arrayitems(arrayptr)

    def _raw_malloc(self, rest, parenttype=None, zero=False):
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
                          immortal = self.TYPE._gckind == 'raw',
                          zero = zero)
        return cast_ptr_to_adr(p)

    def raw_memcopy(self, srcadr, dstadr):
        # should really copy the length field, but we can't
        pass


class ArrayLengthOffset(AddressOffset):

    def __init__(self, TYPE):
        self.TYPE = TYPE

    def __repr__(self):
        return '< ArrayLengthOffset %r >' % (self.TYPE,)

    def ref(self, arrayptr):
        assert lltype.typeOf(arrayptr).TO == self.TYPE
        return lltype._arraylenref._makeptr(arrayptr._obj, arrayptr._solid)


class GCHeaderOffset(AddressOffset):
    def __init__(self, gcheaderbuilder):
        self.gcheaderbuilder = gcheaderbuilder

    def __repr__(self):
        return '< GCHeaderOffset >'

    def __neg__(self):
        return GCHeaderAntiOffset(self.gcheaderbuilder)

    def ref(self, headerptr):
        gcptr = self.gcheaderbuilder.object_from_header(headerptr)
        return gcptr

    def _raw_malloc(self, rest, zero):
        assert rest
        if isinstance(rest[0], GCHeaderAntiOffset):
            return rest[1]._raw_malloc(rest[2:], zero=zero)    # just for fun
        gcobjadr = rest[0]._raw_malloc(rest[1:], zero=zero)
        headerptr = self.gcheaderbuilder.new_header(gcobjadr.ptr)
        return cast_ptr_to_adr(headerptr)

    def raw_memcopy(self, srcadr, dstadr):
        from pypy.rpython.rctypes.rmodel import reccopy
        reccopy(srcadr.ptr, dstadr.ptr)

class GCHeaderAntiOffset(AddressOffset):
    def __init__(self, gcheaderbuilder):
        self.gcheaderbuilder = gcheaderbuilder

    def __repr__(self):
        return '< GCHeaderAntiOffset >'

    def __neg__(self):
        return GCHeaderOffset(self.gcheaderbuilder)

    def ref(self, gcptr):
        headerptr = self.gcheaderbuilder.header_of_object(gcptr)
        return headerptr

    def _raw_malloc(self, rest, zero):
        assert len(rest) >= 2
        assert isinstance(rest[0], GCHeaderOffset)
        return rest[1]._raw_malloc(rest[2:], zero=zero)

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
    # NOTE: the 'ptr' in the addresses must be normalized.
    # Use cast_ptr_to_adr() instead of directly fakeaddress() if unsure.
    def __init__(self, ptr):
        self.ptr = ptr or None   # null ptr => None

    def __repr__(self):
        if self.ptr is None:
            s = 'NULL'
        else:
            s = str(self.ptr)
        return '<fakeaddr %s>' % (s,)

    def __add__(self, other):
        if isinstance(other, AddressOffset):
            if self.ptr is None:
                raise NullAddressError("offset from NULL address")
            return fakeaddress(other.ref(self.ptr))
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
        return self.ptr is not None

    def __eq__(self, other):
        if isinstance(other, fakeaddress):
            obj1 = self.ptr
            obj2 = other.ptr
            if obj1 is not None: obj1 = obj1._obj
            if obj2 is not None: obj2 = obj2._obj
            return obj1 == obj2
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, fakeaddress):
            return not (self == other)
        else:
            return NotImplemented

    def ref(self):
        if not self:
            raise NullAddressError
        return self.ptr

##    def get(self):
##        return self.ref().get()

##    def set(self, value):
##        self.ref().set(value)

    def _cast_to_ptr(self, EXPECTED_TYPE):
        if self:
            PTRTYPE = lltype.typeOf(self.ptr)
            if (isinstance(EXPECTED_TYPE.TO, lltype.OpaqueType) or
                isinstance(PTRTYPE.TO, lltype.OpaqueType)):
                return lltype.cast_opaque_ptr(EXPECTED_TYPE, self.ptr)
            else:
                # regular case
                return lltype.cast_pointer(EXPECTED_TYPE, self.ptr)
        else:
            return lltype.nullptr(EXPECTED_TYPE.TO)

##        if (isinstance(ref, _arrayitemref) and
##            isinstance(EXPECTED_TYPE.TO, lltype.FixedSizeArray) and
##            ref.type() == EXPECTED_TYPE.TO.OF):
##            # special case that requires direct_arrayitems
##            p_items = lltype.direct_arrayitems(ref.array)
##            return lltype.direct_ptradd(p_items, ref.index)
##        elif (isinstance(ref, _structfieldref) and
##              isinstance(EXPECTED_TYPE.TO, lltype.FixedSizeArray) and
##              ref.type() == EXPECTED_TYPE.TO.OF):
##            # special case that requires direct_fieldptr
##            return lltype.direct_fieldptr(ref.struct,
##                                          ref.fieldname)
##        else:
##            result = ref.get()
##            if (isinstance(EXPECTED_TYPE.TO, lltype.OpaqueType) or
##                isinstance(lltype.typeOf(result).TO, lltype.OpaqueType)):
##                return lltype.cast_opaque_ptr(EXPECTED_TYPE, result)
##            else:
##                # regular case
##                return lltype.cast_pointer(EXPECTED_TYPE, result)

    def _cast_to_int(self):
        if self:
            return self.ptr._cast_to_int()
        else:
            return 0

# ____________________________________________________________

class NullAddressError(Exception):
    pass

class DanglingPointerError(Exception):
    pass

NULL = fakeaddress(None)
NULL.intaddress = 0      # this is to make memory.lladdress more happy
Address = lltype.Primitive("Address", NULL)

# GCREF is similar to Address but it is GC-aware
GCREF = lltype.Ptr(lltype.GcOpaqueType('GCREF'))


class _fakeaccessor(object):
    def __init__(self, addr):
        self.addr = addr
    def __getitem__(self, index):
        ptr = self.addr.ref()
        if index != 0:
            ptr = lltype.direct_ptradd(ptr, index)
        return self.read_from_ptr(ptr)

    def __setitem__(self, index, value):
        assert lltype.typeOf(value) == self.TYPE
        ptr = self.addr.ref()
        if index != 0:
            ptr = lltype.direct_ptradd(ptr, index)
        self.write_into_ptr(ptr, value)

    def read_from_ptr(self, ptr):
        value = ptr[0]
        assert lltype.typeOf(value) == self.TYPE
        return value

    def write_into_ptr(self, ptr, value):
        ptr[0] = value


class _signed_fakeaccessor(_fakeaccessor):
    TYPE = lltype.Signed

class _char_fakeaccessor(_fakeaccessor):
    TYPE = lltype.Char

class _address_fakeaccessor(_fakeaccessor):
    TYPE = Address

    def read_from_ptr(self, ptr):
        value = ptr[0]
        if isinstance(value, lltype._ptr):
            return value._cast_to_adr()
        elif lltype.typeOf(value) == Address:
            return value
        else:
            raise TypeError(value)

    def write_into_ptr(self, ptr, value):
        TARGETTYPE = lltype.typeOf(ptr).TO.OF
        if TARGETTYPE == Address:
            pass
        elif isinstance(TARGETTYPE, lltype.Ptr):
            value = cast_adr_to_ptr(value, TARGETTYPE)
        else:
            raise TypeError(TARGETTYPE)
        ptr[0] = value


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

def cast_int_to_adr(int):
    raise NotImplementedError("cast_int_to_adr")


# ____________________________________________________________

class fakeweakaddress(object):
    def __init__(self, ob):
        if ob is not None:
            self.ref = weakref.ref(ob)
            # umpf
            from pypy.rpython.memory import lltypesimulation
            if isinstance(ob, (lltype._ptr,lltypesimulation.simulatorptr)):
                self.id = ob._cast_to_int()
            else:
                self.id = id(ob)
        else:
            self.ref = None
    def get(self):
        if self.ref is None:
            return None
        ob = self.ref()
        # xxx stop-gap
        #if ob is None:
        #    raise DanglingPointerError
        return ob
    def __repr__(self):
        if self.ref is None:
            s = 'NULL'
        else:
            s = str(self.ref)
        return '<%s %s>' % (self.__class__.__name__, s)
    def cast_to_int(self):
        # this is not always the behaviour that is really happening
        # but make sure that nobody depends on it
        return self.id ^ ~3

WeakGcAddress = lltype.Primitive("WeakGcAddress",
                                 fakeweakaddress(None))

def cast_ptr_to_weakadr(obj):
    # XXX this is missing the normalizations done by _ptr._cast_to_adr()
    assert isinstance(lltype.typeOf(obj), lltype.Ptr)
    return fakeweakaddress(obj)

def cast_weakadr_to_ptr(adr, EXPECTED_TYPE):
    result = adr.get()
    if result is None:
        return lltype.nullptr(EXPECTED_TYPE.TO)
    return result

fakeweakaddress._TYPE = WeakGcAddress
WEAKNULL = fakeweakaddress(None)

# ____________________________________________________________

WeakGcRefOpaque = lltype.OpaqueType('WeakGcRef')

def weakgcref_init(wropaque, obj):
    PTRTYPE = lltype.typeOf(obj)
    assert isinstance(PTRTYPE, lltype.Ptr)
    assert PTRTYPE.TO._gckind == 'gc'
    wropaque._obj.ref = weakref.ref(lltype.normalizeptr(obj))

def weakgcref_get(PTRTYPE, wropaque):
    assert isinstance(PTRTYPE, lltype.Ptr)
    assert PTRTYPE.TO._gckind == 'gc'
    assert lltype.typeOf(wropaque) == lltype.Ptr(WeakGcRefOpaque)
    p = wropaque._obj.ref()
    if p is None:
        return lltype.nullptr(PTRTYPE.TO)
    else:
        return lltype.cast_pointer(PTRTYPE, p)

# ____________________________________________________________

def raw_malloc(size):
    if not isinstance(size, AddressOffset):
        raise NotImplementedError(size)
    return size._raw_malloc([], zero=False)

def raw_free(adr):
    # try to free the whole object if 'adr' is the address of the header
    from pypy.rpython.memory.gcheader import GCHeaderBuilder
    try:
        objectptr = GCHeaderBuilder.object_from_header(adr.ptr)
    except KeyError:
        pass
    else:
        raw_free(cast_ptr_to_adr(objectptr))
    assert isinstance(adr.ref()._obj, lltype._parentable)
    adr.ptr._as_obj()._free()

def raw_malloc_usage(size):
    if isinstance(size, AddressOffset):
        # ouah
        from pypy.rpython.memory.lltypelayout import convert_offset_to_int
        size = convert_offset_to_int(size)
    return size

def raw_memclear(adr, size):
    if not isinstance(size, AddressOffset):
        raise NotImplementedError(size)
    assert lltype.typeOf(adr) == Address
    zeroadr = size._raw_malloc([], zero=True)
    size.raw_memcopy(zeroadr, adr)

def raw_memcopy(source, dest, size):
    assert lltype.typeOf(source) == Address
    assert lltype.typeOf(dest)   == Address
    size.raw_memcopy(source, dest)

# ____________________________________________________________

ARENA_ITEM = lltype.OpaqueType('ArenaItem')

class _arena(object):
    #_cache = weakref.WeakKeyDictionary()    # {obj: _arenaitem}

    def __init__(self, rng, zero):
        self.rng = rng
        self.zero = zero
        self.items = []

    def getitemaddr(self, n):
        while len(self.items) <= n:
            self.items.append(_arenaitem(self, len(self.items)))
        return fakeaddress(self.items[n]._as_ptr())

class _arenaitem(lltype._container):
    _TYPE = ARENA_ITEM

    def __init__(self, arena, nr):
        self.arena = arena
        self.nr = nr
        self.reserved_size = None

    def reserve(self, size):
        if self.reserved_size is None:
            # xxx check that we are not larger than unitsize*n
            itemadr = raw_malloc(size)
            self.container = itemadr.ptr._obj
            #_arena._cache[itemadr.ptr._obj] = self
        else:
            assert size == self.reserved_size

class ArenaRange(AddressOffset):
    def __init__(self, unitsize, n):
        self.unitsize = unitsize
        self.n = n

    def _raw_malloc(self, rest, zero=False):
        assert not rest
        arena = _arena(self, zero=zero)
        return arena.getitemaddr(0)
        
def arena(TYPE, n):
    return ArenaRange(sizeof(TYPE), n)

def bump(adr, size):
    baseptr = cast_adr_to_ptr(adr, lltype.Ptr(ARENA_ITEM))
    baseptr._obj.reserve(size)
    arena = baseptr._obj.arena
    nr = baseptr._obj.nr
    return arena.getitemaddr(nr + 1)
