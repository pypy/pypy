from pypy.rpython.extregistry import ExtRegistryEntry


def cpy_export(obj, cpytype):
    raise NotImplementedError("only works in translated versions")


class Entry(ExtRegistryEntry):
    _about_ = cpy_export

    def compute_result_annotation(self, s_obj, s_cpytype):
        from pypy.annotation.model import SomeObject
        from pypy.annotation.model import SomeInstance
        assert isinstance(s_obj, SomeInstance)
        assert s_cpytype.is_constant()
        cpytype = s_cpytype.const
        if hasattr(s_obj.classdef, '_cpy_exported_type_'):
            assert s_obj.classdef._cpy_exported_type_ == cpytype
        else:
            s_obj.classdef._cpy_exported_type_ = cpytype
        s = SomeObject()
        s.knowntype = cpytype
        return s

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        r_inst = hop.args_r[0]
        v_inst = hop.inputarg(r_inst, arg=0)
        return hop.genop('cast_pointer', [v_inst],
                         resulttype = lltype.Ptr(lltype.PyObject))
