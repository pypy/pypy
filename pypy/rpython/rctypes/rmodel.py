from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.error import TyperError
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.annotation.model import SomeCTypesObject
from pypy.annotation.pairtype import pairtype


class CTypesRepr(Repr):
    "Base class for the Reprs representing ctypes object."

    # Attributes that are types:
    #
    #  * 'ctype'        is the ctypes type.
    #
    #  * 'll_type'      is the low-level type representing the raw C data,
    #                   like Signed or Array(...).
    #
    #  * 'c_data_type'  is a low-level container type that also represents
    #                   the raw C data; the difference is that we can take
    #                   an lltype pointer to it.  For primitives or pointers
    #                   this is a FixedSizeArray with a single item of
    #                   type 'll_type'.  Otherwise, c_data_type == ll_type.
    #
    #  * 'lowleveltype' is the Repr's choosen low-level type for the RPython
    #                   variables.  It's a Ptr to a GcStruct.  This is a box
    #                   traked by our GC around the raw 'c_data_type'-shaped
    #                   data.
    #
    #  * 'r_memoryowner.lowleveltype' is the lowleveltype of the repr for the
    #                                 same ctype but for ownsmemory=True.

    def __init__(self, rtyper, s_ctypesobject, ll_type):
        # s_ctypesobject: the annotation to represent
        # ll_type: the low-level type representing the raw
        #          data, which is then embedded in a box.
        ctype = s_ctypesobject.knowntype

        self.rtyper = rtyper
        self.ctype = ctype
        self.ll_type = ll_type
        self.ownsmemory = s_ctypesobject.ownsmemory

        self.c_data_type = self.get_c_data_type(ll_type)

        fields = []
        content_keepalive_type = self.get_content_keepalive_type()
        if content_keepalive_type:
            fields.append(( "keepalive", content_keepalive_type ))

        if self.ownsmemory:
            self.r_memoryowner = self
            fields.append(( "c_data", self.c_data_type ))
        else:
            s_memoryowner = SomeCTypesObject(ctype, ownsmemory=True)
            self.r_memoryowner = rtyper.getrepr(s_memoryowner)
            fields += [
                ( "c_data_owner_keepalive", self.r_memoryowner.lowleveltype ),
                ( "c_data", lltype.Ptr(self.c_data_type) ),
                ]
        self.lowleveltype = lltype.Ptr(
                lltype.GcStruct( "CtypesBox_%s" % (ctype.__name__,),
                    *fields
                )
            )
        self.const_cache = {} # store generated const values+original value

    def get_content_keepalive_type(self):
        """Return the type of the extra keepalive field used for the content
        of this object."""
        return None

    def ctypecheck(self, value):
        return isinstance(value, self.ctype)

    def convert_const(self, value):
        if self.ctypecheck(value):
            key = "by_id", id(value)
            keepalive = value
        else:
            if self.ownsmemory:
                raise TyperError("convert_const(%r) but repr owns memory" % (
                    value,))
            key = "by_value", value
            keepalive = None
        try:
            return self.const_cache[key][0]
        except KeyError:
            self.setup()
            p = lltype.malloc(self.r_memoryowner.lowleveltype.TO, zero=True)
            self.initialize_const(p, value)
            if self.ownsmemory:
                result = p
            else:
                # we must return a non-memory-owning box that keeps the
                # memory-owning box alive
                result = lltype.malloc(self.lowleveltype.TO, zero=True)
                result.c_data = p.c_data    # initialize c_data pointer
                result.c_data_owner_keepalive = p
            self.const_cache[key] = result, keepalive
            return result

    def get_c_data(self, llops, v_box):
        if self.ownsmemory:
            inputargs = [v_box, inputconst(lltype.Void, "c_data")]
            return llops.genop('getsubstruct', inputargs,
                        lltype.Ptr(self.c_data_type) )
        else:
            inputargs = [v_box, inputconst(lltype.Void, "c_data")]
            return llops.genop('getfield', inputargs,
                        lltype.Ptr(self.c_data_type) )

    def get_c_data_owner(self, llops, v_box):
        if self.ownsmemory:
            return v_box
        else:
            inputargs = [v_box, inputconst(lltype.Void,
                                           "c_data_owner_keepalive")]
            return llops.genop('getfield', inputargs,
                               self.r_memoryowner.lowleveltype)

    def allocate_instance(self, llops):
        TYPE = self.lowleveltype.TO
        if TYPE._is_varsize():
            raise TyperError("allocating array with unknown length")
        c1 = inputconst(lltype.Void, TYPE)
        cflags = inputconst(lltype.Void, {'flavor': 'gc', 'zero': True})
        return llops.genop("malloc", [c1, cflags], resulttype=self.lowleveltype)

    def allocate_instance_varsize(self, llops, v_length):
        TYPE = self.lowleveltype.TO
        if not TYPE._is_varsize():
            raise TyperError("allocating non-array with a specified length")
        c1 = inputconst(lltype.Void, TYPE)
        cflags = inputconst(lltype.Void, {'flavor': 'gc', 'zero': True})
        return llops.genop("malloc_varsize", [c1, cflags, v_length],
                           resulttype=self.lowleveltype)

    def allocate_instance_ref(self, llops, v_c_data, v_c_data_owner=None):
        """Only if self.ownsmemory is false.  This allocates a new instance
        and initialize its c_data pointer."""
        if self.ownsmemory:
            raise TyperError("allocate_instance_ref: %r owns its memory" % (
                self,))
        v_box = self.allocate_instance(llops)
        inputargs = [v_box, inputconst(lltype.Void, "c_data"), v_c_data]
        llops.genop('setfield', inputargs)
        if v_c_data_owner is not None:
            assert (v_c_data_owner.concretetype ==
                    self.r_memoryowner.lowleveltype)
            inputargs = [v_box,
                         inputconst(lltype.Void, "c_data_owner_keepalive"),
                         v_c_data_owner]
            llops.genop('setfield', inputargs)
        return v_box

    def return_c_data(self, llops, v_c_data):
        """Turn a raw C pointer to the data into a memory-alias box.
        Used when the data is returned from an operation or C function call.
        Special-cased in PrimitiveRepr.
        """
        # XXX add v_c_data_owner
        return self.allocate_instance_ref(llops, v_c_data)

    def getkeepalive(self, llops, v_box):
        try:
            TYPE = self.lowleveltype.TO.keepalive
        except AttributeError:
            return None
        else:
            if isinstance(TYPE, lltype.ContainerType):
                TYPE = lltype.Ptr(TYPE)
                opname = 'getsubstruct'
            else:
                opname = 'getfield'
            c_name = inputconst(lltype.Void, 'keepalive')
            return llops.genop(opname, [v_box, c_name],
                               resulttype = TYPE)


