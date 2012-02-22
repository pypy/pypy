from pypy.annotation import model, description
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.controllerentry import (
    Controller, ControllerEntry, SomeControlledInstance)
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rlib.objectmodel import instantiate
from pypy.rlib.unroll import unrolling_iterable
from pypy.tool.sourcetools import func_with_new_name
from pypy.translator.tool.cbuild import ExternalCompilationInfo
import py
import sys
import types

class export(object):
    """decorator to mark a function as exported by a shared module.
    Can be used with a signature::
        @export(float, float)
        def f(x, y):
            return x + y
    or without any argument at all::
        @export
        def f(x, y):
            return x + y
    in which case the function must be used somewhere else, which will
    trigger its annotation."""

    argtypes = None
    namespace = None

    def __new__(cls, *args, **kwds):
        if len(args) == 1 and isinstance(args[0], types.FunctionType):
            func = args[0]
            decorated = export()(func)
            del decorated.argtypes
            return decorated
        return object.__new__(cls)

    def __init__(self, *args, **kwds):
        self.argtypes = args
        self.namespace = kwds.pop('namespace', None)
        if kwds:
            raise TypeError("unexpected keyword arguments: %s" % kwds.keys())

    def __call__(self, func):
        func.exported = True
        if self.argtypes is not None:
            func.argtypes = self.argtypes
        if self.namespace is not None:
            func.namespace = self.namespace
        return func


class ClassExportInfo:
    def __init__(self, name, cls):
        self.name = name
        self.cls = cls

    def make_constructor(self):
        self.constructor_name = "__new__%s" % (self.name,)
        nbargs = len(self.cls.__init__.argtypes)
        args = ', '.join(['arg%d' % d for d in range(nbargs)])
        source = py.code.Source(r"""
            def %s(%s):
                obj = instantiate(cls)
                obj.__init__(%s)
                return obj
            """ % (self.constructor_name, args, args))
        miniglobals = {'cls': self.cls, 'instantiate': instantiate}
        exec source.compile() in miniglobals
        constructor = miniglobals[self.constructor_name]
        constructor._annspecialcase_ = 'specialize:ll'
        constructor._always_inline_ = True
        constructor.argtypes = self.cls.__init__.argtypes
        return constructor

    def save_repr(self, rtyper):
        bookkeeper = rtyper.annotator.bookkeeper
        classdef = bookkeeper.getuniqueclassdef(self.cls)
        self.classrepr = rtyper.getrepr(model.SomeInstance(classdef)
                                        ).lowleveltype
        
    def make_repr(self, module):
        """Returns the class repr, but also installs a Controller that
        will intercept all operations on the class."""
        STRUCTPTR = self.classrepr

        constructor = getattr(module, self.constructor_name)

        class ClassController(Controller):
            knowntype = STRUCTPTR

            def new(self, *args):
                return constructor(*args)

        class Entry(ControllerEntry):
            _about_ = STRUCTPTR
            _controller_ = ClassController

        return STRUCTPTR


