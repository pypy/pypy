from pypy.rpython.rmodel import Repr, IntegerRepr, inputconst
from pypy.rpython.error import TyperError
from pypy.rpython import extregistry
from pypy.rpython.lltypesystem import lltype
from pypy.annotation import model as annmodel
from pypy.annotation.pairtype import pairtype
from pypy.rpython.rctypes.rmodel import CTypesValueRepr, genreccopy

from ctypes import POINTER, pointer, byref, c_int

class PointerRepr(CTypesValueRepr):
    def __init__(self, rtyper, s_pointer):
        ptr_ctype = s_pointer.knowntype
        ref_ctype = ptr_ctype._type_

        # Find the repr and low-level type of the contents from its ctype
        self.r_contents = rtyper.getrepr(annmodel.SomeCTypesObject(ref_ctype,
                                     annmodel.SomeCTypesObject.MEMORYALIAS))

        ll_contents = lltype.Ptr(self.r_contents.c_data_type)

        super(PointerRepr, self).__init__(rtyper, s_pointer, ll_contents)

    def get_content_keepalives(self):
        "Return an extra keepalive field used for the pointer's contents."
        return [('keepalive_contents',
                 self.r_contents.r_memoryowner.lowleveltype)]

    def setkeepalive(self, llops, v_box, v_owner):
        inputargs = [v_box, inputconst(lltype.Void, 'keepalive_contents'),
                     v_owner]
        llops.genop('setfield', inputargs)

    def initialize_const(self, p, ptr):
        llcontents = self.r_contents.convert_const(ptr.contents)
        p.c_data[0] = llcontents.c_data
        # the following line is probably pointless, as 'llcontents' will be
        # an immortal global constant just like 'p', but better safe than sorry
        p.keepalive_contents = llcontents.c_data_owner_keepalive

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
        return self.r_contents.allocate_instance_ref(hop.llops, v_c_ptr)

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
        if hop.args_s[1].is_constant() and hop.args_s[1].const == 0:
            v_c_ptr = self.getvalue(hop. llops, v_ptr)
            return self.r_contents.return_c_data(hop.llops, v_c_ptr)
        else:
            raise NotImplementedError("XXX: pointer[non-zero-index]")

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
        genreccopy(hop.llops, v_new_c_data, v_target)

# ____________________________________________________________

def pointertype_compute_annotation(metatype, type):
    def compute_result_annotation(*arg_s):
        return annmodel.SomeCTypesObject(type,
                annmodel.SomeCTypesObject.OWNSMEMORY)
    return annmodel.SomeBuiltin(compute_result_annotation, 
                                methodname=type.__name__)

def pointertype_specialize_call(hop):
    r_ptr = hop.r_result
    v_result = r_ptr.allocate_instance(hop.llops)
    if len(hop.args_s):
        v_contentsbox, = hop.inputargs(r_ptr.r_contents)
        r_ptr.setcontents(hop.llops, v_result, v_contentsbox)
    return v_result

def pointerinstance_compute_annotation(type, instance):
    return annmodel.SomeCTypesObject(type,
            annmodel.SomeCTypesObject.OWNSMEMORY)

def pointerinstance_field_annotation(s_pointer, fieldname):
    assert fieldname == "contents"
    ptrtype = s_pointer.knowntype
    return annmodel.SomeCTypesObject(ptrtype._type_,
                                     annmodel.SomeCTypesObject.MEMORYALIAS)

def pointerinstance_get_repr(rtyper, s_pointer):
    return PointerRepr(rtyper, s_pointer)

PointerType = type(POINTER(c_int))
extregistry.register_type(PointerType,
        compute_annotation=pointertype_compute_annotation,
        specialize_call=pointertype_specialize_call)

entry = extregistry.register_metatype(PointerType,
        compute_annotation=pointerinstance_compute_annotation,
        get_repr=pointerinstance_get_repr)
entry.get_field_annotation = pointerinstance_field_annotation

def pointerfn_compute_annotation(s_arg):
    assert isinstance(s_arg, annmodel.SomeCTypesObject)
    ctype = s_arg.knowntype
    result_ctype = POINTER(ctype)
    return annmodel.SomeCTypesObject(result_ctype,
                                     annmodel.SomeCTypesObject.OWNSMEMORY)

extregistry.register_value(pointer,
        compute_result_annotation=pointerfn_compute_annotation,
        # same rtyping for calling pointer() or calling a specific instance
        # of PointerType:
        specialize_call=pointertype_specialize_call)

# byref() is equivalent to pointer() -- the difference is only an
# optimization that is useful in ctypes but not in rctypes.
extregistry.register_value(byref,
        compute_result_annotation=pointerfn_compute_annotation,
        specialize_call=pointertype_specialize_call)

# constant-fold POINTER(CONSTANT_CTYPE) calls
def POINTER_compute_annotation(s_arg):
    from pypy.annotation.bookkeeper import getbookkeeper
    assert s_arg.is_constant(), "POINTER(%r): argument must be constant" % (
        s_arg,)
    RESTYPE = POINTER(s_arg.const)
    return getbookkeeper().immutablevalue(RESTYPE)

def POINTER_specialize_call(hop):
    assert hop.s_result.is_constant()
    return hop.inputconst(lltype.Void, hop.s_result.const)

extregistry.register_value(POINTER,
        compute_result_annotation=POINTER_compute_annotation,
        specialize_call=POINTER_specialize_call)
