from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rlib import jit
from pypy.rlib.nonconst import NonConstant
from pypy.rpython.lltypesystem import lltype
from pypy.tool.sourcetools import func_with_new_name


TP = lltype.Array(lltype.Float, hints={'nolength': True})

numpy_driver = jit.JitDriver(greens = ['bytecode_pos', 'bytecode'],
                             reds = ['result_size', 'i', 'frame',
                                     'result'],
                             virtualizables = ['frame'])

class ComputationFrame(object):
    _virtualizable2_ = ['valuestackdepth', 'valuestack[*]',
                        'array_pos', 'arrays[*]',
                        'float_pos', 'floats[*]',
                        ]

    def __init__(self, arrays, floats):
        self = jit.hint(self, access_directly=True, fresh_virtualizable=True)
        self.valuestackdepth = 0
        self.arrays = arrays
        self.array_pos = len(arrays)
        self.floats = floats
        if NonConstant(0):
            self.floats = [3.5] # annotator hack for test_jit
        self.float_pos = len(floats)
        self.valuestack = [0.0] * (len(arrays) + len(floats))

    def reset(self):
        self.valuestackdepth = 0
        self.array_pos = len(self.arrays)
        self.float_pos = len(self.floats)

    def getarray(self):
        p = self.array_pos - 1
        assert p >= 0
        res = self.arrays[p]
        self.array_pos = p
        return res

    def getfloat(self):
        p = self.float_pos - 1
        assert p >= 0
        res = self.floats[p]
        self.float_pos = p
        return res

    def popvalue(self):
        v = self.valuestackdepth - 1
        assert v >= 0
        res = self.valuestack[v]
        self.valuestackdepth = v
        return res

    def pushvalue(self, v):
        self.valuestack[self.valuestackdepth] = v
        self.valuestackdepth += 1

class Code(object):
    """
    A chunk of bytecode.
    """

    def __init__(self, bytecode, arrays, floats):
        self.bytecode = bytecode
        self.arrays = arrays
        self.floats = floats

    def merge(self, code, other):
        """
        Merge this bytecode with the other bytecode, using ``code`` as the
        bytecode instruction for performing the merge.
        """

        return Code(code + self.bytecode + other.bytecode,
            self.arrays + other.arrays,
            self.floats + other.floats)

def compute(code):
    """
    Crunch a ``Code`` full of bytecode.
    """

    bytecode = code.bytecode
    result_size = code.arrays[0].size
    result = SingleDimArray(result_size)
    bytecode_pos = len(bytecode) - 1
    i = 0
    frame = ComputationFrame(code.arrays, code.floats)
    while i < result_size:
        numpy_driver.jit_merge_point(bytecode=bytecode, result=result,
                                     result_size=result_size,
                                     i=i, frame=frame,
                                     bytecode_pos=bytecode_pos)
        if bytecode_pos == -1:
            bytecode_pos = len(bytecode) - 1
            frame.reset()
            result.storage[i] = frame.valuestack[0]
            i += 1
            numpy_driver.can_enter_jit(bytecode=bytecode, result=result,
                                       result_size=result_size,
                                       i=i, frame=frame,
                                       bytecode_pos=bytecode_pos)
        else:
            opcode = bytecode[bytecode_pos]
            if opcode == 'l':
                # Load array.
                val = frame.getarray().storage[i]
                frame.pushvalue(val)
            elif opcode == 'f':
                # Load float.
                val = frame.getfloat()
                frame.pushvalue(val)
            elif opcode == 'a':
                # Add.
                a = frame.popvalue()
                b = frame.popvalue()
                frame.pushvalue(a + b)
            elif opcode == 's':
                # Subtract
                a = frame.popvalue()
                b = frame.popvalue()
                frame.pushvalue(a - b)
            elif opcode == 'm':
                # Multiply.
                a = frame.popvalue()
                b = frame.popvalue()
                frame.pushvalue(a * b)
            elif opcode == 'd':
                a = frame.popvalue()
                b = frame.popvalue()
                frame.pushvalue(a / b)
            else:
                raise NotImplementedError(
                    "Can't handle bytecode instruction %s" % opcode)
            bytecode_pos -= 1
    return result

JITCODES = {}

