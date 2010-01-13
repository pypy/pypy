from pypy.annotation import model, description
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.unroll import unrolling_iterable
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.extregistry import ExtRegistryEntry

import types

def annotate_exported_functions(annotator, exports):
    bk = annotator.bookkeeper

    # annotate functions with signatures
    for funcname, func in exports.items():
        if hasattr(func, 'argtypes'):
            annotator.build_types(func, func.argtypes,
                                  complete_now=False)
    # annotate classes
    for funcname, cls in exports.items():
        if not isinstance(cls, (type, types.ClassType)):
            continue
        desc = bk.getdesc(cls)
        classdef = desc.getuniqueclassdef()
        s_init = desc.s_read_attribute('__init__')
        if isinstance(s_init, model.SomeImpossibleValue):
            continue

        argtypes = (model.SomeInstance(classdef),)
        argtypes += tuple(cls.__init__.argtypes)
        annotator.build_types(cls.__init__.im_func, argtypes,
                              complete_now=False)

    annotator.complete()

    # ensure that functions without signature are not constant-folded
    for funcname, func in exports.items():
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

def get_exported_functions(annotator, exports):
    bk = annotator.bookkeeper

    exported_funcptr = {}
    for funcname, func in exports.items():
        desc = bk.getdesc(func)
        if not isinstance(desc, description.FunctionDesc):
            continue
        graph = desc.getuniquegraph()
        funcptr = getfunctionptr(graph)

        exported_funcptr[funcname] = funcptr
    return exported_funcptr

def make_import_module(builder):
    class Module:
        pass
    mod = Module()
    mod.__file__ = builder.so_name

    forwards = []
    node_names = builder.export_node_names.values()
    for node in builder.db.globalcontainers():
        if node.nodekind == 'func' and node.name in node_names:
            forwards.append('\n'.join(node.forward_declaration()))

    import_eci = ExternalCompilationInfo(
        libraries = [builder.so_name],
        post_include_bits = forwards
        )

    for funcname, import_name in builder.export_node_names.items():
        functype = lltype.typeOf(builder.entrypoint[funcname])
        func = make_ll_import_function(import_name, functype, import_eci)
        setattr(mod, funcname, func)
    return mod

def make_ll_import_arg_converter(TARGET):
    from pypy.annotation import model

    def convert(x):
        XXX

    class Entry(ExtRegistryEntry):
        _about_ = convert
        s_result_annotation = model.lltype_to_annotation(TARGET)

        def specialize_call(self, hop):
            # TODO: input type check
            [v_instance] = hop.inputargs(*hop.args_r)
            return hop.genop('force_cast', [v_instance],
                             resulttype=TARGET)

    return convert
make_ll_import_arg_converter._annspecialcase_ = 'specialize:memo'

def make_ll_import_function(name, functype, eci):
    from pypy.rpython.lltypesystem import lltype, rffi

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

