from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.objectmodel import CDefinedIntSymbolic


def cpy_export(cpytype, obj):
    raise NotImplementedError("only works in translated versions")

def cpy_import(rpytype, obj):
    raise NotImplementedError("only works in translated versions")


class Entry(ExtRegistryEntry):
    _about_ = cpy_export

    def compute_result_annotation(self, s_cpytype, s_obj):
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
        s_obj = hop.args_s[1]
        r_inst = hop.args_r[1]
        v_inst = hop.inputarg(r_inst, arg=1)
        return hop.genop('cast_pointer', [v_inst],
                         resulttype = lltype.Ptr(lltype.PyObject))


class Entry(ExtRegistryEntry):
    _about_ = cpy_import

    def compute_result_annotation(self, s_rpytype, s_obj):
        from pypy.annotation.bookkeeper import getbookkeeper
        from pypy.annotation.model import SomeInstance
        assert s_rpytype.is_constant()
        rpytype = s_rpytype.const
        bk = getbookkeeper()
        return SomeInstance(bk.getuniqueclassdef(rpytype))

    def specialize_call(self, hop):
        from pypy.annotation.model import SomeInstance
        from pypy.rpython.robject import pyobj_repr
        s_rpytype = hop.args_s[0]
        assert s_rpytype.is_constant()
        rpytype = s_rpytype.const
        classdef = hop.rtyper.annotator.bookkeeper.getuniqueclassdef(rpytype)
        s_inst = SomeInstance(classdef)
        r_inst = hop.rtyper.getrepr(s_inst)
        assert r_inst.lowleveltype.TO._gckind == 'cpy'
        v_obj = hop.inputarg(pyobj_repr, arg=1)
        return hop.genop('cast_pointer', [v_obj],
                         resulttype = r_inst.lowleveltype)


PyObjPtr = lltype.Ptr(lltype.PyObject)

PY_TYPE_OBJECT = lltype.PyStruct(
    'PyTypeObject',
    ('head',           lltype.PyObject),
    ('c_ob_size',      lltype.Signed),
    ('c_tp_name',      lltype.Ptr(lltype.FixedSizeArray(lltype.Char, 1))),
    ('c_tp_basicsize', lltype.Signed),
    ('c_tp_itemsize',  lltype.Signed),
    ('c_tp_dealloc',   lltype.Signed),
    ('c_tp_print',     lltype.Signed),
    ('c_tp_getattr',   lltype.Signed),
    ('c_tp_setattr',   lltype.Signed),   # in
    ('c_tp_compare',   lltype.Signed),
    ('c_tp_repr',      lltype.Signed),   # progress
    ('c_tp_as_number', lltype.Signed),
    ('c_tp_as_sequence',lltype.Signed),
    ('c_tp_as_mapping',lltype.Signed),
    ('c_tp_hash',      lltype.Signed),
    ('c_tp_call',      lltype.Signed),
    ('c_tp_str',       lltype.Signed),
    ('c_tp_getattro',  lltype.Signed),
    ('c_tp_setattro',  lltype.Signed),
    ('c_tp_as_buffer', lltype.Signed),
    ('c_tp_flags',     lltype.Signed),

    hints={'c_name': '_typeobject', 'external': True, 'inline_head': True})
# XXX should be PyTypeObject but genc inserts 'struct' :-(

def build_pytypeobject(r_inst):
    typetype = lltype.pyobjectptr(type)
    pytypeobj = lltype.malloc(PY_TYPE_OBJECT, flavor='cpy',
                              extra_args=(typetype,))
    name = r_inst.classdef._cpy_exported_type_.__name__
    T = lltype.FixedSizeArray(lltype.Char, len(name)+1)
    p = lltype.malloc(T, immortal=True)
    for i in range(len(name)):
        p[i] = name[i]
    p[len(name)] = '\x00'
    pytypeobj.c_tp_name = lltype.direct_arrayitems(p)
    pytypeobj.c_tp_basicsize = llmemory.sizeof(r_inst.lowleveltype.TO)
    pytypeobj.c_tp_flags = CDefinedIntSymbolic('Py_TPFLAGS_DEFAULT')
    return lltype.cast_pointer(PyObjPtr, pytypeobj)
