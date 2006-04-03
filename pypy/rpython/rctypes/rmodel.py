from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.error import TyperError
from pypy.rpython.lltypesystem import lltype
from pypy.annotation.model import SomeCTypesObject



class CTypesRepr(Repr):
    "Base class for the Reprs representing ctypes object."

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

        if isinstance(ll_type, lltype.ContainerType):
            self.c_data_type = ll_type
        else:
            self.c_data_type = lltype.Struct('C_Data_%s' % (ctype.__name__,),
                                                ('value', ll_type) )

        if self.ownsmemory:
            self.lowleveltype = lltype.Ptr(
                lltype.GcStruct( "CtypesBox_%s" % (ctype.__name__,),
                    ( "c_data", self.c_data_type )
                )
            )
        else:
            self.lowleveltype = lltype.Ptr(
                lltype.GcStruct( "CtypesBox_%s" % (ctype.__name__,),
                    ( "c_data_ref", lltype.Ptr(self.c_data_type) )
                )
            )
        # XXX keepalives...
        self.const_cache = {} # store generated const values+original value

    def get_c_data(self, llops, v_box):
        if self.ownsmemory:
            inputargs = [v_box, inputconst(lltype.Void, "c_data")]
            return llops.genop('getsubstruct', inputargs,
                        lltype.Ptr(self.c_data_type) )
        else:
            inputargs = [v_box, inputconst(lltype.Void, "c_data_ref")]
            return llops.genop('getfield', inputargs,
                        lltype.Ptr(self.c_data_type) )

    def setvalue(self, llops, v_box, v_value):
        """Writes the 'value' field of the raw data
           (only if ll_type is not a container type)"""
        v_c_data = self.get_c_data(llops, v_box)
        cname = inputconst(lltype.Void, 'value')
        llops.genop('setfield', [v_c_data, cname, v_value])

    def getvalue(self, llops, v_box):
        """Reads the 'value' field of the raw data
           (only if ll_type is not a container type)"""
        v_c_data = self.get_c_data(llops, v_box)
        cname = inputconst(lltype.Void, 'value')
        return llops.genop('getfield', [v_c_data, cname],
                resulttype=self.ll_type)
