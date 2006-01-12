from pypy.objspace.flow.model import FunctionGraph, Constant, Variable, c_last_exception
from pypy.rpython.rarithmetic import intmask, r_uint, ovfcheck, r_longlong, r_ulonglong
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.memory import lladdress
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.objectmodel import FREED_OBJECT

import sys
import math
import py

log = py.log.Producer('llinterp')

class LLException(Exception):
    def __str__(self):
        etype, evalue = self.args
        return '<LLException %r>' % (''.join(etype.name).rstrip('\x00'),)

class LLInterpreter(object):
    """ low level interpreter working with concrete values. """

    def __init__(self, typer, lltype=lltype):
        self.bindings = {}
        self.typer = typer
        self.llt = lltype  #module that contains the used lltype classes
        self.active_frame = None
        # XXX hack hack hack: set gc to None because
        # prepare_graphs_and_create_gc might already use the llinterpreter!
        self.gc = None
        if hasattr(lltype, "prepare_graphs_and_create_gc"):
            flowgraphs = typer.annotator.translator.graphs
            self.gc = lltype.prepare_graphs_and_create_gc(self, flowgraphs)

    def eval_graph(self, graph, args=()):
        llframe = LLFrame(graph, args, self)
        try:
            return llframe.eval()
        except LLException, e:
            print "LLEXCEPTION:", e
            self.print_traceback()
            raise
        except Exception, e:
            print "AN ERROR OCCURED:", e
            self.print_traceback()
            raise

    def print_traceback(self):
        frame = self.active_frame
        frames = []
        while frame is not None:
            frames.append(frame)
            frame = frame.f_back
        frames.reverse()
        for frame in frames:
            print frame.graph.name,
            if frame.curr_block is None:
                print "<not running yet>"
                continue
            try:
                print self.typer.annotator.annotated[frame.curr_block].__module__
            except KeyError:
                # if the graph is from the GC it was not produced by the same
                # translator :-(
                print "<unknown module>"
            for i, operation in enumerate(frame.curr_block.operations):
                if i == frame.curr_operation_index:
                    print "E  ",
                else:
                    print "   ",
                print operation

    def find_roots(self):
        log.findroots("starting")
        frame = self.active_frame
        roots = []
        while frame is not None:
            log.findroots("graph", frame.graph.name)
            frame.find_roots(roots)
            frame = frame.f_back
        return roots


# implementations of ops from flow.operation
from pypy.objspace.flow.operation import FunctionByName
opimpls = FunctionByName.copy()
opimpls['is_true'] = bool

ops_returning_a_bool = {'gt': True, 'ge': True,
                        'lt': True, 'le': True,
                        'eq': True, 'ne': True,
                        'is_true': True}

