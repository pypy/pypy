from pypy.translator.translator import TranslationContext
from pypy import conftest
from py.test import raises
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython import robject, rclass, rint
from pypy.translator.tool.cbuild import enable_fast_compilation
from pypy.interpreter.baseobjspace import ObjSpace

import sys, types

P = False  # debug printing

SPECIAL_METHODS = {}

def setup_special_methods():
    for name, op, arity, funcs in ObjSpace.MethodTable:
        for fname in funcs:
            if fname.startswith('__'):
                ann = [None] * arity # replaced by class
                if 'attr' in fname:
                    ann[1] = str
                elif 'item' in fname:
                    ann[1] = int
                elif 'pow' in fname:
                    ann[1] = int
                elif 'shift' in fname:
                    ann[1] = int
                if arity == 3 and '_set' in fname:
                    ann[-1] = object
            SPECIAL_METHODS[fname] = ann
    # __init__ is not in the table.
    SPECIAL_METHODS['__init__'] = [None]
setup_special_methods()
                
def get_annotation(func, pre=[]):
    argstypelist = pre[:]
    if hasattr(func, '_initialannotation_'):
        for spec in func._initialannotation_:
            argstypelist.append(spec)
    if len(argstypelist) == 1:
        argstypelist = guess_methannotation(func, argstypelist[0])
    missing = [object] * (func.func_code.co_argcount - len(argstypelist))
    return missing + argstypelist

def guess_methannotation(func, cls):
    ret = [cls]
    if func.__name__ in SPECIAL_METHODS:
        pattern = SPECIAL_METHODS[func.__name__]
        ret = [thetype or cls for thetype in pattern]
    return ret

def should_expose_method(func):
    # expose all special methods but hide those starting with _
    name = func.__name__
    return name in SPECIAL_METHODS or not name.startswith('_')

def get_compiled_module(func, view=conftest.option.view, inline_threshold=1,
                use_boehm=False, exports=None):
    from pypy.translator.translator import TranslationContext
    from pypy.translator.backendopt.all import backend_optimizations

    from pypy.translator.c import gc
    from pypy.translator.c.genc import CExtModuleBuilder

    global _t # allow us to view later
    _t = t = TranslationContext(do_imports_immediately=False)
    ann = t.buildannotator()
    rtyper = t.buildrtyper()
    bk = rtyper.annotator.bookkeeper
    if not exports:
        exports = []

    ann.build_types(func, get_annotation(func))

    pyobj_options = {}

    for obj in exports:
        if isinstance(obj, tuple):
            _, obj = obj
        if isinstance(obj, type):
            cls = obj
            clsdef = bk.getuniqueclassdef(cls)
            rtyper.add_wrapper(clsdef)
            for obj in cls.__dict__.values():
                if isinstance(obj, types.FunctionType):
                    if should_expose_method(obj):
                        if not ann.bookkeeper.getdesc(obj).querycallfamily():
                            # not annotated, so enforce it
                            ann.build_types(obj, get_annotation(obj, [cls]), complete_now=False)
                elif isinstance(obj, property):
                    for obj in obj.fget, obj.fset, obj.fdel:
                        if obj and not ann.bookkeeper.getdesc(obj).querycallfamily():
                            ann.build_types(obj, get_annotation(obj, [cls]), complete_now=False)
        elif isinstance(obj, types.FunctionType):
            if not ann.bookkeeper.getdesc(obj).querycallfamily():
                # not annotated, so enforce it
                ann.build_types(obj, get_annotation(obj), complete_now=False)
            if obj.__name__ == '__init__':
                pyobj_options['use_true_methods'] = True

    all = []
    for obj in exports:
        if isinstance(obj, tuple):
            name, obj = obj
        else:
            name = obj.__name__
        if name != '__init__':
            all.append(name)

    exports = exports + [('__all__', all)]

    ann.build_types(func, get_annotation(func))
    if view:
        t.viewcg()
    rtyper.specialize()
    if view:
        t.viewcg()
    t.checkgraphs()

    gcpolicy = None
    if use_boehm:
        gcpolicy = gc.BoehmGcPolicy

    backend_optimizations(t, inline_threshold=inline_threshold)
    if view:
        t.viewcg()

    cbuilder = CExtModuleBuilder(t, func, gcpolicy=gcpolicy)
    # explicit build of database
    db = cbuilder.build_database(exports=exports, pyobj_options=pyobj_options)
    cbuilder.generate_source(db)
    if view:
        t.viewcg()
    cbuilder.compile()

    return cbuilder.import_module()

def get_compiled(func, *args, **kwds):
    module = get_compiled_module(func, *args, **kwds)
    return getattr(module, func.__name__)

# _______________________________________________-
# stubs for special annotation/rtyping

## these are not used for production right now.

def wrap(thing):
    return thing # untranslated case

def unwrap(pyobj, typ):
    assert isinstance(pyobj, typ)
    return pyobj # untranslated case
unwrap._annspecialcase_ = 'specialize:arg(1)'


# XXX
# wrapping/unwrapping should be annotatable.
# Idea: create tunnel objects which share
# annotation across SomeObjectness, sharing a key!

class Entry(ExtRegistryEntry):
    _about_ = unwrap

    def compute_result_annotation(self, s_wrapped, s_spec):
        # this will go away, much better way found!
        assert hasattr(s_spec, 'descriptions'), 'need a class in unwrap 2nd arg'
        descs = s_spec.descriptions
        assert len(descs) == 1, 'missing specialisation, classdesc not unique!'
        for desc in descs.keys():
            classdef = desc.getuniqueclassdef()
        return annmodel.SomeInstance(classdef)

    def specialize_call(self, hop):
        v_obj = hop.inputarg(hop.args_r[0], 0)
        return hop.llops.convertvar(v_obj, hop.args_r[0], hop.r_result)


class Entry(ExtRegistryEntry):
    _about_ = wrap

    s_result_annotation = annmodel.SomeObject()

    def specialize_call(self, hop):
        assert len(hop.args_r) == 1, 'wrap() takes exactly one argument'
        v_obj, = hop.inputargs(*hop.args_r)
        return hop.llops.convertvar(v_obj, hop.args_r[0], robject.pyobj_repr)

# _______________________________________________
# creating our own setup function for the module

# this class *can* be used for faster access.
# the compiler anyway chews quite a bit on it...
class BuiltinHelper(object):
    # the following would be much easier if we had
    # loop unrolling right inside the flowing process
    src = []
    src.append('def _setup(self):')
    src.append('    import __builtin__ as b')
    import __builtin__
    for name in dir(__builtin__):
        obj = getattr(__builtin__, name)
        if callable(obj) and hasattr(obj, '__name__'):
            src.append('    self.%s = b.%s' % (name, obj.__name__))
    src = '\n'.join(src)
    #print src
    exec src
    def __init__(self):
        self._initialized = False
    del __builtin__, name, obj, src

bltn_singleton = BuiltinHelper()

def get_bltn():
    if not bltn_singleton._initialized:
        bltn_singleton._setup()
        bltn_singleton._initialized = True
    return bltn_singleton

def get_methodname(funcidx):
    pass

class Entry(ExtRegistryEntry):
    _about_ = get_methodname
    s_result_annotation = annmodel.SomeObject()

    def specialize_call(self, hop):
        v_idx, = hop.inputargs(*hop.args_r)
        if hop.args_r[0] <> rint.signed_repr:
            v_idx = hop.llops.convertvar(v_idx,
                                         r_from=hop.args_r[0],
                                           r_to=rint.signed_repr)
        v_res = hop.llops.gencapicall('postsetup_get_methodname', [v_idx],
                                      resulttype=robject.pyobj_repr)
        return v_res

def build_method(funcidx):
    pass

class Entry(ExtRegistryEntry):
    _about_ = build_method
    s_result_annotation = annmodel.SomeObject()

    def specialize_call(self, hop):
        v_idx, v_type = hop.inputargs(*hop.args_r)
        if hop.args_r[0] <> rint.signed_repr:
            v_idx = hop.llops.convertvar(v_idx,
                                         r_from=hop.args_r[0],
                                           r_to=rint.signed_repr)
        assert hop.args_r[1] == robject.pyobj_repr, (
            'build_method works for Python types only')                                            
        v_res = hop.llops.gencapicall('postsetup_build_method', [v_idx, v_type],
                                      resulttype=robject.pyobj_repr)
        return v_res

def get_typedict(cls):
    pass

class Entry(ExtRegistryEntry):
    _about_ = get_typedict
    s_result_annotation = annmodel.SomeObject()

    def specialize_call(self, hop):
        v_type, = hop.inputargs(*hop.args_r)
        assert hop.args_r[0] == robject.pyobj_repr, (
            'get_typedict works for Python types only')                                            
        v_res = hop.llops.gencapicall('postsetup_get_typedict', [v_type],
                                      resulttype=robject.pyobj_repr)
        return v_res

def __init__(mod):
    """
    this module init function walks through all exported classes
    and tries to build real methods from the functions.
    properties are re-created, too.
    """
    import types
    bltn = get_bltn()
    hasattr = bltn.hasattr
    isinstance = bltn.isinstance

    funcs = bltn.dict() # no hashing function for PyObject
    idx = 0
    while 1:
        name = get_methodname(idx)
        if not name:
            break
        func = getattr(mod, name)
        funcs[func] = idx
        idx += 1
    
    for name in mod.__all__:
        obj = getattr(mod, name)
        if isinstance(obj, type) and hasattr(obj, '__self__'):
            cls = obj
            dic = get_typedict(cls)
            for name, value in dic.items():
                if isinstance(value, types.BuiltinFunctionType) and value in funcs:
                    idx = funcs[value]
                    meth = build_method(idx, cls)
                    dic[name] = meth
                elif isinstance(value, property):
                    stuff = [value.fget, value.fset, value.fdel, value.__doc__]
                    for i, fn in enumerate(stuff):
                        if fn in funcs:
                            idx = funcs[fn]
                            stuff[i] = build_method(idx, cls)
                    if not stuff[-1]:
                        # use fget's doc if we don't ahve one
                        stuff[-1] = getattr(stuff[0], '__doc__', None)
                    dic[name] = property(*stuff)

class ExtCompiler(object):
    def __init__(self, startupfunc, use_true_methods=True):
        self.startupfunc = startupfunc
        self.exports = {}
        if use_true_methods:
            self.export(__init__)

    def export(self, obj, name=None):
        if name:
            self.exports[name] = (name, obj)
        else:
            self.exports[obj.__name__] = obj

    def build(self, modname):
        mod = get_compiled_module(self.startupfunc, exports=self.exports.values())
        return mod
