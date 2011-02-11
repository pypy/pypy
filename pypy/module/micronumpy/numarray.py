
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.rpython.lltypesystem import lltype
from pypy.rlib import jit

TP = lltype.GcArray(lltype.Float)

numpy_driver = jit.JitDriver(greens = ['bytecode_pos', 'bytecode'],
                             reds = ['result_size', 'i', 'frame',
                                     'result'],
                             virtualizables = ['frame'])

class ComputationFrame(object):
    _virtualizable2_ = ['valuestackdepth', 'valuestack[*]', 'local_pos',
                        'locals[*]']
    
    def __init__(self, input):
        self.valuestackdepth = 0
        self.valuestack = [0.0] * len(input)
        self.locals = input[:]
        self.local_pos = len(input)

    def getlocal(self):
        p = self.local_pos - 1
        assert p >= 0
        res = self.locals[p]
        self.local_pos = p
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

def compute(bytecode, input):
    result_size = input[0].size
    result = SingleDimArray(result_size)
    bytecode_pos = len(bytecode) - 1
    i = 0
    frame = ComputationFrame(input)
    while i < result_size:
        numpy_driver.jit_merge_point(bytecode=bytecode, result=result,
                                     result_size=result_size,
                                     i=i, frame=frame,
                                     bytecode_pos=bytecode_pos)
        if bytecode_pos == -1:
            bytecode_pos = len(bytecode) - 1
            frame.local_pos = len(frame.locals)
            result.storage[i] = frame.valuestack[0]
            frame.valuestackdepth = 0
            i += 1
            numpy_driver.can_enter_jit(bytecode=bytecode, result=result,
                                       result_size=result_size,
                                       i=i, frame=frame,
                                       bytecode_pos=bytecode_pos)
        else:
            opcode = bytecode[bytecode_pos]
            if opcode == 'l':
                val = frame.getlocal().storage[i]
                frame.valuestack[frame.valuestackdepth] = val
                frame.valuestackdepth += 1
            elif opcode == 'a':
                b = frame.popvalue()
                a = frame.popvalue()
                frame.pushvalue(a + b)
            else:
                raise NotImplementedError
            bytecode_pos -= 1
    return result

    
class BaseArray(Wrappable):
    def force(self):
        bytecode, stack = self.compile()
        return compute(bytecode, stack)
    force.unwrap_spec = ['self']

    def descr_add(self, space, w_other):
        return space.wrap(Add(self, w_other))
    descr_add.unwrap_spec = ['self', ObjSpace, W_Root]

    def compile(self):
        raise NotImplementedError("abstract base class")

class Add(BaseArray):
    def __init__(self, left, right):
        assert isinstance(left, BaseArray)
        assert isinstance(right, BaseArray)
        self.left = left
        self.right = right

    def compile(self):
        left_bc, left_stack = self.left.compile()
        right_bc, right_stack = self.right.compile()
        return 'a' + left_bc + right_bc, left_stack + right_stack

BaseArray.typedef = TypeDef(
    'Operation',
    force=interp2app(BaseArray.force),
    __add__ = interp2app(BaseArray.descr_add),
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
    __add__ = interp2app(BaseArray.descr_add),
    force = interp2app(SingleDimArray.force),
)

