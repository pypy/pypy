from pypy.rpython.memory import lladdress
from pypy.rpython.memory.lltypesimulation import simulatorptr, get_total_size
from pypy.rpython.memory.lltypesimulation import get_fixed_size
from pypy.rpython.memory.lltypesimulation import get_variable_size
from pypy.rpython.memory.lltypesimulation import primitive_to_fmt
from pypy.rpython.memory.lltypesimulation import get_layout
from pypy.objspace.flow.model import traverse, Link, Constant, Block
from pypy.objspace.flow.model import Constant
from pypy.rpython import lltype

import struct

class LLTypeConverter(object):
    def __init__(self, address):
        self.converted = {}
        self.curraddress = address

    def convert(self, val_or_ptr, inline_to_addr=None):
        TYPE = lltype.typeOf(val_or_ptr)
        if isinstance(TYPE, lltype.Primitive):
            if inline_to_addr is not None:
                inline_to_addr._store(primitive_to_fmt[TYPE], val_or_ptr)
            return val_or_ptr
        elif isinstance(TYPE, lltype.Array):
            return self.convert_array(val_or_ptr, inline_to_addr)
        elif isinstance(TYPE, lltype.Struct):
            return self.convert_struct(val_or_ptr, inline_to_addr)
        elif isinstance(TYPE, lltype.Ptr):
            return self.convert_pointer(val_or_ptr, inline_to_addr)
        elif isinstance(TYPE, lltype.OpaqueType):
            return self.convert_object(val_or_ptr, inline_to_addr)
        elif isinstance(TYPE, lltype.FuncType):
            return self.convert_object(val_or_ptr, inline_to_addr)
        elif isinstance(TYPE, lltype.PyObjectType):
            return self.convert_object(val_or_ptr, inline_to_addr)
        else:
            assert 0, "don't know about %s" % (val_or_ptr, )

    def convert_array(self, _array, inline_to_addr):
        if _array in self.converted:
            address = self.converted[_array]
            assert inline_to_addr is None or address == inline_to_addr
            return address
        TYPE = lltype.typeOf(_array)
        arraylength = len(_array.items)
        size = get_total_size(TYPE, arraylength)
        if inline_to_addr is not None:
            startaddr = inline_to_addr
        else:
            startaddr = self.curraddress
        self.converted[_array] = startaddr
        startaddr.signed[0] = arraylength
        curraddr = startaddr + get_fixed_size(TYPE)
        varsize = get_variable_size(TYPE)
        self.curraddress += size
        for item in _array.items:
            self.convert(item, curraddr)
            curraddr += varsize
        return startaddr

    def convert_struct(self, _struct, inline_to_addr):
        if _struct in self.converted:
            address = self.converted[_struct]
            assert inline_to_addr is None or address == inline_to_addr
            return address
        TYPE = lltype.typeOf(_struct)
        layout = get_layout(TYPE)
        if TYPE._arrayfld is not None:
            inlinedarraylength = len(getattr(_struct, TYPE._arrayfld).items)
            size = get_total_size(TYPE, inlinedarraylength)
        else:
            size = get_total_size(TYPE)
        if inline_to_addr is not None:
            startaddr = inline_to_addr
        else:
            startaddr = self.curraddress
        self.converted[_struct] = startaddr
        self.curraddress += size
        for name in TYPE._flds:
            addr = startaddr + layout[name]
            self.convert(getattr(_struct, name), addr)
        return startaddr

    def convert_pointer(self, _ptr, inline_to_addr):
        TYPE = lltype.typeOf(_ptr)
        if _ptr._obj is not None:
            addr = self.convert(_ptr._obj)
        else:
            addr = lladdress.NULL
        assert isinstance(addr, lladdress.Address)
        if inline_to_addr is not None:
            inline_to_addr.address[0] = addr
        return simulatorptr(TYPE, addr)

    def convert_object(self, _obj, inline_to_addr):
        if inline_to_addr is not None:
            inline_to_addr.attached[0] = _obj
            return inline_to_addr
        else:
            addr = self.curraddress
            addr.attached[0] = _obj
            self.curraddress += struct.calcsize("i")
            return addr

class FlowGraphConstantConverter(object):
    def __init__(self, flowgraphs):
        self.flowgraphs = flowgraphs
        self.memory = lladdress.NULL
        self.cvter = None
        self.total_size = 0

    def collect_constants(self):
        constants = {}
        def collect_args(args):
            for arg in args:
                if isinstance(arg, Constant):
                    constants[arg] = None
        def visit(obj):
            if isinstance(obj, Link):
                collect_args(obj.args)
            elif isinstance(obj, Block):
                for op in obj.operations:
                    collect_args(op.args)
        for graph in self.flowgraphs.itervalues():
            traverse(visit, graph)
        self.constants = constants

    def calculate_size(self):
        total_size = 0
        seen = {}
        candidates = [const.value for const in self.constants.iterkeys()]
        while candidates:
            cand = candidates.pop()
            if isinstance(cand, lltype._ptr):
                if cand:
                    candidates.append(cand._obj)
                continue
            elif isinstance(cand, lltype.LowLevelType):
                continue
            elif isinstance(cand, str):
                continue
            elif isinstance(lltype.typeOf(cand), lltype.Primitive):
                continue
            elif cand in seen:
                continue
            elif isinstance(cand, lltype._array):
                seen[cand] = True
                length = len(cand.items)
                total_size += get_total_size(cand._TYPE, length)
                for item in cand.items:
                    candidates.append(item)
            elif isinstance(cand, lltype._struct):
                seen[cand] = True
                TYPE = cand._TYPE
                if TYPE._arrayfld is not None:
                    total_size += get_total_size(
                        TYPE, len(getattr(cand, TYPE._arrayfld).items))
                else:
                    total_size += get_total_size(TYPE)
                for name in TYPE._flds:
                    candidates.append(getattr(cand, name))
            elif isinstance(cand, lltype._opaque):
                total_size += struct.calcsize("i")
            elif isinstance(cand, lltype._func):
                total_size += struct.calcsize("i")
            elif isinstance(cand, lltype._pyobject):
                total_size += struct.calcsize("i")
            else:
                assert 0, "don't know about %s %s" % (cand, cand.__class__)
        self.total_size = total_size

    def convert_constants(self):
        self.memory = lladdress.raw_malloc(self.total_size)
        self.cvter = LLTypeConverter(self.memory)
        for constant in self.constants.iterkeys():
            if isinstance(constant.value, lltype.LowLevelType):
                self.constants[constant] = constant.value
            elif isinstance(constant.value, str):
                self.constants[constant] = constant.value
            else:
                self.constants[constant] = self.cvter.convert(constant.value)

    def patch_graphs(self):
        def patch_consts(args):
            for arg in args:
                if isinstance(arg, Constant) and arg in self.constants:
                    arg.value = self.constants[arg]
        def visit(obj):
            if isinstance(obj, Link):
                patch_consts(obj.args)
            elif isinstance(obj, Block):
                for op in obj.operations:
                    patch_consts(op.args)
        for graph in self.flowgraphs.itervalues():
            traverse(visit, graph)

    def convert(self):
        self.collect_constants()
        self.calculate_size()
        self.convert_constants()
        self.patch_graphs()
