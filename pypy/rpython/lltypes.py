import weakref
import py
from pypy.tool.rarithmetic import r_uint


class LowLevelType(object):
    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.__dict__ == other.__dict__
    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        items = self.__dict__.items()
        items.sort()
        return hash((self.__class__,) + tuple(items))

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return self.__class__.__name__

    def _defl(self):
        raise NotImplementedError


class ContainerType(LowLevelType):
    pass


class Struct(ContainerType):
    def __init__(self, name, *fields):
        self._name = name
        self._flds = flds = {}
        self._names = names = []
        self._arrayfld = None
        for name, typ in fields:
            if name.startswith('_'):
                raise NameError, ("%s: field name %r should not start with "
                                  "an underscore" % (self._name, name,))
            names.append(name)
            if name in flds:
                raise TypeError("%s: repeated field name" % self._name)
            flds[name] = typ
        # look if we have an inlined variable-sized array as the last field
        if fields:
            for name, typ in fields[:-1]:
                if isinstance(typ, Array):
                    raise TypeError("%s: array field must be last")
            name, typ = fields[-1]
            if isinstance(typ, Array):
                self._arrayfld = name

    def __getattr__(self, name):
        try:
            return self._flds[name]
        except KeyError:
            raise AttributeError, 'struct %s has no field %r' % (self._name,
                                                                 name)

    def _str_fields(self):
        return ', '.join(['%s: %s' % (name, self._flds[name])
                          for name in self._names])

    def __str__(self):
        return "Struct %s { %s }" % (self._name, self._str_fields())

    def _defl(self):
        return _struct(self)


class Array(ContainerType):
    def __init__(self, *fields):
        self.OF = Struct("<arrayitem>", *fields)
        if self.OF._arrayfld is not None:
            raise TypeError("array cannot contain an inlined array")

    def __str__(self):
        return "Array of { %s }" % (self.OF._str_fields(),)


class Primitive(LowLevelType):
    def __init__(self, name, default):
        self._name = name
        self._default = default

    def __str__(self):
        return self._name

    def _defl(self):
        return self._default


Signed   = Primitive("Signed", 0)
Unsigned = Primitive("Unsigned", r_uint(0))
Char     = Primitive("Char", '\x00')
Bool     = Primitive("Bool", False)
Void     = Primitive("Void", None)


class _PtrType(LowLevelType):
    def __init__(self, TO, **flags):
        if not isinstance(TO, ContainerType):
            raise TypeError, ("can only point to a Struct or an Array, "
                              "not to %s" % (TO,))
        self.TO = TO
        self.flags = flags

    def _str_flags(self):
        flags = self.flags.keys()
        flags.sort()
        result = []
        for flag in flags:
            if self.flags[flag] is not True:
                flag = '%s=%r' % (flag, self.flags[flag])
            result.append(flag)
        return ', '.join(result)

    def __str__(self):
        return 'ptr(%s) to %s' % (self._str_flags(), self.TO)

    def _defl(self):
        return _ptr(self, None)

def GcPtr(TO, **flags):
    return _PtrType(TO, gc=True, **flags)

def NonGcPtr(TO, **flags):
    return _PtrType(TO, **flags)


# ____________________________________________________________


def typeOf(val):
    if isinstance(val, bool):
        return Bool
    if isinstance(val, r_uint):
        return Unsigned
    if isinstance(val, int):
        return Signed
    if isinstance(val, str):
        assert len(val) == 1
        return Char
    if val is None:
        return Void   # maybe
    return val._TYPE

class InvalidCast(TypeError):
    pass

def cast_flags(PTRTYPE, ptr):
    if not isinstance(ptr, _ptr) or not isinstance(PTRTYPE, _PtrType):
        raise TypeError, "can only cast pointers to other pointers"
    CURTYPE = ptr._TYPE
    if CURTYPE.TO != PTRTYPE.TO:
        raise TypeError, "cast_flags only between pointers to the same type"
    # allowed direct casts (for others, you need several casts):
    # * adding one flag
    curflags = CURTYPE.flags
    newflags = PTRTYPE.flags
    if len(curflags) + 1 == len(newflags):
        for key in curflags:
            if key not in newflags or curflags[key] != newflags[key]:
                raise InvalidCast(CURTYPE, PTRTYPE)
    # * removing one flag
    elif len(curflags) - 1 == len(newflags):
        for key in newflags:
            if key not in curflags or curflags[key] != newflags[key]:
                raise InvalidCast(CURTYPE, PTRTYPE)
    # end
    else:
        raise InvalidCast(CURTYPE, PTRTYPE)
    return _ptr(PTRTYPE, ptr._obj)

def cast_parent(PTRTYPE, ptr):
    if not isinstance(ptr, _ptr) or not isinstance(PTRTYPE, _PtrType):
        raise TypeError, "can only cast pointers to other pointers"
    CURTYPE = ptr._TYPE
    if CURTYPE.flags != PTRTYPE.flags:
        raise TypeError("cast_parent() cannot change the flags (%s) to (%s)"
                        % (CURTYPE._str_flags(), PTRTYPE._str_flags()))
    # * converting from TO-structure to a parent TO-structure whose first
    #     field is the original structure
    if (not isinstance(CURTYPE.TO, Struct) or
        not isinstance(PTRTYPE.TO, Struct)):
        raise InvalidCast(CURTYPE, PTRTYPE)
    ptr._check()
    parent = ptr._obj._wrparent()
    PARENTTYPE = ptr._obj._wrparent_type
    if getattr(parent, PARENTTYPE._names[0]) is not ptr._obj:
        raise InvalidCast(CURTYPE, PTRTYPE)
    return _ptr(PTRTYPE, parent)


def _TmpPtr(TO):
    return _PtrType(TO, _tmp=True)

def _expose(val, can_have_gc=False):
    """XXX A nice docstring here"""
    T = typeOf(val)
    if isinstance(T, ContainerType):
        if can_have_gc and isinstance(T, Struct):
            val = _ptr(GcPtr(T), val)
        else:
            val = _ptr(_TmpPtr(T), val)
    return val


class _ptr(object):

    def __init__(self, TYPE, pointing_to):
        self.__dict__['_TYPE'] = TYPE
        self.__dict__['_T'] = TYPE.TO
        self.__dict__['_obj'] = pointing_to

    def __eq__(self, other):
        if not isinstance(other, _ptr):
            raise TypeError("comparing pointer with %r object" % (
                type(other).__name__,))
        if self._TYPE != other._TYPE:
            raise TypeError("comparing %r and %r" % (self._TYPE, other._TYPE))
        return self._obj is other._obj

    def __ne__(self, other):
        return not (self == other)

    def __nonzero__(self):
        return self._obj is not None

    def _check(self):
        if self._obj is None:
            raise RuntimeError("dereferencing 'NULL' pointer to %r" % (self._T,))
        self._obj._check()

    def __getattr__(self, field_name): # ! can only return basic or ptr !
        if isinstance(self._T, Struct):
            if field_name in self._T._flds:
                self._check()
                o = getattr(self._obj, field_name)
                can_have_gc = (field_name == self._T._names[0] and
                               'gc' in self._TYPE.flags)
                return _expose(o, can_have_gc)
        raise AttributeError("%r instance has no field %r" % (self._T,
                                                              field_name))

    def __setattr__(self, field_name, val):
        if isinstance(self._T, Struct):
            if field_name in self._T._flds:
                T1 = self._T._flds[field_name]
                T2 = typeOf(val)
                if T1 != T2:
                    raise TypeError("%r instance field %r:\n"
                                    "expects %r\n"
                                    "    got %r" % (self._T, field_name, T1, T2))
                self._check()
                setattr(self._obj, field_name, val)
                return
        raise AttributeError("%r instance has no field %r" % (self._T,
                                                              field_name))

    def __getitem__(self, i): # ! can only return basic or ptr !
        if isinstance(self._T, Array):
            self._check()
            if not (0 <= i < len(self._obj.items)):
                raise IndexError("array index out of bounds")
            o = self._obj.items[i]
            return _expose(o)
        raise TypeError("%r instance is not an array" % (self._T,))

    def __setitem__(self, i, val): # ! not allowed !
        if isinstance(self._T, Array):
            raise TypeError("cannot directly assign to array items")
        raise TypeError("%r instance is not an array" % (self._T,))

    def __len__(self):
        if isinstance(self._T, Array):
            self._check()
            return len(self._obj.items)
        raise TypeError("%r instance is not an array" % (self._T,))

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return '%s to %s' % (self._TYPE.__class__.__name__.lower(), self._obj)


class _struct(object):
    _wrparent = None

    def __init__(self, TYPE, n=None, parent=None):
        self._TYPE = TYPE
        if n is not None and TYPE._arrayfld is None:
            raise TypeError("%r is not variable-sized" % (TYPE,))
        if n is None and TYPE._arrayfld is not None:
            raise TypeError("%r is variable-sized" % (TYPE,))
        for fld, typ in TYPE._flds.items():
            if isinstance(typ, Struct):
                value = _struct(typ, parent=self)
            elif fld == TYPE._arrayfld:
                value = _array(typ, n)
            else:
                value = typ._defl()
            setattr(self, fld, value)
        if parent is not None:
            self._wrparent_type = typeOf(parent)
            self._wrparent = weakref.ref(parent)

    def _check(self):
        if self._wrparent is not None:
            if self._wrparent() is None:
                raise RuntimeError("accessing substructure %r,\n"
                                   "but already garbage collected parent %r"
                                   % (self, self._wrparent_type))

    def __repr__(self):
        return '<%s>' % (self,)

    def _str_fields(self):
        fields = []
        for name in self._TYPE._names:
            T = self._TYPE._flds[name]
            if isinstance(T, Primitive):
                reprvalue = repr(getattr(self, name))
            else:
                reprvalue = '...'
            fields.append('%s=%s' % (name, reprvalue))
        return ', '.join(fields)

    def __str__(self):
        return 'struct %s { %s }' % (self._TYPE._name, self._str_fields())


class _array(object):
    _wrparent = None

    def __init__(self, TYPE, n, parent=None):
        if not isinstance(n, int):
            raise TypeError, "array length must be an int"
        if n < 0:
            raise ValueError, "negative array length"
        self._TYPE = TYPE
        self.items = [TYPE.OF._defl() for j in range(n)]
        if parent is not None:
            self._wrparent_type = typeOf(parent)
            self._wrparent = weakref.ref(parent)

    def _check(self):
        if self._wrparent is not None:
            if self._wrparent() is None:
                raise RuntimeError("accessing subarray %r,\n"
                                   "but already garbage collected parent %r"
                                   % (self, self._wrparent_type))

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return 'array [ %s ]' % (', '.join(['{%s}' % item._str_fields()
                                            for item in self.items]),)


def malloc(T, n=None):
    if isinstance(T, Struct):
        o = _struct(T, n)
    elif isinstance(T, Array):
        o = _array(T, n)
    else:
        raise TypeError, "malloc for Structs and Arrays only"
    return _ptr(GcPtr(T), o)

# ____________________________________________________________

def test_me():
    S0 = Struct("s0", ('a', Signed), ('b', Signed))
    assert S0.a == Signed
    assert S0.b == Signed
    s0 = malloc(S0)
    print s0
    assert typeOf(s0) == GcPtr(S0)
    assert s0.a == 0
    assert s0.b == 0
    assert typeOf(s0.a) == Signed
    s0.a = 1
    s0.b = s0.a
    assert s0.a == 1
    assert s0.b == 1
    # simple array
    Ar = Array(('v', Signed))
    x = malloc(Ar,0)
    print x
    assert len(x) == 0
    x = malloc(Ar,3)
    print x
    assert typeOf(x) == GcPtr(Ar)
    assert typeOf(x[0]) == _TmpPtr(Ar.OF)
    assert typeOf(x[0].v) == Signed
    assert x[0].v == 0
    x[0].v = 1
    x[1].v = 2
    x[2].v = 3
    assert [x[z].v for z in range(3)] == [1, 2, 3]
    #
    def define_list(T):
        List_typ = Struct("list",
                ("items", GcPtr(Array(('item',T)))))
        def newlist():
            l = malloc(List_typ)
            items = malloc(List_typ.items.TO, 0)
            l.items = items
            return l

        def append(l, newitem):
            length = len(l.items)
            newitems = malloc(List_typ.items.TO, length+1)
            i = 0
            while i<length:
              newitems[i].item = l.items[i].item
              i += 1
            newitems[length].item = newitem
            l.items = newitems

        def item(l, i):
            return l.items[i].item

        return List_typ, newlist, append, item

    List_typ, inewlist, iappend, iitem = define_list(Signed)

    l = inewlist()
    assert typeOf(l) == GcPtr(List_typ)
    iappend(l, 2)
    iappend(l, 3)
    assert len(l.items) == 2
    assert iitem(l, 0) == 2
    assert iitem(l, 1) == 3

    IWrap = Struct("iwrap", ('v', Signed))
    List_typ, iwnewlist, iwappend, iwitem = define_list(GcPtr(IWrap))

    l = iwnewlist()
    assert typeOf(l) == GcPtr(List_typ)
    iw2 = malloc(IWrap)
    iw3 = malloc(IWrap)
    iw2.v = 2
    iw3.v = 3
    assert iw3.v == 3
    iwappend(l, iw2)
    iwappend(l, iw3)
    assert len(l.items) == 2
    assert iwitem(l, 0).v == 2
    assert iwitem(l, 1).v == 3

    # not allowed
    List_typ, iwnewlistzzz, iwappendzzz, iwitemzzz = define_list(IWrap) # works but
    l = iwnewlistzzz()
    py.test.raises(TypeError, "iwappendzzz(l, malloc(IWrap))")

