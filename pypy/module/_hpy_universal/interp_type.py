from pypy.module._hpy_universal.apiset import API

@API.func("void *_HPy_Cast(HPyContext ctx, HPy h)")
def _HPy_Cast(space, ctx, h):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy _HPy_New(HPyContext ctx, HPy h_type, void **data)")
def _HPy_New(space, ctx, h_type, data):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPyType_FromSpec(HPyContext ctx, HPyType_Spec *spec)")
def HPyType_FromSpec(space, ctx, spec):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError
