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

class RawMemSubBlock(object):
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
                return allocate_object(cls, cls.num_keepalives, cls.rawsize)
            cls.allocate = staticmethod(allocate1)

            def copyfrom1(self, srcbox):
                assert isinstance(srcbox, cls)
                llmemory.raw_memcopy(srcbox.addr, self.addr, cls.rawsize)
                self.copykeepalives(0, srcbox)
            cls.copyfrom = copyfrom1

    def sameaddr(self, otherbox):
        return self.addr == otherbox.addr

    def keepalivememblock(self, index, memblock):
        self.memblock.setkeepalive(index, memblock)

    def copykeepalives(self, startindex, srcbox):
        for i in range(self.num_keepalives):
            memblock = srcbox.memblock.getkeepalive(startindex + i)
            self.memblock.setkeepalive(i, memblock)

    def getmemblock(self, index, target_num_keepalives):
        targetmemblock = self.memblock.getkeepalive(index)
        if targetmemblock is None:
            targetmemblock = RawMemBlock(target_num_keepalives)
            self.memblock.setkeepalive(index, targetmemblock)
        return targetmemblock

    def ll_ref(self, CDATATYPE):
        return llmemory.cast_adr_to_ptr(self.addr, lltype.Ptr(CDATATYPE))


def allocate_object(cls, num_keepalives, rawsize):
    memblock = AllocatedRawMemBlock(num_keepalives, rawsize)
    return cls(memblock.addr, memblock)


_primitive_cache = {}
def makePrimitive(TYPE):
    """Build a return a new RCTypesPrimitive class."""
    try:
        return _primitive_cache[TYPE]
    except KeyError:
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
rc_int = makePrimitive(lltype.Signed)
rc_char = makePrimitive(lltype.Char)


def makeRPointer(contentscls):
    """Build and return a new RCTypesPointer class."""
    try:
        return contentscls._ptrcls
    except AttributeError:
        assert issubclass(contentscls, RCTypesObject)

        class RCTypesPtr(RCTypesObject):
            CONTENTS  = contentscls.CDATATYPE
            LLTYPE    = lltype.Ptr(CONTENTS)
            num_keepalives = 1

            def get_contents(self):
                ptr = self.ll_ref(RCTypesPtr.CDATATYPE)
                targetaddr = llmemory.cast_ptr_to_adr(ptr[0])
                targetkeepalives = contentscls.num_keepalives
                targetmemblock = self.getmemblock(0, targetkeepalives)
                return contentscls(targetaddr, targetmemblock)

            def set_contents(self, newcontentsbox):
                targetaddr = newcontentsbox.addr
                targetmemblock = newcontentsbox.memblock
                ptr = self.ll_ref(RCTypesPtr.CDATATYPE)
                ptr[0] = llmemory.cast_adr_to_ptr(targetaddr,
                                                  RCTypesPtr.LLTYPE)
                self.keepalivememblock(0, targetmemblock)

        contentscls._ptrcls = RCTypesPtr
        return RCTypesPtr
makeRPointer._annspecialcase_ = 'specialize:memo'

def pointer(x):
    PTR = makeRPointer(x.__class__)
    p = PTR.allocate()
    p.set_contents(x)
    return p
pointer._annspecialcase_ = 'specialize:argtype(0)'


def makeRStruct(c_name, fields, c_external=False):
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