class __extend__(pairtype(CTypesRepr, CTypesRepr)):

    def convert_from_to((r_from, r_to), v, llops):
        """Transparent conversion from the memory-owned to the memory-aliased
        version of the same ctypes repr."""
        if (r_from.ctype == r_to.ctype and
            r_from.ownsmemory and not r_to.ownsmemory):
            v_c_data = r_from.get_c_data(llops, v)
            v_result =  r_to.allocate_instance_ref(llops, v_c_data, v)
            # copy of the 'keepalive' field over
            v_keepalive = r_from.getkeepalive(llops, v)
            if v_keepalive is not None:
                genreccopy_structfield(llops, v_keepalive,
                                       v_result, 'keepalive')
            return v_result
        else:
            return NotImplemented


class CTypesRefRepr(CTypesRepr):
    """Base class for ctypes repr that have some kind of by-reference
    semantics, like structures and arrays."""

    def get_c_data_type(self, ll_type):
        assert isinstance(ll_type, lltype.ContainerType)
        return ll_type

    def get_c_data_or_value(self, llops, v_box):
        return self.get_c_data(llops, v_box)


class CTypesValueRepr(CTypesRepr):
    """Base class for ctypes repr that have some kind of by-value
    semantics, like primitives and pointers."""

    def get_c_data_type(self, ll_type):
        return lltype.FixedSizeArray(ll_type, 1)

    def getvalue_from_c_data(self, llops, v_c_data):
        return llops.genop('getarrayitem', [v_c_data, C_ZERO],
                resulttype=self.ll_type)

    def setvalue_inside_c_data(self, llops, v_c_data, v_value):
        llops.genop('setarrayitem', [v_c_data, C_ZERO, v_value])

    def getvalue(self, llops, v_box):
        """Reads from the 'value' field of the raw data."""
        v_c_data = self.get_c_data(llops, v_box)
        return self.getvalue_from_c_data(llops, v_c_data)

    def setvalue(self, llops, v_box, v_value):
        """Writes to the 'value' field of the raw data."""
        v_c_data = self.get_c_data(llops, v_box)
        self.setvalue_inside_c_data(llops, v_c_data, v_value)

    get_c_data_or_value = getvalue

    def initialize_const(self, p, value):
        if self.ctypecheck(value):
            value = value.value
        p.c_data[0] = value

    def return_value(self, llops, v_value):
        # like return_c_data(), but when the input is only the value
        # field instead of the c_data pointer
        r_temp = self.r_memoryowner
        v_owned_box = r_temp.allocate_instance(llops)
        r_temp.setvalue(llops, v_owned_box, v_value)
        return llops.convertvar(v_owned_box, r_temp, self)

    def cast_return_value(self, llops, v_value):
        # like return_value(), but used for the cast function
        return self.return_value(llops, v_value)

    def rtype_is_true(self, hop):
        [v_box] = hop.inputargs(self)
        v_value = self.getvalue(hop.llops, v_box)
        return hop.gendirectcall(ll_is_true, v_value)

