
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.rpython.lltypesystem import lltype
from pypy.rlib import jit

TP = lltype.GcArray(lltype.Float)

numpy_driver = jit.JitDriver(greens = ['bytecode'],
                             reds = ['result', 'result_size', 'i',
                                     'valuestack', 'valuestackdepth',
                                     'input', 'input_pos'])

def compute(bytecode, input):
    result_size = input[0].size
    result = SingleDimArray(result_size)
    bytecode_pos = len(bytecode) - 1
    input_pos = len(input) - 1
    valuestack = [0.0] * len(input)
    valuestackdepth = 0
    i = 0
    while i < result_size:
        numpy_driver.jit_merge_point(bytecode=bytecode, result=result,
                                     result_size=result_size,
                                     valuestackdepth=valuestackdepth,
                                     valuestack=valuestack,
                                     input=input, input_pos=input_pos, i=i)
        if bytecode_pos == -1:
            bytecode_pos = len(bytecode) - 1
            input_pos = len(input) - 1
            result.storage[i] = valuestack[0]
            valuestack = [0.0] * len(input)
            valuestackdepth = 0
            i += 1
            numpy_driver.can_enter_jit(bytecode=bytecode, result=result,
                                       result_size=result_size,
                                       valuestackdepth=valuestackdepth,
                                       valuestack=valuestack,
                                       input=input, input_pos=input_pos, i=i)
        else:
            opcode = bytecode[bytecode_pos]
            if opcode == 'l':
                valuestack[valuestackdepth] = input[input_pos].storage[i]
                valuestackdepth += 1
                input_pos -= 1
            elif opcode == 'a':
                a = valuestack[valuestackdepth - 1]
                b = valuestack[valuestackdepth - 2]
                valuestack[valuestackdepth - 2] = a + b
                valuestackdepth -= 1
            else:
                raise NotImplementedError
            bytecode_pos -= 1
    return result
    
class BaseArray(Wrappable):
    def force(self):
        bytecode, stack = self.compile()
        return compute(bytecode, stack)
    force.unwrap_spec = ['self']

    def compile(self):
        raise NotImplementedError("abstract base class")

class Add(BaseArray):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def compile(self):
        left_bc, left_stack = self.left.compile()
        right_bc, right_stack = self.right.compile()
        return 'a' + left_bc + right_bc, left_stack + right_stack

BaseArray.typedef = TypeDef(
    'Operation',
    force=interp2app(BaseArray.force),
)

class SingleDimArray(BaseArray):
    def __init__(self, size):
        self.size = size
        self.storage = lltype.malloc(TP, size, zero=True)

    def compile(self):
        return "l", [self]

    def descr_getitem(self, space, item):
        if item < 0:
            raise operationerrfmt(space.w_TypeError,
              '%d below zero', item)
        if item > self.size:
            raise operationerrfmt(space.w_TypeError,
              '%d above array size', item)
        return space.wrap(self.storage[item])
    descr_getitem.unwrap_spec = ['self', ObjSpace, int]

    def descr_setitem(self, space, item, value):
        if item < 0:
            raise operationerrfmt(space.w_TypeError,
              '%d below zero', item)
        if item > self.size:
            raise operationerrfmt(space.w_TypeError,
              '%d above array size', item)
        self.storage[item] = value
    descr_setitem.unwrap_spec = ['self', ObjSpace, int, float]

    def descr_add(self, space, w_other):
        return space.wrap(Add(self, w_other))
    descr_add.unwrap_spec = ['self', ObjSpace, W_Root]

    def force(self):
        return self

def descr_new_numarray(space, w_type, w_size_or_iterable):
    if space.isinstance_w(w_size_or_iterable, space.w_int):
        arr = SingleDimArray(space.int_w(w_size_or_iterable))
    else:
        l = space.listview(w_size_or_iterable)
        arr = SingleDimArray(len(l))
        i = 0
        for w_elem in l:
            arr.storage[i] = space.float_w(space.float(w_elem))
            i += 1
    return space.wrap(arr)
descr_new_numarray.unwrap_spec = [ObjSpace, W_Root, W_Root]

SingleDimArray.typedef = TypeDef(
    'numarray',
    __new__ = interp2app(descr_new_numarray),
    __getitem__ = interp2app(SingleDimArray.descr_getitem),
    __setitem__ = interp2app(SingleDimArray.descr_setitem),
    __add__ = interp2app(SingleDimArray.descr_add),
    force = interp2app(SingleDimArray.force),
)

