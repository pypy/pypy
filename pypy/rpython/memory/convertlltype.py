from pypy.rpython.memory import lladdress
from pypy.rpython.memory.lltypesimulation import simulatorptr, sizeof
from pypy.rpython.memory.lltypesimulation import nullptr, malloc
from pypy.rpython.memory.lltypesimulation import init_object_on_address
from pypy.objspace.flow.model import traverse, Link, Constant, Block
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype

from pypy.rpython.rmodel import IntegerRepr

import types

FUNCTIONTYPES = (types.FunctionType, types.UnboundMethodType,
                 types.BuiltinFunctionType)

class LLTypeConverter(object):
    def __init__(self, address, gc=None, qt=None):
        self.type_to_typeid = {}
        self.types = []
        self.converted = {}
        self.curraddress = address
        self.constantroots = []
        self.gc = gc
        self.query_types = qt

    def convert(self, val_or_ptr, inline_to_ptr=None):
        TYPE = lltype.typeOf(val_or_ptr)
        if isinstance(TYPE, lltype.Primitive):
            assert inline_to_ptr is None
            return val_or_ptr
        elif isinstance(TYPE, lltype.Array):
            return self.convert_array(val_or_ptr, inline_to_ptr)
        elif isinstance(TYPE, lltype.Struct):
            return self.convert_struct(val_or_ptr, inline_to_ptr)
        elif isinstance(TYPE, lltype.Ptr):
            return self.convert_pointer(val_or_ptr, inline_to_ptr)
        elif isinstance(TYPE, lltype.OpaqueType):
            return self.convert_object(val_or_ptr, inline_to_ptr)
        elif isinstance(TYPE, lltype.FuncType):
            return self.convert_object(val_or_ptr, inline_to_ptr)
        elif isinstance(TYPE, lltype.PyObjectType):
            return self.convert_object(val_or_ptr, inline_to_ptr)
        else:
            assert 0, "don't know about %s" % (val_or_ptr, )

    def convert_array(self, _array, inline_to_ptr):
        if _array in self.converted:
            ptr = self.converted[_array]
            assert inline_to_ptr is None or ptr == inline_to_ptr
            return ptr
        TYPE = lltype.typeOf(_array)
        arraylength = len(_array.items)
        size = sizeof(TYPE, arraylength)
        if inline_to_ptr is not None:
            ptr = inline_to_ptr
        else:
            startaddr = self.curraddress
            self.curraddress += size
            if self.gc is not None:
                typeid = self.query_types.get_typeid(TYPE)
                self.gc.init_gc_object_immortal(startaddr, typeid)
                startaddr += self.gc.size_gc_header(typeid)
                self.curraddress += self.gc.size_gc_header(typeid)
            ptr = init_object_on_address(startaddr, TYPE, arraylength)
            self.constantroots.append(ptr)
        self.converted[_array] = ptr
        if isinstance(TYPE.OF, lltype.Struct):
            for i, item in enumerate(_array.items):
                self.convert(item, ptr[i])
        else:
            for i, item in enumerate(_array.items):
                ptr[i] = self.convert(item)
        return ptr

    def convert_struct(self, _struct, inline_to_ptr):
        if _struct in self.converted:
            ptr = self.converted[_struct]
            assert inline_to_ptr is None or ptr == inline_to_ptr
            return ptr
        parent = _struct._parentstructure()
        if parent is not None and inline_to_ptr is None:
            ptr = self.convert(parent)
            if isinstance(_struct._parent_index, str):
                return getattr(ptr, _struct._parent_index)
            else:
                return ptr[_struct._parent_index]
        TYPE = lltype.typeOf(_struct)
        if TYPE._arrayfld is not None:
            inlinedarraylength = len(getattr(_struct, TYPE._arrayfld).items)
            size = sizeof(TYPE, inlinedarraylength)
        else:
            inlinedarraylength = None
            size = sizeof(TYPE)
        if inline_to_ptr is not None:
            ptr = inline_to_ptr
        else:
            startaddr = self.curraddress
            self.curraddress += size
            if self.gc is not None:
                typeid = self.query_types.get_typeid(TYPE)
                self.gc.init_gc_object_immortal(startaddr, typeid)
                startaddr += self.gc.size_gc_header(typeid)
                self.curraddress += self.gc.size_gc_header(typeid)
            ptr = init_object_on_address(startaddr, TYPE, inlinedarraylength)
            self.constantroots.append(ptr)
        self.converted[_struct] = ptr
        for name in TYPE._flds:
            FIELD = getattr(TYPE, name)
            if isinstance(FIELD, (lltype.Struct, lltype.Array)):
                self.convert(getattr(_struct, name), getattr(ptr, name))
            else:
                setattr(ptr, name, self.convert(getattr(_struct, name)))
        return ptr

    def convert_pointer(self, _ptr, inline_to_ptr):
        assert inline_to_ptr is None, "can't inline pointer"
        TYPE = lltype.typeOf(_ptr)
        if _ptr._obj is not None:
            return self.convert(_ptr._obj)
        else:
            return nullptr(TYPE.TO)

    def convert_object(self, _obj, inline_to_ptr):
        assert inline_to_ptr is None, "can't inline function or pyobject"
        return simulatorptr(lltype.Ptr(lltype.typeOf(_obj)),
                            lladdress.get_address_of_object(_obj))

