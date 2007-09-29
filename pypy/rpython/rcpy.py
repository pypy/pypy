from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import CDefinedIntSymbolic
from pypy.objspace.flow.model import Constant, Variable
from pypy.objspace.flow.model import FunctionGraph, Block, Link


class CPyTypeInterface(object):

    def __init__(self, name, objects={}, subclassable=False):

        # the exported name of the type
        self.name = name

        # a dict {name: pyobjectptr()} for general class attributes
        # (not for special methods!)
        self.objects = objects.copy()
        self.subclassable = subclassable

    def _freeze_(self):
        return True

    def emulate(self, original_class):
        "Build a type object that emulates 'self'."
        assert isinstance(original_class, type)
        d = {'__slots__': [], '_rpython_class_': original_class}
        for name, value in self.objects.items():
            assert lltype.typeOf(value) == PyObjPtr
            assert isinstance(value._obj, lltype._pyobject)
            d[name] = value._obj.value
        t = type(self.name, (rpython_object,), d)
        return t


def cpy_export(cpytype, obj):
    raise NotImplementedError("only works in translated versions")

def cpy_import(rpytype, obj):
    raise NotImplementedError("only works in translated versions")

def cpy_typeobject(cpytype, cls):
    raise NotImplementedError("only works in translated versions")

def cpy_allocate(cls, cpytype):
    raise NotImplementedError("only works in translated versions")


# ____________________________________________________________
# Implementation

class Entry(ExtRegistryEntry):
    _about_ = cpy_export

    def compute_result_annotation(self, s_cpytype, s_obj):
        from pypy.annotation.model import SomeObject
        from pypy.annotation.model import SomeInstance
        assert isinstance(s_obj, SomeInstance)
        assert s_cpytype.is_constant()
        cpytype = s_cpytype.const
        attach_cpy_flavor(s_obj.classdef, cpytype)
        return SomeObject()

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


class Entry(ExtRegistryEntry):
    _about_ = cpy_typeobject

    def compute_result_annotation(self, s_cpytype, s_cls):
        from pypy.annotation.model import SomeObject
        assert s_cls.is_constant()
        assert s_cpytype.is_constant()
        cpytype = s_cpytype.const
        [classdesc] = s_cls.descriptions
        classdef = classdesc.getuniqueclassdef()
        attach_cpy_flavor(classdef, cpytype)
        return SomeObject()

    def specialize_call(self, hop):
        from pypy.rpython.rclass import getinstancerepr
        s_cls = hop.args_s[1]
        assert s_cls.is_constant()
        [classdesc] = s_cls.descriptions
        classdef = classdesc.getuniqueclassdef()
        r_inst = getinstancerepr(hop.rtyper, classdef)
        cpytype = build_pytypeobject(r_inst)
        return hop.inputconst(PyObjPtr, cpytype)

class Entry(ExtRegistryEntry):
    _about_ = cpy_allocate

    def compute_result_annotation(self, s_cls, s_cpytype):
        from pypy.annotation.model import SomeObject, SomeInstance
        assert s_cls.is_constant()
        [classdesc] = s_cls.descriptions
        classdef = classdesc.getuniqueclassdef()        
        return SomeInstance(classdef)

    def specialize_call(self, hop):
        from pypy.rpython.rclass import getinstancerepr
        s_cls = hop.args_s[0]
        assert s_cls.is_constant()
        [classdesc] = s_cls.descriptions
        classdef = classdesc.getuniqueclassdef()
        r_inst = getinstancerepr(hop.rtyper, classdef)
        vinst = r_inst.new_instance(hop.llops, v_cpytype = hop.args_v[1])
        return vinst


def attach_cpy_flavor(classdef, cpytype):
    for parentdef in classdef.getmro():
        if not hasattr(parentdef, '_cpy_exported_type_'):
            parentdef._cpy_exported_type_ = None
    if classdef._cpy_exported_type_ is None:
        classdef._cpy_exported_type_ = cpytype
    else:
        assert classdef._cpy_exported_type_ == cpytype


PyObjPtr = lltype.Ptr(lltype.PyObject)
PyNumberMethods = lltype.Struct('PyNumberMethods',
    hints={'c_name': 'PyNumberMethods', 'external': True, 'typedef': True})
PyMappingMethods = lltype.Struct('PyMappingMethods',
    hints={'c_name': 'PyMappingMethods', 'external': True, 'typedef': True})
PySequenceMethods = lltype.Struct('PySequenceMethods',
    hints={'c_name': 'PySequenceMethods', 'external': True, 'typedef': True})
