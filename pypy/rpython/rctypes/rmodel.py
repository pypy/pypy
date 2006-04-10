from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.error import TyperError
from pypy.rpython.lltypesystem import lltype
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
    #                   this is a Struct with a single field 'value' of
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
        memorystate = s_ctypesobject.memorystate

        self.rtyper = rtyper
        self.ctype = ctype
        self.ll_type = ll_type
        if memorystate == SomeCTypesObject.OWNSMEMORY:
            self.ownsmemory = True
        elif memorystate == SomeCTypesObject.MEMORYALIAS:
            self.ownsmemory = False
        else:
            raise TyperError("unsupported ctypes memorystate %r" % memorystate)

        self.c_data_type = self.get_c_data_type(ll_type)
        content_keepalives = self.get_content_keepalives()

        if self.ownsmemory:
            self.r_memoryowner = self
            self.lowleveltype = lltype.Ptr(
                    lltype.GcStruct( "CtypesBox_%s" % (ctype.__name__,),
                        ( "c_data", self.c_data_type ),
                        *content_keepalives
                    )
                )
        else:
            s_memoryowner = SomeCTypesObject(ctype,
                                             SomeCTypesObject.OWNSMEMORY)
            self.r_memoryowner = rtyper.getrepr(s_memoryowner)
            self.lowleveltype = lltype.Ptr(
                lltype.GcStruct( "CtypesBox_%s" % (ctype.__name__,),
                 ( "c_data", lltype.Ptr(self.c_data_type) ),
                 ( "c_data_owner_keepalive", self.r_memoryowner.lowleveltype ),
                 *content_keepalives
                )
            )
        self.const_cache = {} # store generated const values+original value

    def get_content_keepalives(self):
        "Return extra keepalive fields used for the content of this object."
        return []

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
        c1 = inputconst(lltype.Void, self.lowleveltype.TO) 
        return llops.genop("malloc", [c1], resulttype=self.lowleveltype)

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


class __extend__(pairtype(CTypesRepr, CTypesRepr)):

    def convert_from_to((r_from, r_to), v, llops):
        """Transparent conversion from the memory-owned to the memory-aliased
        version of the same ctypes repr."""
        if (r_from.ctype == r_to.ctype and
            r_from.ownsmemory and not r_to.ownsmemory):
            v_c_data = r_from.get_c_data(llops, v)
            return r_to.allocate_instance_ref(llops, v_c_data, v)
        else:
            return NotImplemented


class CTypesRefRepr(CTypesRepr):
    """Base class for ctypes repr that have some kind of by-reference
    semantics, like structures and arrays."""

    def get_c_data_type(self, ll_type):
        assert isinstance(ll_type, lltype.ContainerType)
        return ll_type


class CTypesValueRepr(CTypesRepr):
    """Base class for ctypes repr that have some kind of by-value
    semantics, like primitives and pointers."""

    def get_c_data_type(self, ll_type):
        return lltype.Struct('C_Data_%s' % (self.ctype.__name__,),
                             ('value', ll_type) )

    def getvalue_from_c_data(self, llops, v_c_data):
        cname = inputconst(lltype.Void, 'value')
        return llops.genop('getfield', [v_c_data, cname],
                resulttype=self.ll_type)

    def setvalue_inside_c_data(self, llops, v_c_data, v_value):
        cname = inputconst(lltype.Void, 'value')
        llops.genop('setfield', [v_c_data, cname, v_value])

    def getvalue(self, llops, v_box):
        """Reads from the 'value' field of the raw data."""
        v_c_data = self.get_c_data(llops, v_box)
        return self.getvalue_from_c_data(llops, v_c_data)

    def setvalue(self, llops, v_box, v_value):
        """Writes to the 'value' field of the raw data."""
        v_c_data = self.get_c_data(llops, v_box)
        self.setvalue_inside_c_data(llops, v_c_data, v_value)

    def convert_const(self, value):
        if isinstance(value, self.ctype):
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
            p = lltype.malloc(self.r_memoryowner.lowleveltype.TO)
            self.initialize_const(p, value)
            if self.ownsmemory:
                result = p
            else:
                # we must return a non-memory-owning box that keeps the
                # memory-owning box alive
                result = lltype.malloc(self.lowleveltype.TO)
                result.c_data = p.c_data    # initialize c_data pointer
                result.c_data_owner_keepalive = p
            self.const_cache[key] = result, keepalive
            return result

    def initialize_const(self, p, value):
        if isinstance(value, self.ctype):
            value = value.value
        p.c_data.value = value