def test_varsizestruct():
    S1 = Struct("s1", ('a', Signed), ('rest', Array(('v', Signed))))
    py.test.raises(TypeError, "malloc(S1)")
    s1 = malloc(S1, 4)
    assert s1.a == 0
    assert typeOf(s1.rest) == _TmpPtr(S1.rest)
    assert len(s1.rest) == 4
    assert typeOf(s1.rest[0]) == _TmpPtr(S1.rest.OF)
    assert typeOf(s1.rest[0].v) == Signed
    assert s1.rest[0].v == 0
    py.test.raises(IndexError, "s1.rest[4]")
    py.test.raises(IndexError, "s1.rest[-1]")

    s1.a = 17
    s1.rest[3].v = 5
    assert s1.a == 17
    assert s1.rest[3].v == 5

    py.test.raises(TypeError, "Struct('invalid', ('rest', Array(('v', Signed))), ('a', Signed))")

def test_substructure_ptr():
    S2 = Struct("s2", ('a', Signed))
    S1 = Struct("s1", ('sub1', S2), ('sub2', S2))
    p1 = malloc(S1)
    assert typeOf(p1.sub1) == GcPtr(S2)
    assert typeOf(p1.sub2) == _TmpPtr(S2)

def test_tagged_pointer():
    S1 = Struct("s1", ('a', Signed), ('b', Unsigned))
    PList = [
        GcPtr(S1),
        NonGcPtr(S1),
        GcPtr(S1, mytag=True),
        NonGcPtr(S1, mytag=True),
        GcPtr(S1, myothertag=True),
        ]
    for P1 in PList:
        for P2 in PList:
            assert (P1 == P2) == (P1 is P2)
    assert PList[2] == GcPtr(S1, mytag=True)

def test_cast_flags():
    S1 = Struct("s1", ('a', Signed), ('b', Unsigned))
    p1 = malloc(S1)
    p2 = cast_flags(NonGcPtr(S1), p1)
    assert typeOf(p2) == NonGcPtr(S1)
    p3 = cast_flags(GcPtr(S1), p2)
    assert typeOf(p3) == GcPtr(S1)
    assert p1 == p3
    py.test.raises(TypeError, "p1 == p2")
    py.test.raises(TypeError, "p2 == p3")

    PT = GcPtr(S1, mytag=True)
    p2 = cast_flags(PT, p1)
    assert typeOf(p2) == PT
    p3 = cast_flags(GcPtr(S1), p2)
    assert typeOf(p3) == GcPtr(S1)
    assert p1 == p3
    py.test.raises(TypeError, "p1 == p2")
    py.test.raises(TypeError, "p2 == p3")

def test_cast_parent():
    S2 = Struct("s2", ('a', Signed))
    S1 = Struct("s1", ('sub1', S2), ('sub2', S2))
    p1 = malloc(S1)
    p2 = p1.sub1
    assert typeOf(p2) == GcPtr(S2)
    p3 = cast_parent(GcPtr(S1), p2)
    assert typeOf(p3) == GcPtr(S1)
    assert p3 == p1
    py.test.raises(TypeError, "cast_parent(GcPtr(S1), p1.sub2)")
    py.test.raises(TypeError, "cast_parent(_TmpPtr(S1), p1.sub2)")
