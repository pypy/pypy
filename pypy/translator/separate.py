from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.extregistry import ExtRegistryEntry
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

def is_exported(obj):
    return (isinstance(obj, (types.FunctionType, types.UnboundMethodType))
            and getattr(obj, 'exported', False))

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

