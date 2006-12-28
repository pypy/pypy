from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython import annlowlevel
from pypy.interpreter.miscutils import InitializedClass
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.objectmodel import keepalive_until_here


class RawMemBlock(object):
    ofs_keepalives = 0
    def __init__(self, num_keepalives):
        self.keepalives = [None] * num_keepalives  # list of RawMemBlocks
    def addoffset(self, ofs_keepalives):
        if ofs_keepalives == 0:
            return self
        else:
            return RawMemSubBlock(self, ofs_keepalives)
##            return self._addoffset(ofs_keepalives)
##    def _addoffset(self, ofs_keepalives):
##        return RawMemSubBlock(self, ofs_keepalives)
    def getkeepalive(self, index):
        return self.keepalives[self.ofs_keepalives + index]
    def setkeepalive(self, index, memblock):
        self.keepalives[self.ofs_keepalives + index] = memblock

EMPTY_RAW_MEM_BLOCK = RawMemBlock(0)

class AllocatedRawMemBlock(RawMemBlock):
    def __init__(self, num_keepalives, rawsize, zero=True):
        RawMemBlock.__init__(self, num_keepalives)
        addr = llmemory.raw_malloc(rawsize)
        self.addr = addr
        if zero:
            llmemory.raw_memclear(addr, rawsize)
        #print 'raw_malloc: %x' % llmemory.cast_adr_to_int(addr)
    def __del__(self):
        #print 'raw_free:   %x' % llmemory.cast_adr_to_int(self.addr)
        llmemory.raw_free(self.addr)

class RawMemSubBlock(RawMemBlock):
    def __init__(self, baseblock, ofs_keepalives):
        self.baseblock = baseblock
        self.keepalives = baseblock.keepalives
        self.ofs_keepalives = ofs_keepalives
##    def _addoffset(self, ofs_keepalives):
##        ofs_keepalives = self.ofs_keepalives + ofs_keepalives
##        return RawMemSubBlock(self.baseblock, ofs_keepalives)


class RCTypesObject(object):
    __metaclass__ = InitializedClass
    num_keepalives = 0
    __slots__ = ('addr', 'memblock')

    def __init__(self, addr, memblock):
        self.addr = addr
        self.memblock = memblock

    def __initclass__(cls):
        if hasattr(cls, 'LLTYPE'):
            cls.__name__ = 'RCTypes_%s' % (cls.LLTYPE,)
            if not hasattr(cls, 'CDATATYPE'):
                if isinstance(cls.LLTYPE, lltype.ContainerType):
                    cls.CDATATYPE = cls.LLTYPE
                else:
                    cls.CDATATYPE = lltype.FixedSizeArray(cls.LLTYPE, 1)
            if not getattr(cls, 'can_allocate', True):
                return

            if not hasattr(cls, 'rawsize'):
                cls.rawsize = llmemory.sizeof(cls.CDATATYPE)

            def allocate1():
                memblock = AllocatedRawMemBlock(cls.num_keepalives,
                                                cls.rawsize)
                return cls(memblock.addr, memblock)
            cls.allocate = staticmethod(allocate1)

            def copyfrom1(self, srcbox):
                assert isinstance(srcbox, cls)
                llmemory.raw_memcopy(srcbox.addr, self.addr, cls.rawsize)
                self._copykeepalives(0, srcbox)
            cls.copyfrom = copyfrom1

            if hasattr(cls, 'llvalue2value') and not hasattr(cls, 'get_value'):
                def get_value(self):
                    ptr = self.ll_ref(cls.CDATATYPE)
                    res = cls.llvalue2value(ptr[0])
                    keepalive_until_here(self)
                    return res
                cls.get_value = get_value

            if hasattr(cls, 'value2llvalue') and not hasattr(cls, 'set_value'):
                def set_value(self, value):
                    ptr = self.ll_ref(cls.CDATATYPE)
                    ptr[0] = cls.value2llvalue(value)
                    keepalive_until_here(self)
                cls.set_value = set_value

    def sameaddr(self, otherbox):
        return self.addr == otherbox.addr

    def sizeof(self):
        return self.rawsize

    def _keepalivememblock(self, index, memblock):
        self.memblock.setkeepalive(index, memblock)

    def _copykeepalives(self, startindex, srcbox):
        for i in range(self.num_keepalives):
            memblock = srcbox.memblock.getkeepalive(startindex + i)
            self.memblock.setkeepalive(i, memblock)

    def _getmemblock(self, index, target_num_keepalives):
        targetmemblock = self.memblock.getkeepalive(index)
        if targetmemblock is None:
            targetmemblock = RawMemBlock(target_num_keepalives)
            self.memblock.setkeepalive(index, targetmemblock)
        return targetmemblock

    def ll_ref(self, CDATATYPE):
        # Return a ptr to the memory that this object references.
        # WARNING: always use 'keepalive_until_here(self)' when you
        # are done using this ptr!  Otherwise the memory might be
        # deallocated.
        return llmemory.cast_adr_to_ptr(self.addr, lltype.Ptr(CDATATYPE))
    ll_ref._annspecialcase_ = 'specialize:arg(1)'

_abstract_classes = [RCTypesObject]

# ____________________________________________________________

_primitive_cache = {}
def Primitive(TYPE):
    """Build a return a new RCTypesPrimitive class."""
    try:
        return _primitive_cache[TYPE]
    except KeyError:
        assert not isinstance(TYPE, lltype.ContainerType)

        class RCTypesPrimitive(RCTypesObject):
            LLTYPE = TYPE

            def _no_conversion_needed(x):
                return x
            llvalue2value = staticmethod(_no_conversion_needed)
            value2llvalue = staticmethod(_no_conversion_needed)

            #def get_value(self):        added by __initclass__() above
            #def set_value(self, value): added by __initclass__() above

        _primitive_cache[TYPE] = RCTypesPrimitive
        return RCTypesPrimitive

# a few prebuilt primitive types
rc_int = Primitive(lltype.Signed)
rc_char = Primitive(lltype.Char)

# ____________________________________________________________

##class _RCTypesStringData(object):
##    ARRAYTYPE = lltype.FixedSizeArray(lltype.Char, 1)
##    ITEMOFS   = llmemory.sizeof(lltype.Char)
##    def __init__(self, bufsize):
##        rawsize = self.ITEMOFS * bufsize
##        self.addr = llmemory.raw_malloc(rawsize)
##    def __del__(self):
##        llmemory.raw_free(self.addr)

def strlen(p):
    n = 0
    while p[n] != '\x00':
        n += 1
    return n

def strnlen(p, n_max):
    n = 0
    while n < n_max and p[n] != '\x00':
        n += 1
    return n

def charp2string(p, length):
    lst = ['\x00'] * length
    for i in range(length):
        lst[i] = p[i]
    return ''.join(lst)

def string2charp(p, length, string):
    for i in range(length):
        if i < len(string):
            p[i] = string[i]
        else:
            p[i] = '\x00'
            break

class RCTypesCharP(RCTypesObject):
    ARRAYTYPE = lltype.FixedSizeArray(lltype.Char, 1)
    ITEMOFS   = llmemory.sizeof(lltype.Char)
    LLTYPE    = lltype.Ptr(ARRAYTYPE)
    num_keepalives = 1

    def llvalue2value(p):
        length = strlen(p)
        return charp2string(p, length)
    llvalue2value = staticmethod(llvalue2value)

    #def get_value(self): added by __initclass__() above

    def set_value(self, string):
        n = len(string)
        rawsize = RCTypesCharP.ITEMOFS * (n + 1)
        targetmemblock = AllocatedRawMemBlock(0, rawsize, zero=False)
        targetaddr = targetmemblock.addr
        a = targetaddr
        for i in range(n):
            a.char[0] = string[i]
            a += RCTypesCharP.ITEMOFS
        a.char[0] = '\x00'
        ptr = self.ll_ref(RCTypesCharP.CDATATYPE)
        ptr[0] = llmemory.cast_adr_to_ptr(targetaddr, RCTypesCharP.LLTYPE)
        keepalive_until_here(self)
        self._keepalivememblock(0, targetmemblock)