class LLFrame(object):
    def __init__(self, graph, args, llinterpreter, f_back=None):
        assert isinstance(graph, FunctionGraph)
        self.graph = graph
        self.args = args
        self.llinterpreter = llinterpreter
        self.llt = llinterpreter.llt
        self.bindings = {}
        self.f_back = f_back
        self.curr_block = None
        self.curr_operation_index = 0
        self.alloca_objects = []

    # _______________________________________________________
    # variable setters/getters helpers

    def clear(self):
        self.bindings.clear()

    def fillvars(self, block, values):
        vars = block.inputargs
        assert len(vars) == len(values), (
                   "block %s received %d args, expected %d" % (
                    block, len(values), len(vars)))
        for var, val in zip(vars, values):
            self.setvar(var, val)

    def setvar(self, var, val):
        if var.concretetype is not self.llt.Void:
            assert self.llinterpreter.typer.type_system.isCompatibleType(self.llt.typeOf(val), var.concretetype)
        assert isinstance(var, Variable)
        self.bindings[var] = val

    def setifvar(self, var, val):
        if isinstance(var, Variable):
            self.setvar(var, val)

    def getval(self, varorconst):
        try:
            val = varorconst.value
        except AttributeError:
            val = self.bindings[varorconst]
        if varorconst.concretetype is not self.llt.Void:
            assert self.llinterpreter.typer.type_system.isCompatibleType(self.llt.typeOf(val), varorconst.concretetype)
        return val

    # _______________________________________________________
    # other helpers
    def getoperationhandler(self, opname):
        ophandler = getattr(self, 'op_' + opname, None)
        if ophandler is None:
            raise AssertionError, "cannot handle operation %r yet" %(opname,)
        return ophandler
    # _______________________________________________________
    # evaling functions

    def eval(self):
        self.llinterpreter.active_frame = self
        graph = self.graph
        log.frame("evaluating", graph.name)
        nextblock = graph.startblock
        args = self.args
        while 1:
            self.clear()
            self.fillvars(nextblock, args)
            nextblock, args = self.eval_block(nextblock)
            if nextblock is None:
                self.llinterpreter.active_frame = self.f_back
                for obj in self.alloca_objects:
                    #XXX slighly unclean
                    obj._setobj(None)
                return args

    def eval_block(self, block):
        """ return (nextblock, values) tuple. If nextblock
            is None, values is the concrete return value.
        """
        self.curr_block = block
        catch_exception = block.exitswitch == c_last_exception
        e = None

        try:
            for i, op in enumerate(block.operations):
                self.curr_operation_index = i
                self.eval_operation(op)
        except LLException, e:
            if not (catch_exception and op is block.operations[-1]):
                raise

        # determine nextblock and/or return value
        if len(block.exits) == 0:
            # return block
            if len(block.inputargs) == 2:
                # exception
                etypevar, evaluevar = block.getvariables()
                etype = self.getval(etypevar)
                evalue = self.getval(evaluevar)
                # watch out, these are _ptr's
                raise LLException(etype, evalue)
            resultvar, = block.getvariables()
            result = self.getval(resultvar)
            log.operation("returning", repr(result))
            return None, result
        elif block.exitswitch is None:
            # single-exit block
            assert len(block.exits) == 1
            link = block.exits[0]
        elif catch_exception:
            link = block.exits[0]
            if e:
                exdata = self.llinterpreter.typer.getexceptiondata()
                cls, inst = e.args
                for link in block.exits[1:]:
                    assert issubclass(link.exitcase, Exception)
                    if self.op_direct_call(exdata.fn_exception_match,
                                           cls, link.llexitcase):
                        self.setifvar(link.last_exception, cls)
                        self.setifvar(link.last_exc_value, inst)
                        break
                else:
                    # no handler found, pass on
                    raise e
        else:
            llexitvalue = self.getval(block.exitswitch)
            for link in block.exits:
                if link.llexitcase == llexitvalue:
                    break   # found -- the result is in 'link'
            else:
                if block.exits[-1].exitcase == "default":
                    assert block.exits[-1].llexitcase is None
                    link = block.exits[-1]
                else:
                    raise ValueError("exit case %r not found in the exit links "
                                     "of %r" % (llexitvalue, block))
        return link.target, [self.getval(x) for x in link.args]

    def eval_operation(self, operation):
        log.operation("considering", operation)
        ophandler = self.getoperationhandler(operation.opname)
        # XXX slighly unnice but an important safety check
        if operation.opname == 'direct_call':
            assert isinstance(operation.args[0], Constant)
        elif operation.opname == 'indirect_call':
            assert isinstance(operation.args[0], Variable)
        vals = [self.getval(x) for x in operation.args]
        # if these special cases pile up, do something better here
        if operation.opname in ['cast_pointer', 'ooupcast', 'oodowncast']:
            vals.insert(0, operation.result.concretetype)
        retval = ophandler(*vals)
        self.setvar(operation.result, retval)

    def make_llexception(self, exc):
        typer = self.llinterpreter.typer
        exdata = typer.getexceptiondata()
        if isinstance(exc, OSError):
            self.op_direct_call(exdata.fn_raise_OSError, exc.errno)
            assert False, "op_direct_call above should have raised"
        else:
            exc_class = exc.__class__
            evalue = self.op_direct_call(exdata.fn_pyexcclass2exc,
                                         self.llt.pyobjectptr(exc_class))
            etype = self.op_direct_call(exdata.fn_type_of_exc_inst, evalue)
        raise LLException(etype, evalue)

    def invoke_callable_with_pyexceptions(self, fptr, *args):
        obj = self.llinterpreter.typer.type_system.deref(fptr)
        try:
            return obj._callable(*args)
        except Exception, e:
            #print "GOT A CPYTHON EXCEPTION:", e.__class__, e
            self.make_llexception(e)

    def find_roots(self, roots):
        log.findroots(self.curr_block.inputargs)
        for arg in self.curr_block.inputargs:
            if (isinstance(arg, Variable) and
                isinstance(self.getval(arg), self.llt._ptr)):
                roots.append(self.getval(arg))
        for op in self.curr_block.operations[:self.curr_operation_index]:
            if isinstance(self.getval(op.result), self.llt._ptr):
                roots.append(self.getval(op.result))

    # __________________________________________________________
    # misc LL operation implementations

    def op_keepalive(self, value):
        pass

    def op_same_as(self, x):
        return x

    def op_hint(self, x, hints):
        return x

    def op_setfield(self, obj, fieldname, fieldvalue):
        # obj should be pointer
        FIELDTYPE = getattr(self.llt.typeOf(obj).TO, fieldname)
        if FIELDTYPE != self.llt.Void:
            gc = self.llinterpreter.gc
            if gc is None or not gc.needs_write_barrier(FIELDTYPE):
                setattr(obj, fieldname, fieldvalue)
            else:
                args = gc.get_arg_write_barrier(obj, fieldname, fieldvalue)
                write_barrier = gc.get_funcptr_write_barrier()
                result = self.op_direct_call(write_barrier, *args)

    def op_getarrayitem(self, array, index):
        return array[index]

    def op_setarrayitem(self, array, index, item):
        # array should be a pointer
        ITEMTYPE = self.llt.typeOf(array).TO.OF
        if ITEMTYPE != self.llt.Void:
            gc = self.llinterpreter.gc
            if gc is None or not gc.needs_write_barrier(ITEMTYPE):
                array[index] = item
            else:
                args = gc.get_arg_write_barrier(array, index, item)
                write_barrier = gc.get_funcptr_write_barrier()
                self.op_direct_call(write_barrier, *args)

    def op_direct_call(self, f, *args):
        obj = self.llinterpreter.typer.type_system.deref(f)
        has_callable = getattr(obj, '_callable', None) is not None
        if has_callable and getattr(obj._callable, 'suggested_primitive', False):
                return self.invoke_callable_with_pyexceptions(f, *args)
        if hasattr(obj, 'graph'):
            graph = obj.graph
        else:
            assert has_callable, "don't know how to execute %r" % f
            return self.invoke_callable_with_pyexceptions(f, *args)
        frame = self.__class__(graph, args, self.llinterpreter, self)
        return frame.eval()

    def op_indirect_call(self, f, *args):
        graphs = args[-1]
        args = args[:-1]
        if graphs is not None:
            obj = self.llinterpreter.typer.type_system.deref(f)
            if hasattr(obj, 'graph'):
                assert obj.graph in graphs 
        else:
            print "this should ideally not happen", f, graphs, args
        return self.op_direct_call(f, *args)

    def op_malloc(self, obj):
        if self.llinterpreter.gc is not None:
            args = self.llinterpreter.gc.get_arg_malloc(obj)
            malloc = self.llinterpreter.gc.get_funcptr_malloc()
            result = self.op_direct_call(malloc, *args)
            return self.llinterpreter.gc.adjust_result_malloc(result, obj)
        else:
            return self.llt.malloc(obj)

    def op_malloc_varsize(self, obj, size):
        if self.llinterpreter.gc is not None:
            args = self.llinterpreter.gc.get_arg_malloc(obj, size)
            malloc = self.llinterpreter.gc.get_funcptr_malloc()
            result = self.op_direct_call(malloc, *args)
            return self.llinterpreter.gc.adjust_result_malloc(result, obj, size)
        else:
            try:
                return self.llt.malloc(obj, size)
            except MemoryError, e:
                self.make_llexception(e)

    def op_flavored_malloc(self, flavor, obj):
        assert isinstance(flavor, str)
        if flavor == "stack":
            if isinstance(obj, self.llt.Struct) and obj._arrayfld is None:
                result = self.llt.malloc(obj)
                self.alloca_objects.append(result)
                return result
            else:
                raise ValueError("cannot allocate variable-sized things on the stack")
        return self.llt.malloc(obj, flavor=flavor)

    def op_flavored_free(self, flavor, obj):
        assert isinstance(flavor, str)
        self.llt.free(obj, flavor=flavor)

    def op_getfield(self, obj, field):
        assert isinstance(obj, self.llt._ptr)
        result = getattr(obj, field)
        # check the difference between op_getfield and op_getsubstruct:
        # the former returns the real field, the latter a pointer to it
        assert self.llt.typeOf(result) == getattr(self.llt.typeOf(obj).TO,
                                                  field)
        return result

    def op_getsubstruct(self, obj, field):
        assert isinstance(obj, self.llt._ptr)
        result = getattr(obj, field)
        # check the difference between op_getfield and op_getsubstruct:
        # the former returns the real field, the latter a pointer to it
        assert (self.llt.typeOf(result) ==
                self.llt.Ptr(getattr(self.llt.typeOf(obj).TO, field)))
        return result

    def op_getarraysubstruct(self, array, index):
        assert isinstance(array, self.llt._ptr)
        result = array[index]
        return result
        # the diff between op_getarrayitem and op_getarraysubstruct
        # is the same as between op_getfield and op_getsubstruct

    def op_getarraysize(self, array):
        #print array,type(array),dir(array)
        assert isinstance(self.llt.typeOf(array).TO, self.llt.Array)
        return len(array)

    def op_cast_pointer(self, tp, obj):
        # well, actually this is what's now in the globals.
        return self.llt.cast_pointer(tp, obj)

    def op_ptr_eq(self, ptr1, ptr2):
        assert isinstance(ptr1, self.llt._ptr)
        assert isinstance(ptr2, self.llt._ptr)
        return ptr1 == ptr2

    def op_ptr_ne(self, ptr1, ptr2):
        assert isinstance(ptr1, self.llt._ptr)
        assert isinstance(ptr2, self.llt._ptr)
        return ptr1 != ptr2

    def op_ptr_nonzero(self, ptr1):
        assert isinstance(ptr1, self.llt._ptr)
        return bool(ptr1)

    def op_ptr_iszero(self, ptr1):
        assert isinstance(ptr1, self.llt._ptr)
        return not bool(ptr1)

    def op_cast_ptr_to_int(self, ptr1):
        assert isinstance(ptr1, self.llt._ptr)
        assert isinstance(self.llt.typeOf(ptr1).TO, (self.llt.Array,
                                                     self.llt.Struct))
        return self.llt.cast_ptr_to_int(ptr1)

    def op_cast_int_to_float(self, i):
        assert type(i) is int
        return float(i)

    def op_cast_int_to_char(self, b):
        assert type(b) is int
        return chr(b)

    def op_cast_bool_to_int(self, b):
        assert type(b) is bool
        return int(b)

    def op_cast_bool_to_uint(self, b):
        assert type(b) is bool
        return r_uint(int(b))

    def op_cast_bool_to_float(self, b):
        assert type(b) is bool
        return float(b)

    def op_bool_not(self, b):
        assert type(b) is bool
        return not b

    def op_cast_float_to_int(self, f):
        assert type(f) is float
        return ovfcheck(int(f))

    def op_cast_float_to_uint(self, f):
        assert type(f) is float
        return r_uint(int(f))

    def op_cast_char_to_int(self, b):
        assert type(b) is str and len(b) == 1
        return ord(b)

    def op_cast_unichar_to_int(self, b):
        assert type(b) is unicode and len(b) == 1
        return ord(b)

    def op_cast_int_to_unichar(self, b):
        assert type(b) is int 
        return unichr(b)

    def op_cast_int_to_uint(self, b):
        assert type(b) is int
        return r_uint(b)

    def op_cast_uint_to_int(self, b):
        assert type(b) is r_uint
        return intmask(b)

    def op_cast_int_to_longlong(self, b):
        assert type(b) is int
        return r_longlong(b)

    def op_truncate_longlong_to_int(self, b):
        assert type(b) is r_longlong
        assert -sys.maxint-1 <= b <= sys.maxint
        return int(b)

    def op_int_floordiv_ovf_zer(self, a, b):
        assert type(a) is int
        assert type(b) is int
        if b == 0:
            self.make_llexception(ZeroDivisionError())
        return self.op_int_floordiv_ovf(a, b)
            
    def op_int_mod_ovf_zer(self, a, b):
        assert type(a) is int
        assert type(b) is int
        if b == 0:
            self.make_llexception(ZeroDivisionError())
        return self.op_int_mod_ovf(a, b)
            
    def op_float_floor(self, b):
        assert type(b) is float
        return math.floor(b)

    def op_float_fmod(self, b,c):
        assert type(b) is float
        assert type(c) is float
        return math.fmod(b,c)

    # operations on pyobjects!
    for opname in opimpls.keys():
        exec py.code.Source("""
        def op_%(opname)s(self, *pyobjs):
            for pyo in pyobjs:
                assert self.llt.typeOf(pyo) == self.llt.Ptr(self.llt.PyObject)
            func = opimpls[%(opname)r]
            try:
                pyo = func(*[pyo._obj.value for pyo in pyobjs])
            except Exception, e:
                self.make_llexception(e)
            return self.llt.pyobjectptr(pyo)
        """ % locals()).compile()
    del opname

    def op_simple_call(self, f, *args):
        assert self.llt.typeOf(f) == self.llt.Ptr(self.llt.PyObject)
        for pyo in args:
            assert self.llt.typeOf(pyo) == self.llt.Ptr(self.llt.PyObject)
        res = f._obj.value(*[pyo._obj.value for pyo in args])
        return self.llt.pyobjectptr(res)

    # __________________________________________________________
    # operations on addresses

    def op_raw_malloc(self, size):
        assert self.llt.typeOf(size) == self.llt.Signed
        return lladdress.raw_malloc(size)

    def op_raw_free(self, addr):
        assert self.llt.typeOf(addr) == lladdress.Address
        lladdress.raw_free(addr)

    def op_raw_memcopy(self, fromaddr, toaddr, size):
        assert self.llt.typeOf(fromaddr) == lladdress.Address
        assert self.llt.typeOf(toaddr) == lladdress.Address
        lladdress.raw_memcopy(fromaddr, toaddr, size)

    def op_raw_load(self, addr, typ, offset):
        assert isinstance(addr, lladdress.address)
        value = getattr(addr, str(typ).lower())[offset]
        assert self.llt.typeOf(value) == typ
        return value

    def op_raw_store(self, addr, typ, offset, value):
        assert isinstance(addr, lladdress.address)
        assert self.llt.typeOf(value) == typ
        getattr(addr, str(typ).lower())[offset] = value

    def op_adr_add(self, addr, offset):
        assert isinstance(addr, lladdress.address)
        assert self.llt.typeOf(offset) is self.llt.Signed
        return addr + offset

    def op_adr_sub(self, addr, offset):
        assert isinstance(addr, lladdress.address)
        assert self.llt.typeOf(offset) is self.llt.Signed
        return addr - offset

    def op_adr_delta(self, addr1, addr2):
        assert isinstance(addr1, lladdress.address)
        assert isinstance(addr2, lladdress.address)
        return addr1 - addr2

    for opname, op in (("eq", "=="), ("ne", "!="), ("le", "<="), ("lt", "<"),
                       ("gt", ">"), ("ge", ">=")):
        exec py.code.Source("""
            def op_adr_%s(self, addr1, addr2):
                assert isinstance(addr1, lladdress.address)
                assert isinstance(addr2, lladdress.address)
                return addr1 %s addr2""" % (opname, op)).compile()

    # __________________________________________________________
    # primitive operations

    for typ in (float, int, r_uint, r_longlong, r_ulonglong):
        typname = typ.__name__
        optup = ('add', 'sub', 'mul', 'div', 'truediv', 'floordiv',
                 'mod', 'gt', 'lt', 'ge', 'ne', 'le', 'eq',)
        if typ is r_uint:
            opnameprefix = 'uint'
        elif typ is r_longlong:
            opnameprefix = 'llong'
        elif typ is r_ulonglong:
            opnameprefix = 'ullong'
        else:
            opnameprefix = typname
        if typ in (int, r_uint):
            optup += 'and_', 'or_', 'lshift', 'rshift', 'xor'
        for opname in optup:
            assert opname in opimpls
            if typ is int and opname not in ops_returning_a_bool:
                adjust_result = 'intmask'
            else:
                adjust_result = ''
            pureopname = opname.rstrip('_')
            exec py.code.Source("""
                def op_%(opnameprefix)s_%(pureopname)s(self, x, y):
                    assert isinstance(x, %(typname)s)
                    assert isinstance(y, %(typname)s)
                    func = opimpls[%(opname)r]
                    return %(adjust_result)s(func(x, y))
            """ % locals()).compile()
            if typ is int:
                opname += '_ovf'
                exec py.code.Source("""
                    def op_%(opnameprefix)s_%(pureopname)s_ovf(self, x, y):
                        assert isinstance(x, %(typname)s)
                        assert isinstance(y, %(typname)s)
                        func = opimpls[%(opname)r]
                        try:
                            return %(adjust_result)s(func(x, y))
                        except OverflowError, e:
                            self.make_llexception(e)
                """ % locals()).compile()
        for opname in 'is_true', 'neg', 'abs', 'invert':
            assert opname in opimpls
            if typ is int and opname not in ops_returning_a_bool:
                adjust_result = 'intmask'
            else:
                adjust_result = ''
            exec py.code.Source("""
                def op_%(opnameprefix)s_%(opname)s(self, x):
                    assert isinstance(x, %(typname)s)
                    func = opimpls[%(opname)r]
                    return %(adjust_result)s(func(x))
            """ % locals()).compile()
            if typ is int:
                opname += '_ovf'
                exec py.code.Source("""
                    def op_%(opnameprefix)s_%(opname)s(self, x):
                        assert isinstance(x, %(typname)s)
                        func = opimpls[%(opname)r]
                        try:
                            return %(adjust_result)s(func(x))
                        except OverflowError, e:
                            self.make_llexception(e)
                """ % locals()).compile()
            
    for opname in ('gt', 'lt', 'ge', 'ne', 'le', 'eq'):
        assert opname in opimpls
        exec py.code.Source("""
            def op_char_%(opname)s(self, x, y):
                assert isinstance(x, str) and len(x) == 1
                assert isinstance(y, str) and len(y) == 1
                func = opimpls[%(opname)r]
                return func(x, y)
        """ % locals()).compile()
    
    def op_unichar_eq(self, x, y):
        assert isinstance(x, unicode) and len(x) == 1
        assert isinstance(y, unicode) and len(y) == 1
        func = opimpls['eq']
        return func(x, y)

    def op_unichar_ne(self, x, y):
        assert isinstance(x, unicode) and len(x) == 1
        assert isinstance(y, unicode) and len(y) == 1
        func = opimpls['ne']
        return func(x, y)

    #Operation of ootype

    def op_new(self, INST):
        assert isinstance(INST, ootype.Instance)
        return ootype.new(INST)

    def op_oosetfield(self, inst, name, value):
        assert isinstance(inst, ootype._instance)
        assert isinstance(name, str)
        FIELDTYPE = self.llt.typeOf(inst)._field_type(name)
        if FIELDTYPE != self.llt.Void:
            setattr(inst, name, value)

    def op_oogetfield(self, inst, name):
        assert isinstance(inst, ootype._instance)
        assert isinstance(name, str)
        return getattr(inst, name)

    def op_oosend(self, message, inst, *args):
        assert isinstance(inst, ootype._instance)
        assert isinstance(message, str)
        bm = getattr(inst, message)
        m = bm.meth
        m._checkargs(args, check_callable=False)
        if getattr(m, 'abstract', False):
            raise RuntimeError("calling abstract method %r" % (m,))
        return self.op_direct_call(m, inst, *args)

    def op_ooupcast(self, INST, inst):
        return ootype.ooupcast(INST, inst)
    
    def op_oodowncast(self, INST, inst):
        return ootype.oodowncast(INST, inst)

    def op_oononnull(self, inst):
        assert isinstance(inst, ootype._instance)
        return bool(inst)

    def op_oois(self, inst1, inst2):
        assert isinstance(inst1, ootype._instance)
        assert isinstance(inst2, ootype._instance)
        return inst1 == inst2   # NB. differently-typed NULLs must be equal

    def op_instanceof(self, inst, INST):
        return ootype.instanceof(inst, INST)

    def op_classof(self, inst):
        return ootype.classof(inst)

    def op_subclassof(self, class1, class2):
        return ootype.subclassof(class1, class2)

    def op_oosameclass(self, class1, class2):
        assert isinstance(class1, ootype._class)
        assert isinstance(class2, ootype._class)
        return class1 is class2

    def op_ooidentityhash(self, inst):
        return ootype.ooidentityhash(inst)

# by default we route all logging messages to nothingness
# e.g. tests can then switch on logging to get more help
# for failing tests
from pypy.tool.ansi_print import ansi_log
py.log.setconsumer('llinterp', ansi_log)