class FlowGraphConstantConverter(object):
    def __init__(self, graphs, gc=None, qt=None):
        self.graphs = graphs
        self.memory = lladdress.NULL
        self.cvter = None
        self.total_size = 0
        self.gc = gc
        self.query_types = qt

    def collect_constants_and_types(self):
        constants = {}
        types = {}
        def collect_args(args):
            for arg in args:
                if (isinstance(arg, Constant) and
                    arg.concretetype is not lltype.Void):
                    constants[arg] = None
                    types[arg.concretetype] = True
        def visit(obj):
            if isinstance(obj, Link):
                collect_args(obj.args)
                if hasattr(obj, "llexitcase"):
                    if isinstance(obj.llexitcase, IntegerRepr):
                        assert 0
                    constants[Constant(obj.llexitcase)] = None
            elif isinstance(obj, Block):
                for op in obj.operations:
                    collect_args(op.args)
                    if op.opname in ("malloc", "malloc_varsize"):
                        types[op.args[0].value] = True
        for graph in self.graphs:
            traverse(visit, graph)
        self.constants = constants
        self.types = types

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
            elif isinstance(cand, FUNCTIONTYPES):
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
                total_size += sizeof(cand._TYPE, length)
                if self.gc is not None:
                    typeid = self.query_types.get_typeid(cand._TYPE)
                    total_size += self.gc.size_gc_header(typeid)
                for item in cand.items:
                    candidates.append(item)
            elif isinstance(cand, lltype._struct):
                seen[cand] = True
                parent = cand._parentstructure()
                if parent is not None:
                    has_parent = True
                    candidates.append(parent)
                else:
                    has_parent = False
                TYPE = cand._TYPE
                if not has_parent:
                    if TYPE._arrayfld is not None:
                        total_size += sizeof(
                            TYPE, len(getattr(cand, TYPE._arrayfld).items))
                    else:
                        total_size += sizeof(TYPE)
                    if self.gc is not None:
                        typeid = self.query_types.get_typeid(TYPE)
                        total_size += self.gc.size_gc_header(typeid)
                for name in TYPE._flds:
                    candidates.append(getattr(cand, name))
            elif isinstance(cand, lltype._opaque):
                total_size += sizeof(lltype.Signed)
            elif isinstance(cand, lltype._func):
                total_size += sizeof(lltype.Signed)
            elif isinstance(cand, lltype._pyobject):
                total_size += sizeof(lltype.Signed)
            else:
                assert 0, "don't know about %s %s" % (cand, cand.__class__)
        self.total_size = total_size

    def convert_constants(self):
        self.memory = lladdress.raw_malloc(self.total_size)
        self.cvter = LLTypeConverter(self.memory, self.gc, self.query_types)
        for constant in self.constants.iterkeys():
            if isinstance(constant.value, lltype.LowLevelType):
                self.constants[constant] = constant.value
            elif isinstance(constant.value, str):
                self.constants[constant] = constant.value
            elif isinstance(constant.value, FUNCTIONTYPES):
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
                if (hasattr(obj, "llexitcase") and
                    Constant(obj.llexitcase) in self.constants):
                    obj.llexitcase = self.constants[Constant(obj.llexitcase)]
            elif isinstance(obj, Block):
                for op in obj.operations:
                    patch_consts(op.args)
        for graph in self.graphs:
            traverse(visit, graph)

    def create_type_ids(self):
        for TYPE in self.types:
            if isinstance(TYPE, (lltype.Array, lltype.Struct)):
                #assign a typeid
                self.query_types.get_typeid(TYPE)
            elif isinstance(TYPE, lltype.Ptr):
                self.query_types.get_typeid(TYPE.TO)

    def convert(self):
        self.collect_constants_and_types()
        self.calculate_size()
        self.convert_constants()
        self.patch_graphs()
        if self.query_types is not None:
            self.create_type_ids()