# ____________________________________________________________

def ll_is_true(x):
    return bool(x)

C_ZERO = inputconst(lltype.Signed, 0)

def reccopy(source, dest):
    # copy recursively a structure or array onto another.
    T = lltype.typeOf(source).TO
    assert T == lltype.typeOf(dest).TO
    if isinstance(T, (lltype.Array, lltype.FixedSizeArray)):
        assert source._obj.getlength() == dest._obj.getlength()
        ITEMTYPE = T.OF
        for i in range(source._obj.getlength()):
            if isinstance(ITEMTYPE, lltype.ContainerType):
                subsrc = source[i]
                subdst = dest[i]
                reccopy(subsrc, subdst)
            else:
                # this is a hack XXX de-hack this
                llvalue = source._obj.getitem(i, uninitialized_ok=True)
                dest._obj.setitem(i, llvalue)
    elif isinstance(T, lltype.Struct):
        for name in T._names:
            FIELDTYPE = getattr(T, name)
            if isinstance(FIELDTYPE, lltype.ContainerType):
                subsrc = getattr(source, name)
                subdst = getattr(dest,   name)
                reccopy(subsrc, subdst)
            else:
                # this is a hack XXX de-hack this
                llvalue = source._obj._getattr(name, uninitialized_ok=True)
                setattr(dest._obj, name, llvalue)
    else:
        raise TypeError(T)

def reccopy_arrayitem(source, destarray, destindex):
    ITEMTYPE = lltype.typeOf(destarray).TO.OF
    if isinstance(ITEMTYPE, lltype.Primitive):
        destarray[destindex] = source
    else:
        reccopy(source, destarray[destindex])

def genreccopy(llops, v_source, v_dest):
    # helper to generate the llops that copy recursively a structure
    # or array onto another.  'v_source' and 'v_dest' can also be pairs
    # (v, i) to mean the ith item of the array that v points to.
    T = v_source.concretetype.TO
    assert T == v_dest.concretetype.TO

    if isinstance(T, lltype.FixedSizeArray):
        # XXX don't do that if the length is large
        ITEMTYPE = T.OF
        for i in range(T.length):
            c_i = inputconst(lltype.Signed, i)
            if isinstance(ITEMTYPE, lltype.ContainerType):
                RESTYPE = lltype.Ptr(ITEMTYPE)
                v_subsrc = llops.genop('getarraysubstruct', [v_source, c_i],
                                       resulttype = RESTYPE)
                v_subdst = llops.genop('getarraysubstruct', [v_dest,   c_i],
                                       resulttype = RESTYPE)
                genreccopy(llops, v_subsrc, v_subdst)
            else:
                v_value = llops.genop('getarrayitem', [v_source, c_i],
                                      resulttype = ITEMTYPE)
                llops.genop('setarrayitem', [v_dest, c_i, v_value])

    elif isinstance(T, lltype.Array):
        raise NotImplementedError("XXX genreccopy() for arrays")

    elif isinstance(T, lltype.Struct):
        for name in T._names:
            FIELDTYPE = getattr(T, name)
            cname = inputconst(lltype.Void, name)
            if isinstance(FIELDTYPE, lltype.ContainerType):
                RESTYPE = lltype.Ptr(FIELDTYPE)
                v_subsrc = llops.genop('getsubstruct', [v_source, cname],
                                       resulttype = RESTYPE)
                v_subdst = llops.genop('getsubstruct', [v_dest,   cname],
                                       resulttype = RESTYPE)
                genreccopy(llops, v_subsrc, v_subdst)
            else:
                v_value = llops.genop('getfield', [v_source, cname],
                                      resulttype = FIELDTYPE)
                llops.genop('setfield', [v_dest, cname, v_value])

    else:
        raise TypeError(T)

def genreccopy_arrayitem(llops, v_source, v_destarray, v_destindex):
    ITEMTYPE = v_destarray.concretetype.TO.OF
    if isinstance(ITEMTYPE, lltype.ContainerType):
        v_dest = llops.genop('getarraysubstruct', [v_destarray, v_destindex],
                             resulttype = lltype.Ptr(ITEMTYPE))
        genreccopy(llops, v_source, v_dest)
    else:
        llops.genop('setarrayitem', [v_destarray, v_destindex, v_source])

def genreccopy_structfield(llops, v_source, v_deststruct, fieldname):
    c_name = inputconst(lltype.Void, fieldname)
    FIELDTYPE = getattr(v_deststruct.concretetype.TO, fieldname)
    if isinstance(FIELDTYPE, lltype.ContainerType):
        v_dest = llops.genop('getsubstruct', [v_deststruct, c_name],
                             resulttype = lltype.Ptr(FIELDTYPE))
        genreccopy(llops, v_source, v_dest)
    else:
        llops.genop('setfield', [v_deststruct, c_name, v_source])