PY_TYPE_OBJECT = lltype.PyForwardReference()
PY_TYPE_OBJECT.become(lltype.PyStruct(
    'PyTypeObject',
    ('head',           lltype.PyObject),
    ('c_ob_size',      lltype.Signed),
    ('c_tp_name',      lltype.Ptr(lltype.FixedSizeArray(lltype.Char, 1))),
    ('c_tp_basicsize', lltype.Signed),
    ('c_tp_itemsize',  lltype.Signed),
    ('c_tp_dealloc',   lltype.Ptr(lltype.FuncType([PyObjPtr],
                                                  lltype.Void))),
    ('c_tp_print',     lltype.Signed),
    ('c_tp_getattr',   lltype.Signed),
    ('c_tp_setattr',   lltype.Signed),   # in
    ('c_tp_compare',   lltype.Signed),
    ('c_tp_repr',      lltype.Signed),   # progress
    ('c_tp_as_number', lltype.Ptr(PyNumberMethods)),
    ('c_tp_as_sequence',lltype.Ptr(PySequenceMethods)),
    ('c_tp_as_mapping',lltype.Ptr(PyMappingMethods)),
    ('c_tp_hash',      lltype.Signed),
    ('c_tp_call',      lltype.Signed),
    ('c_tp_str',       lltype.Signed),
    ('c_tp_getattro',  lltype.Signed),
    ('c_tp_setattro',  lltype.Signed),
    ('c_tp_as_buffer', lltype.Signed),
    ('c_tp_flags',     lltype.Signed),
    ('c_tp_doc',       lltype.Signed),
    ('c_tp_traverse',  lltype.Signed),
    ('c_tp_clear',     lltype.Signed),
    ('c_tp_richcompare',lltype.Signed),
    ('c_tp_weaklistoffset',lltype.Signed),
    ('c_tp_iter',      lltype.Signed),
    ('c_tp_iternext',  lltype.Signed),
    ('c_tp_methods',   lltype.Signed),
    ('c_tp_members',   lltype.Signed),
    ('c_tp_getset',    lltype.Signed),
    ('c_tp_base',      lltype.Signed),
    ('c_tp_dict',      PyObjPtr),
    ('c_tp_descr_get', lltype.Signed),
    ('c_tp_descr_set', lltype.Signed),
    ('c_tp_dictoffset',lltype.Signed),
    ('c_tp_init',      lltype.Signed),
    ('c_tp_alloc',     lltype.Signed),
                       #lltype.Ptr(lltype.FuncType([lltype.Ptr(PY_TYPE_OBJECT),
                       #                            lltype.Signed],
                       #                           PyObjPtr))),
    ('c_tp_new',       lltype.Ptr(lltype.FuncType([lltype.Ptr(PY_TYPE_OBJECT),
                                                   PyObjPtr,
                                                   PyObjPtr],
                                                  PyObjPtr))),
    ('c_tp_free',      lltype.Signed),
                       #lltype.Ptr(lltype.FuncType([llmemory.Address],
                       #                           lltype.Void))),

    hints={'c_name': 'PyTypeObject', 'external': True, 'typedef': True, 'inline_head': True}))
# XXX 'c_name' should be 'PyTypeObject' but genc inserts 'struct' :-(

def ll_tp_dealloc(p):
    addr = llmemory.cast_ptr_to_adr(p)
    # Warning: this relies on an optimization in gctransformer, which will
    # not insert any incref/decref for 'p'.  That would lead to infinite
    # recursion, as the refcnt of 'p' is already zero!
    from pypy.rpython.lltypesystem.rclass import CPYOBJECT
    llop.gc_deallocate(lltype.Void, CPYOBJECT, addr)

