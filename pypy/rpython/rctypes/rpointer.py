from pypy.rpython.rmodel import IntegerRepr, inputconst
from pypy.rpython.error import TyperError
from pypy.rpython.lltypesystem import lltype
from pypy.tool.pairtype import pairtype
from pypy.rpython.rctypes.rmodel import CTypesValueRepr, genreccopy
from pypy.annotation.model import SomeCTypesObject
from pypy.objspace.flow.model import Constant


class PointerRepr(CTypesValueRepr):
    def __init__(self, rtyper, s_pointer):
        # For recursive types, getting the r_contents is delayed until
        # _setup_repr().
        ll_contents = lltype.Ptr(lltype.ForwardReference())
        self.keepalive_box_type = lltype.GcForwardReference()
        super(PointerRepr, self).__init__(rtyper, s_pointer, ll_contents)

    def _setup_repr(self):
        # Find the repr and low-level type of the contents from its ctype
        rtyper = self.rtyper
        ref_ctype = self.ctype._type_
        self.r_contents = rtyper.getrepr(SomeCTypesObject(ref_ctype,
                                                          ownsmemory=False))
        if isinstance(self.ll_type.TO, lltype.ForwardReference):
            self.ll_type.TO.become(self.r_contents.c_data_type)
        if isinstance(self.keepalive_box_type, lltype.GcForwardReference):
            self.keepalive_box_type.become(
                self.r_contents.r_memoryowner.lowleveltype.TO)

    def get_content_keepalive_type(self):
        "Keepalive for the box that holds the data that 'self' points to."
        return lltype.Ptr(self.keepalive_box_type)

    def setkeepalive(self, llops, v_box, v_owner):
        inputargs = [v_box, inputconst(lltype.Void, 'keepalive'),
                     v_owner]
        llops.genop('setfield', inputargs)

    def initialize_const(self, p, ptr):
        if not ptr:   # NULL pointer, or literal None passed as argument to
            return    #  functions expecting pointers
        llcontents = self.r_contents.convert_const(ptr.contents)
        p.c_data[0] = llcontents.c_data
        # the following line is probably pointless, as 'llcontents' will be
        # an immortal global constant just like 'p', but better safe than sorry
        p.keepalive = llcontents.c_data_owner_keepalive

    def setcontents(self, llops, v_ptr, v_contentsbox):
        v_c_data = self.r_contents.get_c_data(llops, v_contentsbox)
        v_owner = self.r_contents.get_c_data_owner(llops, v_contentsbox)
        self.setvalue(llops, v_ptr, v_c_data)
        self.setkeepalive(llops, v_ptr, v_owner)

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'contents'
        v_ptr = hop.inputarg(self, 0)
        v_c_ptr = self.getvalue(hop.llops, v_ptr)
        v_owner = self.getkeepalive(hop.llops, v_ptr)
        hop.exception_cannot_occur()
        return self.r_contents.allocate_instance_ref(hop.llops, v_c_ptr,
                                                     v_owner)

    def rtype_setattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'contents'
        v_ptr, v_attr, v_newcontents = hop.inputargs(self, lltype.Void,
                                                     self.r_contents)
        self.setcontents(hop.llops, v_ptr, v_newcontents)


class __extend__(pairtype(PointerRepr, IntegerRepr)):

    def rtype_getitem((r_ptr, _), hop):
        self = r_ptr
        v_ptr, v_index = hop.inputargs(self, lltype.Signed)
        v_c_ptr = self.getvalue(hop.llops, v_ptr)
        hop.exception_cannot_occur()
        if isinstance(v_index, Constant) and v_index.value == 0:
            pass   # skip direct_ptradd
        else:
            v_c_ptr = hop.genop('direct_ptradd', [v_c_ptr, v_index],
                                resulttype = r_ptr.ll_type)
        return self.r_contents.return_c_data(hop.llops, v_c_ptr)

    def rtype_setitem((r_ptr, _), hop):
        # p[0] = x  is not the same as  p.contents.value = x
        # it makes a copy of the data in 'x' just like rarray.rtype_setitem()
        self = r_ptr
        v_ptr, v_index, v_contentsbox = hop.inputargs(self, lltype.Signed,
                                                      self.r_contents)
        v_new_c_data = self.r_contents.get_c_data(hop.llops, v_contentsbox)
        v_target = self.getvalue(hop.llops, v_ptr)
        if hop.args_s[1].is_constant() and hop.args_s[1].const == 0:
            pass
        else:
            # not supported by ctypes either
            raise TyperError("assignment to pointer[x] with x != 0")
        # copy the whole structure's content over
        hop.exception_cannot_occur()
        genreccopy(hop.llops, v_new_c_data, v_target)
