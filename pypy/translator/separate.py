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

def make_ll_import_function(name, functype, eci):
    from pypy.rpython.lltypesystem import lltype, rffi
    from pypy.annotation import model

    imported_func = rffi.llexternal(
        name, functype.TO.ARGS, functype.TO.RESULT,
        compilation_info=eci,
        )

    if not functype.TO.ARGS:
        func = imported_func
    elif len(functype.TO.ARGS) == 1:
        ARG = functype.TO.ARGS[0]
        from pypy.rpython.lltypesystem import llmemory
        from pypy.rpython.extregistry import ExtRegistryEntry

        if isinstance(ARG, lltype.Ptr): # XXX more precise check?
            def convert(x):
                raiseNameError

            class Entry(ExtRegistryEntry):
                _about_ = convert
                s_result_annotation = model.lltype_to_annotation(ARG)

                def specialize_call(self, hop):
                    # TODO: input type check
                    [v_instance] = hop.inputargs(*hop.args_r)
                    return hop.genop('force_cast', [v_instance],
                                     resulttype = ARG)
        else:
            def convert(x):
                return x

        def func(arg0):
            ll_arg0 = convert(arg0)
            ll_res = imported_func(ll_arg0)
            return ll_res
    else:
        raise NotImplementedError("Not supported")
    return func