rc_char_p = RCTypesCharP

# ____________________________________________________________

def RPointer(contentscls):
    """Build and return a new RCTypesPointer class."""
    try:
        return contentscls._ptrcls
    except AttributeError:
        assert issubclass(contentscls, RCTypesObject)
        if contentscls in _abstract_classes:
            raise Exception("cannot call RPointer(%s) or "
                            "pointer(x) if x degenerated to the base "
                            "%s class" % (contentscls.__name__,
                                          contentscls.__name__,))

        class RCTypesPtr(RCTypesObject):
            CONTENTS  = contentscls.CDATATYPE
            LLTYPE    = lltype.Ptr(CONTENTS)
            num_keepalives = 1

            def get_contents(self):
                ptr = self.ll_ref(RCTypesPtr.CDATATYPE)
                targetaddr = llmemory.cast_ptr_to_adr(ptr[0])
                keepalive_until_here(self)
                targetkeepalives = contentscls.num_keepalives
                targetmemblock = self._getmemblock(0, targetkeepalives)
                return contentscls(targetaddr, targetmemblock)

            def set_contents(self, newcontentsbox):
                targetaddr = newcontentsbox.addr
                targetmemblock = newcontentsbox.memblock
                ptr = self.ll_ref(RCTypesPtr.CDATATYPE)
                ptr[0] = llmemory.cast_adr_to_ptr(targetaddr,
                                                  RCTypesPtr.LLTYPE)
                keepalive_until_here(self)
                self._keepalivememblock(0, targetmemblock)

        contentscls._ptrcls = RCTypesPtr
        return RCTypesPtr
RPointer._annspecialcase_ = 'specialize:memo'

def pointer(x):
    PTR = RPointer(x.__class__)
    p = PTR.allocate()
    p.set_contents(x)
    return p
pointer._annspecialcase_ = 'specialize:argtype(0)'

def sizeof(x):
    return x.sizeof()

# ____________________________________________________________

def RStruct(c_name, fields, c_external=False):
    """Build and return a new RCTypesStruct class."""

    def cmangle(name):
        # obscure: names starting with '_' are not allowed in
        # lltype.Struct, so we prefix all nam4es with 'c_'
        return 'c_' + name

    fieldclasses = {}
    llfields = []
    num_keepalives = 0
    for name, fieldboxcls in fields:
        llname = cmangle(name)
        fieldclasses[name] = llname, fieldboxcls, num_keepalives
        llfields.append((llname, fieldboxcls.LLTYPE))
        num_keepalives += fieldboxcls.num_keepalives

    extras = {'hints': {'c_name': c_name, 'external': c_external}}
    STRUCT = lltype.Struct(c_name, *llfields, **extras)

    class RCTypesStruct(RCTypesObject):
        LLTYPE = STRUCT
    RCTypesStruct.num_keepalives = num_keepalives

    def make_accessors(fieldname):
        llname, fieldboxcls, ofs_keepalives = fieldclasses[fieldname]
        FIELD = fieldboxcls.LLTYPE
        FIELDOFS = llmemory.offsetof(STRUCT, llname)

        def refgetter(self):
            subaddr = self.addr + FIELDOFS
            subblock = self.memblock.addoffset(ofs_keepalives)
            return fieldboxcls(subaddr, subblock)
        setattr(RCTypesStruct, 'ref_' + fieldname, refgetter)

    for name in fieldclasses:
        make_accessors(name)
    return RCTypesStruct

# ____________________________________________________________