def build_pytypeobject(r_inst):
    rtyper = r_inst.rtyper
    cache = rtyper.classdef_to_pytypeobject
    try:
        return cache[r_inst.classdef]
    except KeyError:
        for parentdef in r_inst.classdef.getmro():
            cpytype = parentdef._cpy_exported_type_
            if cpytype is not None:
                break
        else:
            # for classes that cannot be exported at all
            return lltype.nullptr(lltype.PyObject)

        from pypy.rpython.lltypesystem.rclass import CPYOBJECTPTR
        from pypy.rpython.rtyper import LowLevelOpList
        typetype = lltype.pyobjectptr(type)

        # XXX default tp_new should go away
        # make the graph of tp_new manually    
        v1 = Variable('tp');   v1.concretetype = lltype.Ptr(PY_TYPE_OBJECT)
        v2 = Variable('args'); v2.concretetype = PyObjPtr
        v3 = Variable('kwds'); v3.concretetype = PyObjPtr
        block = Block([v1, v2, v3])
        llops = LowLevelOpList(None)
        v4 = r_inst.new_instance(llops, v_cpytype = v1)
        v5 = llops.genop('cast_pointer', [v4], resulttype = PyObjPtr)
        block.operations = list(llops)
        tp_new_graph = FunctionGraph('ll_tp_new', block)
        block.closeblock(Link([v5], tp_new_graph.returnblock))
        tp_new_graph.getreturnvar().concretetype = v5.concretetype

        # build the PyTypeObject structure
        pytypeobj = lltype.malloc(PY_TYPE_OBJECT, flavor='cpy',
                                  extra_args=(typetype,))
        name = cpytype.name
        T = lltype.FixedSizeArray(lltype.Char, len(name)+1)
        p = lltype.malloc(T, immortal=True)
        for i in range(len(name)):
            p[i] = name[i]
        p[len(name)] = '\x00'
        pytypeobj.c_tp_name = lltype.direct_arrayitems(p)
        pytypeobj.c_tp_basicsize = llmemory.sizeof(r_inst.lowleveltype.TO)
        if cpytype.subclassable:
            pytypeobj.c_tp_flags = CDefinedIntSymbolic('''(Py_TPFLAGS_DEFAULT |
                Py_TPFLAGS_CHECKTYPES | Py_TPFLAGS_BASETYPE)''')
        else:
            pytypeobj.c_tp_flags = CDefinedIntSymbolic('''(Py_TPFLAGS_DEFAULT |
                Py_TPFLAGS_CHECKTYPES)''')
        pytypeobj.c_tp_new = rtyper.type_system.getcallable(tp_new_graph)
        pytypeobj.c_tp_dealloc = rtyper.annotate_helper_fn(ll_tp_dealloc,
                                                           [PyObjPtr])
        pytypeobj.c_tp_as_number = lltype.malloc(PyNumberMethods, immortal=True)
        pytypeobj.c_tp_as_sequence = lltype.malloc(PySequenceMethods, immortal=True)
        pytypeobj.c_tp_as_mapping = lltype.malloc(PyMappingMethods, immortal=True)
        result =  lltype.cast_pointer(PyObjPtr, pytypeobj)

        # the llsetup function that will store the 'objects' into the
        # type's tp_dict
        Py_TPFLAGS_HEAPTYPE = CDefinedIntSymbolic('Py_TPFLAGS_HEAPTYPE')
        if cpytype.objects:
            objects = [(lltype.pyobjectptr(name), value)
                       for name, value in cpytype.objects.items() if name != '__new__']
            if '__new__' in cpytype.objects:
                new = cpytype.objects['__new__']._obj.value
                objects.append((lltype.pyobjectptr('__new__'),
                                lltype.pyobjectptr(staticmethod(new))))

            def ll_type_setup(p):
                tp = lltype.cast_pointer(lltype.Ptr(PY_TYPE_OBJECT), p)
                old_flags = tp.c_tp_flags
                tp.c_tp_flags |= Py_TPFLAGS_HEAPTYPE
                for name, value in objects:
                    llop.setattr(PyObjPtr, tp, name, value)
                tp.c_tp_flags = old_flags
            result._obj.setup_fnptr = rtyper.annotate_helper_fn(ll_type_setup,
                                                                [PyObjPtr])

        cache[r_inst.classdef] = result
        return result

# ____________________________________________________________
# Emulation support, to have user-defined classes and instances
# work nicely on top of CPython running the CPyObjSpace

class rpython_meta(type):
    pass

class rpython_object(object):
    """NOT_RPYTHON
    Wrapper object, for emulation.
    """
    __metaclass__ = rpython_meta
    __slots__ = ('data',)
rpython_data = rpython_object.data
del rpython_object.data

def init_rpython_data(wrapperobj, value):
    """NOT_RPYTHON
    Set the wrapper object's hidden 'data' slot to point to the original
    RPython instance 'value'.
    """
    rpython_data.__set__(wrapperobj, value)

def get_rpython_data(wrapperobj):
    """NOT_RPYTHON
    Get the original RPython instance from the wrapper object.
    """
    return rpython_data.__get__(wrapperobj)


class Entry(ExtRegistryEntry):
    """Support for translating prebuilt emulated type objects."""
    _type_ = rpython_meta

    def get_ll_pyobjectptr(self, rtyper):
        from pypy.rpython.rclass import getinstancerepr
        emulated_cls = self.instance
        rpython_cls = emulated_cls._rpython_class_
        classdef = rtyper.annotator.bookkeeper.getuniqueclassdef(rpython_cls)
        r_inst = getinstancerepr(rtyper, classdef)
        return build_pytypeobject(r_inst)


class Entry(ExtRegistryEntry):
    """Support for translating prebuilt emulated type objects."""
    _metatype_ = rpython_meta

    def get_ll_pyobjectptr(self, rtyper):
        from pypy.rpython.rclass import getinstancerepr
        wrapperobj = self.instance
        rpython_obj = get_rpython_data(wrapperobj)
        rpython_cls = rpython_obj.__class__
        classdef = rtyper.annotator.bookkeeper.getuniqueclassdef(rpython_cls)
        r_inst = getinstancerepr(rtyper, classdef)
        pyobj = r_inst.convert_const(rpython_obj)
        return lltype.cast_pointer(PyObjPtr, pyobj)