class BaseArray(Wrappable):
    def __init__(self):
        self.invalidates = []

    def force(self):
        code = self.compile()
        try:
            code.bytecode = JITCODES[code.bytecode]
        except KeyError:
            JITCODES[code.bytecode] = code.bytecode
        # the point of above hacks is to intern the bytecode string
        # otherwise we have to compile new assembler each time, which sucks
        # (we still have to compile new bytecode, but too bad)
        return compute(code)

    def invalidated(self):
        for arr in self.invalidates:
            arr.force_if_needed()
        self.invalidates = []

    def _binop_impl(bytecode):
        def impl(self, space, w_other):
            if isinstance(w_other, BaseArray):
                res = space.wrap(BinOp(bytecode, self, w_other))
                w_other.invalidates.append(res)
            else:
                res = space.wrap(BinOp(
                    bytecode,
                    self,
                    FloatWrapper(space.float_w(w_other))
                ))
            self.invalidates.append(res)
            return res
        return func_with_new_name(impl, "binop_%s_impl" % bytecode)

    descr_add = _binop_impl("a")
    descr_sub = _binop_impl("s")
    descr_mul = _binop_impl("m")
    descr_div = _binop_impl("d")

    def compile(self):
        raise NotImplementedError("abstract base class")

class FloatWrapper(BaseArray):
    """
    Intermediate class representing a float literal.
    """

    def __init__(self, float_value):
        BaseArray.__init__(self)
        self.float_value = float_value

    def compile(self):
        return Code('f', [], [self.float_value])

class BinOp(BaseArray):
    """
    Intermediate class for performing binary operations.
    """

    def __init__(self, opcode, left, right):
        BaseArray.__init__(self)
        self.opcode = opcode
        self.left = left
        self.right = right

        self.forced_result = None

    def compile(self):
        if self.forced_result is not None:
            return self.forced_result.compile()

        left_code = self.left.compile()
        right_code = self.right.compile()
        return left_code.merge(self.opcode, right_code)

    def force_if_needed(self):
        if self.forced_result is None:
            self.forced_result = self.force()

    @unwrap_spec(item=int)
    def descr_getitem(self, space, item):
        self.force_if_needed()
        return self.forced_result.descr_getitem(space, item)

    @unwrap_spec(item=int, value=float)
    def descr_setitem(self, space, item, value):
        self.forced_if_needed()
        self.invalidated()
        return self.forced_result.descr_setitem(space, item, value)


BinOp.typedef = TypeDef(
    'Operation',
    __getitem__ = interp2app(BinOp.descr_getitem),
    __setitem__ = interp2app(BinOp.descr_setitem),

    __add__ = interp2app(BaseArray.descr_add),
    __sub__ = interp2app(BaseArray.descr_sub),
    __mul__ = interp2app(BaseArray.descr_mul),
    __div__ = interp2app(BaseArray.descr_div),
)

class SingleDimArray(BaseArray):
    def __init__(self, size):
        BaseArray.__init__(self)
        self.size = size
        self.storage = lltype.malloc(TP, size, zero=True,
                                     flavor='raw', track_allocation=False)
        # XXX find out why test_jit explodes with trackign of allocations

    def compile(self):
        return Code('l', [self], [])

    @unwrap_spec(item=int)
    def descr_getitem(self, space, item):
        if item < 0:
            raise operationerrfmt(space.w_TypeError,
              '%d below zero', item)
        if item > self.size:
            raise operationerrfmt(space.w_TypeError,
              '%d above array size', item)
        return space.wrap(self.storage[item])

    @unwrap_spec(item=int, value=float)
    def descr_setitem(self, space, item, value):
        if item < 0:
            raise operationerrfmt(space.w_TypeError,
              '%d below zero', item)
        if item > self.size:
            raise operationerrfmt(space.w_TypeError,
              '%d above array size', item)
        self.invalidated()
        self.storage[item] = value

    def __del__(self):
        lltype.free(self.storage, flavor='raw')

def descr_new_numarray(space, w_type, w_size_or_iterable):
    l = space.listview(w_size_or_iterable)
    arr = SingleDimArray(len(l))
    i = 0
    for w_elem in l:
        arr.storage[i] = space.float_w(space.float(w_elem))
        i += 1
    return space.wrap(arr)

@unwrap_spec(ObjSpace, int)
def zeros(space, size):
    return space.wrap(SingleDimArray(size))


SingleDimArray.typedef = TypeDef(
    'numarray',
    __new__ = interp2app(descr_new_numarray),
    __getitem__ = interp2app(SingleDimArray.descr_getitem),
    __setitem__ = interp2app(SingleDimArray.descr_setitem),
    __add__ = interp2app(BaseArray.descr_add),
    __sub__ = interp2app(BaseArray.descr_sub),
    __mul__ = interp2app(BaseArray.descr_mul),
    __div__ = interp2app(BaseArray.descr_div),
)