class ModuleExportInfo:
    """Translates and builds a library, and returns an 'import Module'
    which can be used in another translation.

    Using this object will generate external calls to the low-level
    functions.
    """
    def __init__(self):
        self.functions = {}
        self.classes = {}

    def add_function(self, name, func):
        """Adds a function to export."""
        self.functions[name] = func

    def add_class(self, name, cls):
        """Adds a class to export."""
        self.classes[name] = ClassExportInfo(name, cls)

    def annotate(self, annotator):
        """Annotate all exported functions."""
        bk = annotator.bookkeeper

        # annotate constructors of exported classes
        for name, class_info in self.classes.items():
            constructor = class_info.make_constructor()
            self.functions[constructor.__name__] = constructor

        # annotate functions with signatures
        for name, func in self.functions.items():
            if hasattr(func, 'argtypes'):
                annotator.build_types(func, func.argtypes,
                                      complete_now=False)
        annotator.complete()

        # Ensure that functions without signature are not constant-folded
        for funcname, func in self.functions.items():
            if not hasattr(func, 'argtypes'):
                # build a list of arguments where constants are erased
                newargs = []
                desc = bk.getdesc(func)
                if isinstance(desc, description.FunctionDesc):
                    graph = desc.getuniquegraph()
                    for arg in graph.startblock.inputargs:
                        newarg = model.not_const(annotator.binding(arg))
                        newargs.append(newarg)
                    # and reflow
                    annotator.build_types(func, newargs)

    def get_lowlevel_functions(self, annotator):
        """Builds a map of low_level objects."""
        bk = annotator.bookkeeper

        exported_funcptr = {}
        for name, item in self.functions.items():
            desc = bk.getdesc(item)
            if isinstance(desc, description.FunctionDesc):
                graph = desc.getuniquegraph()
                funcptr = getfunctionptr(graph)
            else:
                raise NotImplementedError

            exported_funcptr[name] = funcptr
        return exported_funcptr

    def make_import_module(self, builder):
        """Builds an object with all exported functions."""
        rtyper = builder.db.translator.rtyper

        for clsname, class_info in self.classes.items():
            class_info.save_repr(rtyper)

        exported_funcptr = self.get_lowlevel_functions(
            builder.translator.annotator)
        # Map exported functions to the names given by the translator.
        node_names = dict(
            (funcname, builder.db.get(funcptr))
            for funcname, funcptr in exported_funcptr.items())

        # Declarations of functions defined in the first module.
        forwards = []
        for node in builder.db.globalcontainers():
            if node.nodekind == 'func' and node.name in node_names.values():
                forwards.append('\n'.join(node.forward_declaration()))

        so_name = py.path.local(builder.so_name)

        if sys.platform == 'win32':
            libraries = [so_name.purebasename]
        else:
            libraries = [so_name.purebasename[3:]]

        import_eci = ExternalCompilationInfo(
            libraries=libraries,
            library_dirs=[so_name.dirname],
            post_include_bits=forwards,
            )
        class Module(object):
            __file__ = builder.so_name
        mod = Module()
        for funcname, funcptr in exported_funcptr.items():
            import_name = node_names[funcname]
            func = make_llexternal_function(import_name, funcptr, import_eci)
            setattr(mod, funcname, func)
        for clsname, class_info in self.classes.items():
            structptr = class_info.make_repr(mod)
            setattr(mod, clsname, structptr)
            
        return mod

def make_ll_import_arg_converter(TARGET):
    from pypy.annotation import model

    def convert(x):
        UNUSED

    class Entry(ExtRegistryEntry):
        _about_ = convert

        def compute_result_annotation(self, s_arg):
            if not (isinstance(s_arg, SomeControlledInstance) and
                    s_arg.s_real_obj.ll_ptrtype == TARGET):
                raise TypeError("Expected a proxy for %s" % (TARGET,))
            return model.lltype_to_annotation(TARGET)

        def specialize_call(self, hop):
            [v_instance] = hop.inputargs(*hop.args_r)
            return hop.genop('force_cast', [v_instance],
                             resulttype=TARGET)

    return convert
make_ll_import_arg_converter._annspecialcase_ = 'specialize:memo'

def make_llexternal_function(name, funcptr, eci):
    functype = lltype.typeOf(funcptr)
    imported_func = rffi.llexternal(
        name, functype.TO.ARGS, functype.TO.RESULT,
        compilation_info=eci,
        )
    ARGS = functype.TO.ARGS
    unrolling_ARGS = unrolling_iterable(enumerate(ARGS))
    def wrapper(*args):
        real_args = ()
        for i, TARGET in unrolling_ARGS:
            arg = args[i]
            if isinstance(TARGET, lltype.Ptr): # XXX more precise check?
                arg = make_ll_import_arg_converter(TARGET)(arg)

            real_args = real_args + (arg,)
        res = imported_func(*real_args)
        return res
    wrapper._annspecialcase_ = 'specialize:ll'
    wrapper._always_inline_ = True
    return func_with_new_name(wrapper, name)