def RFixedArray(itemcls, fixedsize):
    """Build and return a new RCTypesFixedArray class."""

    key = '_fixedarraycls%d' % (fixedsize,)
    try:
        return getattr(itemcls, key)
    except AttributeError:
        assert issubclass(itemcls, RCTypesObject)
        if itemcls in _abstract_classes:
            raise Exception("cannot call RFixedArray(%s)" % (
                itemcls.__name__,))

        ARRAYTYPE = lltype.FixedSizeArray(itemcls.LLTYPE, fixedsize)
        FIRSTITEMOFS = llmemory.ArrayItemsOffset(ARRAYTYPE)
        ITEMOFS      = llmemory.sizeof(itemcls.LLTYPE)

        class RCTypesFixedArray(RCTypesObject):
            ITEM   = ARRAYTYPE.OF
            LLTYPE = ARRAYTYPE
            length = fixedsize
            num_keepalives = itemcls.num_keepalives * fixedsize

            def ref(self, n):
                subaddr = self.addr + (FIRSTITEMOFS + ITEMOFS * n)
                subblock = self.memblock.addoffset(itemcls.num_keepalives * n)
                return itemcls(subaddr, subblock)

        if itemcls is rc_char:
            # attach special methods for arrays of chars
            def as_ll_charptr(self):
                ptr = self.ll_ref(ARRAYTYPE)
                return lltype.direct_arrayitems(ptr)
            _initialize_array_of_char(RCTypesFixedArray, as_ll_charptr)

        setattr(itemcls, key, RCTypesFixedArray)
        return RCTypesFixedArray
RFixedArray._annspecialcase_ = 'specialize:memo'


def RVarArray(itemcls):
    """Build and return a new RCTypesVarArray class.
    Note that this is *not* a subclass of RCTypesObject, so you cannot
    take a pointer to it, use it as a field of a structure, etc.
    You can take a pointer to one of its elements (e.g. the first),
    though, and that pointer will keep the whole array alive.
    """
    try:
        return itemcls._vararraycls
    except AttributeError:
        assert issubclass(itemcls, RCTypesObject)
        if itemcls in _abstract_classes:
            raise Exception("cannot call RVarArray(%s)" % (
                itemcls.__name__,))

        ARRAYTYPE = lltype.Array(itemcls.LLTYPE, hints={'nolength': True})
        FIRSTITEMOFS = llmemory.ArrayItemsOffset(ARRAYTYPE)
        ITEMOFS      = llmemory.sizeof(itemcls.LLTYPE)

        class RCTypesVarArray(object):
            ITEM = ARRAYTYPE.OF

            def __init__(self, addr, memblock, length):
                self.addr = addr
                self.memblock = memblock
                self.length = length

            def sizeof(self):
                rawsize = FIRSTITEMOFS + ITEMOFS * self.length
                return rawsize

            def allocate(length):
                rawsize = FIRSTITEMOFS + ITEMOFS * length
                num_keepalives = itemcls.num_keepalives * length
                memblock = AllocatedRawMemBlock(num_keepalives, rawsize)
                addr = memblock.addr + FIRSTITEMOFS
                return RCTypesVarArray(addr, memblock, length)
            allocate = staticmethod(allocate)

            def fromitem(itembox, length):
                """Return a VarArray from a reference to its first element.
                Note that if you use the VarArray to store pointer-ish data,
                you have to keep the VarArray alive as long as you want
                this new data to stay alive.
                """
                assert isinstance(itembox, itemcls)
                num_keepalives = itemcls.num_keepalives * length
                memblock = RawMemBlock(num_keepalives)
                res = RCTypesVarArray(itembox.addr, memblock, length)
                res._keepalive_memblock_fromitem = itembox.memblock
                return res
            fromitem = staticmethod(fromitem)

            def ref(self, n):
                subaddr = self.addr + ITEMOFS * n
                subblock = self.memblock.addoffset(itemcls.num_keepalives * n)
                return itemcls(subaddr, subblock)

        if itemcls is rc_char:
            # attach special methods for arrays of chars
            def as_ll_charptr(self):
                return llmemory.cast_adr_to_ptr(self.addr, RCTypesCharP.LLTYPE)
            _initialize_array_of_char(RCTypesVarArray, as_ll_charptr)

        itemcls._vararraycls = RCTypesVarArray
        return RCTypesVarArray
