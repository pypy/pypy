from pypy.annotation import model, description
from pypy.annotation.signature import annotation
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.controllerentry import (
    Controller, ControllerEntry, SomeControlledInstance)
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.extfunc import ExtFuncEntry
from pypy.rlib.objectmodel import instantiate, specialize
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


class FunctionExportInfo:
    def __init__(self, name, func):
        self.name = name
        self.func = func

    def save_repr(self, builder):
        bk = builder.translator.annotator.bookkeeper
        desc = bk.getdesc(self.func)
        if isinstance(desc, description.FunctionDesc):
            graph = desc.getuniquegraph()
            funcptr = getfunctionptr(graph)
        else:
            raise NotImplementedError
        self.external_name = builder.db.get(funcptr)
        self.functype = lltype.typeOf(funcptr)

    def register_external(self, eci):
        llimpl = self.make_llexternal_function(eci)
        functype = self.functype
        class FuncEntry(ExtFuncEntry):
            _about_ = self.func
            name = self.name
            def normalize_args(self, *args_s):
                return args_s    # accept any argument unmodified
            signature_result = annotation(functype.TO.RESULT)
            lltypeimpl = staticmethod(llimpl)
            
        return llimpl

    def make_llexternal_function(self, eci):
        functype = self.functype
        imported_func = rffi.llexternal(
            self.external_name, functype.TO.ARGS, functype.TO.RESULT,
            compilation_info=eci,
            )
        ARGS = functype.TO.ARGS
        unrolling_ARGS = unrolling_iterable(enumerate(ARGS))
        def wrapper(*args):
            real_args = ()
            for i, TARGET in unrolling_ARGS:
                arg = args[i]
                if isinstance(TARGET, lltype.Ptr): # XXX more precise check?
                    arg = self.make_ll_import_arg_converter(TARGET)(arg)

                real_args = real_args + (arg,)
            res = imported_func(*real_args)
            return res
        wrapper._always_inline_ = True
        return func_with_new_name(wrapper, self.external_name)

    @staticmethod
    @specialize.memo()
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
        constructor._always_inline_ = True
        constructor.argtypes = self.cls.__init__.argtypes
        return constructor

    def save_repr(self, builder):
        rtyper = builder.db.translator.rtyper
        bookkeeper = rtyper.annotator.bookkeeper
        self.classdef = bookkeeper.getuniqueclassdef(self.cls)
        self.classrepr = rtyper.getrepr(model.SomeInstance(self.classdef)
                                        ).lowleveltype
        
    def make_controller(self, module):
        """Returns the class repr, but also installs a Controller that
        will intercept all operations on the class."""
        STRUCTPTR = self.classrepr

        constructor = getattr(module, self.constructor_name)

        class ClassController(Controller):
            knowntype = STRUCTPTR

            def new(self, *args):
                return constructor(*args)

        def install_attribute(name):
            def getter(self, obj):
                return getattr(obj, 'inst_' + name)
            setattr(ClassController, 'get_' + name, getter)
            def setter(self, obj, value):
                return getattr(obj, 'inst_' + name, value)
            setattr(ClassController, 'set_' + name, getter)
        for name, attrdef in self.classdef.attrs.items():
            install_attribute(name)

        class Entry(ControllerEntry):
            _about_ = self.cls
            _controller_ = ClassController

        return self.cls


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
        self.functions[name] = FunctionExportInfo(name, func)

    def add_class(self, name, cls):
        """Adds a class to export."""
        self.classes[name] = ClassExportInfo(name, cls)

    def annotate(self, annotator):
        """Annotate all exported functions."""
        bk = annotator.bookkeeper

        # annotate constructors of exported classes
        for name, class_info in self.classes.items():
            constructor = class_info.make_constructor()
            self.add_function(constructor.__name__, constructor)

        # annotate functions with signatures
        for name, func_info in self.functions.items():
            func = func_info.func
            if hasattr(func, 'argtypes'):
                annotator.build_types(func, func.argtypes,
                                      complete_now=False)
        annotator.complete()

        # Ensure that functions without signature are not constant-folded
        for name, func_info in self.functions.items():
            func = func_info.func
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

    def make_import_module(self, builder):
        """Builds an object with all exported functions."""
        for name, class_info in self.classes.items():
            class_info.save_repr(builder)
        for name, func_info in self.functions.items():
            func_info.save_repr(builder)

        # Declarations of functions defined in the first module.
        forwards = []
        node_names = set(func_info.external_name
                         for func_info in self.functions.values())
        for node in builder.db.globalcontainers():
            if node.nodekind == 'func' and node.name in node_names:
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
        for name, func_info in self.functions.items():
            funcptr = func_info.register_external(import_eci)
            setattr(mod, name, funcptr)
        for name, class_info in self.classes.items():
            structptr = class_info.make_controller(mod)
            setattr(mod, name, structptr)
            
        return mod

