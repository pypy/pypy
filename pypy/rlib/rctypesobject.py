from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.interpreter.miscutils import InitializedClass
from pypy.tool.sourcetools import func_with_new_name


class RawMemBlock(object):
    ofs_keepalives = 0
    def __init__(self, num_keepalives):
        self.keepalives = [None] * num_keepalives  # list of RawMemBlocks
    def addoffset(self, ofs_keepalives):
        if ofs_keepalives == 0:
            return self
        else:
            return self._addoffset(ofs_keepalives)
    def _addoffset(self, ofs_keepalives):
        return RawMemSubBlock(self, ofs_keepalives)
    def getkeepalive(self, index):
        return self.keepalives[self.ofs_keepalives + index]
    def setkeepalive(self, index, memblock):
        self.keepalives[self.ofs_keepalives + index] = memblock

class AllocatedRawMemBlock(RawMemBlock):
    def __init__(self, num_keepalives, rawsize):
        RawMemBlock.__init__(self, num_keepalives)
        addr = llmemory.raw_malloc(rawsize)
        self.addr = addr
        llmemory.raw_memclear(addr, rawsize)
        #print 'raw_malloc:', addr
    def __del__(self):
        #print 'raw_free:  ', self.addr
        llmemory.raw_free(self.addr)

class RawMemSubBlock(RawMemBlock):
    def __init__(self, baseblock, ofs_keepalives):
        self.baseblock = baseblock
        self.keepalives = baseblock.keepalives
        self.ofs_keepalives = ofs_keepalives
    def _addoffset(self, ofs_keepalives):
        ofs_keepalives = self.ofs_keepalives + ofs_keepalives
        return RawMemSubBlock(self.baseblock, ofs_keepalives)


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

    def sameaddr(self, otherbox):
        return self.addr == otherbox.addr

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
        return llmemory.cast_adr_to_ptr(self.addr, lltype.Ptr(CDATATYPE))
    ll_ref._annspecialcase_ = 'specialize:arg(1)'


_primitive_cache = {}
def Primitive(TYPE):
    """Build a return a new RCTypesPrimitive class."""
    try:
        return _primitive_cache[TYPE]
    except KeyError:
        assert not isinstance(TYPE, lltype.ContainerType)

        class RCTypesPrimitive(RCTypesObject):
            LLTYPE = TYPE

            def get_value(self):
                ptr = self.ll_ref(RCTypesPrimitive.CDATATYPE)
                return ptr[0]

            def set_value(self, llvalue):
                ptr = self.ll_ref(RCTypesPrimitive.CDATATYPE)
                ptr[0] = llvalue

        _primitive_cache[TYPE] = RCTypesPrimitive
        return RCTypesPrimitive

# a few prebuilt primitive types
rc_int = Primitive(lltype.Signed)
rc_char = Primitive(lltype.Char)


class _RCTypesStringData(object):
    ARRAYTYPE    = lltype.Array(lltype.Char, hints={'nolength': True})
    FIRSTITEMOFS = llmemory.ArrayItemsOffset(ARRAYTYPE)
    ITEMOFS      = llmemory.sizeof(lltype.Char)
    
    def __init__(self, string):
        rawsize = self.FIRSTITEMOFS + self.ITEMOFS * (len(string) + 1)
        self.addr = llmemory.raw_malloc(rawsize)
        a = self.addr + self.FIRSTITEMOFS
        for i in range(len(string)):
            a.char[0] = string[i]
            a += self.ITEMOFS
        a.char[0] = '\x00'
    def __del__(self):
        llmemory.raw_free(self.addr)

class RCTypesCharP(RCTypesObject):
    LLTYPE = lltype.Ptr(_RCTypesStringData.ARRAYTYPE)

    def strlen(self):
        ptr = self.ll_ref(RCTypesCharP.CDATATYPE)
        a = ptr[0]
        n = 0
        while a[n] != '\x00':
            n += 1
        return n

    def get_value(self):
        length = self.strlen()
        ptr = self.ll_ref(RCTypesCharP.CDATATYPE)
        a = ptr[0]
        lst = ['\x00'] * length
        for i in range(length):
            lst[i] = a[i]
        return ''.join(lst)

    def set_value(self, string):
        data = _RCTypesStringData(string)
        ptr = self.ll_ref(RCTypesCharP.CDATATYPE)
        ptr[0] = llmemory.cast_adr_to_ptr(data.addr, RCTypesCharP.LLTYPE)
        self._keepalive_stringdata = data

rc_char_p = RCTypesCharP


def RPointer(contentscls):
    """Build and return a new RCTypesPointer class."""
    try:
        return contentscls._ptrcls
    except AttributeError:
        assert issubclass(contentscls, RCTypesObject)
        if contentscls is RCTypesObject:
            raise Exception("cannot call RPointer(RCTypesObject) or "
                            "pointer(x) if x degenerated to the base "
                            "RCTypesObject class")

        class RCTypesPtr(RCTypesObject):
            CONTENTS  = contentscls.CDATATYPE
            LLTYPE    = lltype.Ptr(CONTENTS)
            num_keepalives = 1

            def get_contents(self):
                ptr = self.ll_ref(RCTypesPtr.CDATATYPE)
                targetaddr = llmemory.cast_ptr_to_adr(ptr[0])
                targetkeepalives = contentscls.num_keepalives
                targetmemblock = self._getmemblock(0, targetkeepalives)
                return contentscls(targetaddr, targetmemblock)

            def set_contents(self, newcontentsbox):
                targetaddr = newcontentsbox.addr
                targetmemblock = newcontentsbox.memblock
                ptr = self.ll_ref(RCTypesPtr.CDATATYPE)
                ptr[0] = llmemory.cast_adr_to_ptr(targetaddr,
                                                  RCTypesPtr.LLTYPE)
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


def RFixedArray(itemcls, fixedsize):
    """Build and return a new RCTypesFixedArray class."""

    key = '_fixedarraycls%d' % (fixedsize,)
    try:
        return getattr(itemcls, key)
    except AttributeError:
        assert issubclass(itemcls, RCTypesObject)
        if itemcls is RCTypesObject:
            raise Exception("cannot call RFixedArray(RCTypesObject)")

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
        if itemcls is RCTypesObject:
            raise Exception("cannot call RVarArray(RCTypesObject)")

        ARRAYTYPE = lltype.Array(itemcls.LLTYPE, hints={'nolength': True})
        FIRSTITEMOFS = llmemory.ArrayItemsOffset(ARRAYTYPE)
        ITEMOFS      = llmemory.sizeof(itemcls.LLTYPE)

        class RCTypesVarArray(object):
            ITEM = ARRAYTYPE.OF

            def __init__(self, addr, memblock, length):
                self.addr = addr
                self.memblock = memblock
                self.length = length

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

        itemcls._vararraycls = RCTypesVarArray
        return RCTypesVarArray
RVarArray._annspecialcase_ = 'specialize:memo'