RVarArray._annspecialcase_ = 'specialize:memo'

# ____________________________________________________________

def _initialize_array_of_char(RCClass, as_ll_charptr):
    # Attach additional methods for fixed- or variable-sized arrays of char

    def get_value(self):
        p = as_ll_charptr(self)
        n = strnlen(p, self.length)
        res = charp2string(p, n)
        keepalive_until_here(self)
        return res

    def set_value(self, string):
        string2charp(as_ll_charptr(self), self.length, string)
        keepalive_until_here(self)

    def get_raw(self):
        res = charp2string(as_ll_charptr(self), self.length)
        keepalive_until_here(self)
        return res

    def get_substring(self, start, length):
        p = lltype.direct_ptradd(as_ll_charptr(self), start)
        res = charp2string(p, length)
        keepalive_until_here(self)
        return res

    RCClass.get_value     = get_value
    RCClass.set_value     = set_value
    RCClass.get_raw       = get_raw
    RCClass.get_substring = get_substring


create_string_buffer = RVarArray(rc_char).allocate

# ____________________________________________________________

_functype_cache = {}
def RFuncType(args_cls, rescls):
    """Build and return a new RCTypesFunc class.
    Note that like lltype, but unlike ctypes, a 'function' type is not
    automatically a pointer to a function.  Conceptually, it represents
    the area of memory where the function's machine code is stored."""
    args_cls = tuple(args_cls)
    try:
        return _functype_cache[args_cls, rescls]
    except KeyError:

        ARGS = [cls.LLTYPE for cls in args_cls]
        RES  = rescls.LLTYPE
        FUNCTYPE = lltype.FuncType(ARGS, RES)
        PTRTYPE  = lltype.Ptr(FUNCTYPE)

        class RCTypesFunc(RCTypesObject):
            LLTYPE = FUNCTYPE
            can_allocate = False

            def fromllptr(p):
                addr = llmemory.cast_ptr_to_adr(p)
                memblock = EMPTY_RAW_MEM_BLOCK
                return RCTypesFunc(addr, memblock)
            fromllptr = staticmethod(fromllptr)

            def fromrpython(func):
                """Return an RCTypes function that references the given
                RPython function."""
                p = annlowlevel.llhelper(PTRTYPE, func)
                return RCTypesFunc.fromllptr(p)
            fromrpython._annspecialcase_ = 'specialize:arg(0)'
            fromrpython = staticmethod(fromrpython)

            def fromlib(rlib, c_funcname, llinterp_friendly_version=None):
                flags = {'external': 'C'}
                if rlib.pythonapi:
                    pass   # no 'includes': hack to trigger
                           # in GenC a PyErr_Occurred() check
                else:
                    flags['includes']  = rlib.c_includes
                    flags['libraries'] = rlib.c_libs
                if llinterp_friendly_version:
                    flags['_callable'] = llinterp_friendly_version
                p = lltype.functionptr(FUNCTYPE, c_funcname, **flags)
                return RCTypesFunc.fromllptr(p)
            fromlib._annspecialcase_ = 'specialize:memo'
            fromlib = staticmethod(fromlib)

            def call(self, *args):
                assert len(args) == len(ARGS)
                p = llmemory.cast_adr_to_ptr(self.addr, PTRTYPE)
                return p(*args)

        _functype_cache[args_cls, rescls] = RCTypesFunc
        return RCTypesFunc
RFuncType._annspecialcase_ = 'specialize:memo'


class RLibrary(object):
    """A C library.  Use to create references to external functions.
    """
    # XXX for now, lltype only supports functions imported from external
    # libraries, not variables

    pythonapi = False

    def __init__(self, c_libs=(), c_includes=()):
        if isinstance(c_libs,     str): c_libs     = (c_libs,)
        if isinstance(c_includes, str): c_includes = (c_includes,)
        self.c_libs = c_libs
        self.c_includes = c_includes

    def _freeze_(self):
        return True

LIBC = RLibrary()
