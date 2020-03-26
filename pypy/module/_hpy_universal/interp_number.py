from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles


@API.func("HPy HPy_Add(HPyContext ctx, HPy x, HPy y)")
def HPy_Add(space, ctx, h1, h2):
    w_obj1 = handles.deref(space, h1)
    w_obj2 = handles.deref(space, h2)
    w_result = space.add(w_obj1, w_obj2)
    return handles.new(space, w_result)

def make_unary(name, spacemeth):
    assert spacemeth.startswith('space.')
    spacemeth = spacemeth[len('space.'):]
    #
    @API.func("HPy HPy_unary(HPyContext ctx, HPy h1)", func_name=name)
    def HPy_unary(space, ctx, h1):
        w_obj1 = handles.deref(space, h1)
        meth = getattr(space, spacemeth)
        w_res = meth(w_obj1)
        return handles.new(space, w_res)
    #
    globals()[name] = HPy_unary

make_unary('HPy_Negative', 'space.neg')
make_unary('HPy_Positive', 'space.pos')
make_unary('HPy_Absolute', 'space.abs')
make_unary('HPy_Invert', 'space.invert')
make_unary('HPy_Index', 'space.index')

@API.func("HPy HPy_Long(HPyContext ctx, HPy h1)")
def HPy_Long(space, ctx, h1):
    w_obj1 = handles.deref(space, h1)
    w_res = space.call_function(space.w_int, w_obj1)
    return handles.new(space, w_res)


@API.func("HPy HPy_Float(HPyContext ctx, HPy h1)")
def HPy_Float(space, ctx, h1):
    w_obj1 = handles.deref(space, h1)
    w_res = space.call_function(space.w_float, w_obj1)
    return handles.new(space, w_res)


@API.func("HPy HPy_Subtract(HPyContext ctx, HPy h1, HPy h2)")
def HPy_Subtract(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_Multiply(HPyContext ctx, HPy h1, HPy h2)")
def HPy_Multiply(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_MatrixMultiply(HPyContext ctx, HPy h1, HPy h2)")
def HPy_MatrixMultiply(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_FloorDivide(HPyContext ctx, HPy h1, HPy h2)")
def HPy_FloorDivide(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_TrueDivide(HPyContext ctx, HPy h1, HPy h2)")
def HPy_TrueDivide(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_Remainder(HPyContext ctx, HPy h1, HPy h2)")
def HPy_Remainder(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_Divmod(HPyContext ctx, HPy h1, HPy h2)")
def HPy_Divmod(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_Power(HPyContext ctx, HPy h1, HPy h2, HPy h3)")
def HPy_Power(space, ctx, h1, h2, h3):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError



@API.func("HPy HPy_Lshift(HPyContext ctx, HPy h1, HPy h2)")
def HPy_Lshift(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_Rshift(HPyContext ctx, HPy h1, HPy h2)")
def HPy_Rshift(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_And(HPyContext ctx, HPy h1, HPy h2)")
def HPy_And(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_Xor(HPyContext ctx, HPy h1, HPy h2)")
def HPy_Xor(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_Or(HPyContext ctx, HPy h1, HPy h2)")
def HPy_Or(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError


@API.func("HPy HPy_InPlaceAdd(HPyContext ctx, HPy h1, HPy h2)")
def HPy_InPlaceAdd(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_InPlaceSubtract(HPyContext ctx, HPy h1, HPy h2)")
def HPy_InPlaceSubtract(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_InPlaceMultiply(HPyContext ctx, HPy h1, HPy h2)")
def HPy_InPlaceMultiply(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_InPlaceMatrixMultiply(HPyContext ctx, HPy h1, HPy h2)")
def HPy_InPlaceMatrixMultiply(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_InPlaceFloorDivide(HPyContext ctx, HPy h1, HPy h2)")
def HPy_InPlaceFloorDivide(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_InPlaceTrueDivide(HPyContext ctx, HPy h1, HPy h2)")
def HPy_InPlaceTrueDivide(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_InPlaceRemainder(HPyContext ctx, HPy h1, HPy h2)")
def HPy_InPlaceRemainder(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_InPlacePower(HPyContext ctx, HPy h1, HPy h2, HPy h3)")
def HPy_InPlacePower(space, ctx, h1, h2, h3):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_InPlaceLshift(HPyContext ctx, HPy h1, HPy h2)")
def HPy_InPlaceLshift(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_InPlaceRshift(HPyContext ctx, HPy h1, HPy h2)")
def HPy_InPlaceRshift(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_InPlaceAnd(HPyContext ctx, HPy h1, HPy h2)")
def HPy_InPlaceAnd(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_InPlaceXor(HPyContext ctx, HPy h1, HPy h2)")
def HPy_InPlaceXor(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPy_InPlaceOr(HPyContext ctx, HPy h1, HPy h2)")
def HPy_InPlaceOr(space, ctx, h1, h2):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError
