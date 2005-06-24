from pypy.translator.translator import Translator
from pypy.tool.sourcetools import compile2
from pypy.objspace.flow.model import Constant, Variable, last_exception
from pypy.rpython.rarithmetic import intmask, r_uint
import py
from pypy.rpython.lltype import _ptr, Ptr, Void, typeOf, malloc, cast_pointer
from pypy.rpython.lltype import Array

log = py.log.Producer('llinterp')

class LLException(Exception):
    pass

class LLInterpreter(object):
    """ low level interpreter working with concrete values. """

    def __init__(self, flowgraphs, typer):
        self.flowgraphs = flowgraphs
        self.bindings = {}
        self.typer = typer

    def getgraph(self, func):
        return self.flowgraphs[func]

    def eval_function(self, func, args=()):
        graph = self.getgraph(func)
        llframe = LLFrame(graph, args, self)
        return llframe.eval()

class LLFrame(object):
    def __init__(self, graph, args, llinterpreter):
        self.graph = graph
        self.args = args
        self.llinterpreter = llinterpreter
        self.bindings = {}

    # _______________________________________________________
    # variable setters/getters helpers

    def fillvars(self, block, values):
        vars = block.inputargs
        assert len(vars) == len(values), (
                   "block %s received %d args, expected %d" % (
                    block, len(values), len(vars)))
        for var, val in zip(vars, values):
            self.setvar(var, val)

    def setvar(self, var, val):
        if var.concretetype != Void:
            assert var.concretetype == typeOf(val)
        assert isinstance(var, Variable)
        self.bindings[var] = val

    def setifvar(self, var, val):
        if isinstance(var, Variable):
            self.setvar(var, val)

    def getval(self, varorconst):
        try:
            return varorconst.value
        except AttributeError:
            return self.bindings[varorconst]

    # _______________________________________________________
    # other helpers
    def getoperationhandler(self, opname):
        try:
            return getattr(self, 'op_' + opname)
        except AttributeError:
            g = globals()
            assert opname in g, (
                    "cannot handle operation %r yet" %(opname,))
            ophandler = g[opname]
            return ophandler

    # _______________________________________________________
    # evaling functions

    def eval(self):
        graph = self.graph
        log.frame("evaluating", graph.name)
        nextblock = graph.startblock
        args = self.args
        while 1:
            self.fillvars(nextblock, args)
            nextblock, args = self.eval_block(nextblock)
            if nextblock is None:
                return args

    def eval_block(self, block):
        """ return (nextblock, values) tuple. If nextblock
            is None, values is the concrete return value.
        """
        catch_exception = block.exitswitch == Constant(last_exception)
        e = None

        try:
            for op in block.operations:
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
            log.operation("returning", result)
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
                    if exdata.ll_exception_match(cls, link.llexitcase):
                        self.setifvar(link.last_exception, cls)
                        self.setifvar(link.last_exc_value, inst)
                        break
                else:
                    # no handler found, pass on
                    raise e
        else:
            index = self.getval(block.exitswitch)
            link = block.exits[index]
        return link.target, [self.getval(x) for x in link.args]

    def eval_operation(self, operation):
        log.operation("considering", operation)
        ophandler = self.getoperationhandler(operation.opname)
        vals = [self.getval(x) for x in operation.args]
        # if these special cases pile up, do something better here
        if operation.opname == 'cast_pointer':
            vals.insert(0, operation.result.concretetype)
        retval = ophandler(*vals)
        self.setvar(operation.result, retval)

    # __________________________________________________________
    # misc LL operation implementations

    def op_same_as(self, x):
        return x

    def op_setfield(self, obj, fieldname, fieldvalue):
        # obj should be pointer
        setattr(obj, fieldname, fieldvalue)

    def op_getarrayitem(self, array, index):
        return array[index]

    def op_setarrayitem(self, array, index, item):
        array[index] = item

    def op_direct_call(self, f, *args):
        if hasattr(f._obj, 'graph'):
            graph = f._obj.graph
        else:
            graph = self.llinterpreter.getgraph(f._obj._callable)
        frame = self.__class__(graph, args, self.llinterpreter)
        return frame.eval()

    def op_malloc(self, obj):
        return malloc(obj)

    def op_getfield(self, obj, field):
        assert isinstance(obj, _ptr)
        result = getattr(obj, field)
        # check the difference between op_getfield and op_getsubstruct:
        # the former returns the real field, the latter a pointer to it
        assert typeOf(result) == getattr(typeOf(obj).TO, field)
        return result

    def op_getsubstruct(self, obj, field):
        assert isinstance(obj, _ptr)
        result = getattr(obj, field)
        # check the difference between op_getfield and op_getsubstruct:
        # the former returns the real field, the latter a pointer to it
        assert typeOf(result) == Ptr(getattr(typeOf(obj).TO, field))
        return result

    def op_malloc_varsize(self, obj, size):
        return malloc(obj, size)

    def op_getarraysubstruct(self, array, index):
        assert isinstance(array, _ptr)
        result = array[index]
        return result
        # the diff between op_getarrayitem and op_getarraysubstruct
        # is the same as between op_getfield and op_getsubstruct

    def op_getarraysize(self, array):
        #print array,type(array),dir(array)
        assert isinstance(typeOf(array).TO, Array)
        return len(array)

    def op_cast_pointer(self, tp, obj):
        # well, actually this is what's now in the globals.
        return cast_pointer(tp, obj)

    def op_ptr_eq(self, ptr1, ptr2):
        assert isinstance(ptr1, _ptr)
        assert isinstance(ptr2, _ptr)
        return ptr1 == ptr2

    def op_ptr_ne(self, ptr1, ptr2):
        assert isinstance(ptr1, _ptr)
        assert isinstance(ptr2, _ptr)
        return ptr1 != ptr2

    def op_ptr_nonzero(self, ptr1):
        assert isinstance(ptr1, _ptr)
        return bool(ptr1)

    def op_ptr_iszero(self, ptr1):
        assert isinstance(ptr1, _ptr)
        return not bool(ptr1)

    def op_cast_int_to_float(self, i):
        assert type(i) is int
        return float(i)

    def op_cast_int_to_char(self, b):
        assert type(b) is int
        return chr(b)

    def op_cast_bool_to_int(self, b):
        assert type(b) is bool
        return int(b)

    def op_cast_bool_to_float(self, b):
        assert type(b) is bool
        return float(b)

    def op_bool_not(self, b):
        assert type(b) is bool
        return not b
    
    def op_cast_char_to_int(self, b):
        assert type(b) is str and len(b) == 1
        return ord(b)

    def op_cast_int_to_uint(self, b):
        assert type(b) is int
        return r_uint(b)

    def op_cast_uint_to_int(self, b):
        assert type(b) is r_uint
        return intmask(b)

# __________________________________________________________
# primitive operations
from pypy.objspace.flow.operation import FunctionByName
opimpls = FunctionByName.copy()
opimpls['is_true'] = bool
ops_returning_a_bool = {'gt': True, 'ge': True,
                        'lt': True, 'le': True,
                        'eq': True, 'ne': True,
                        'is_true': True}

for typ in (float, int, r_uint):
    typname = typ.__name__
    optup = ('add', 'sub', 'mul', 'div', 'mod', 'gt', 'lt', 'ge', 'ne', 'le', 'eq',)
    if typ is r_uint:
        opnameprefix = 'uint'
    else:
        opnameprefix = typname
    if typ in (int, r_uint):
        optup += 'truediv', 'floordiv', 'and_', 'or_', 'lshift', 'rshift', 'xor'
    for opname in optup:
        assert opname in opimpls
        if typ is int and opname not in ops_returning_a_bool:
            adjust_result = 'intmask'
        else:
            adjust_result = ''
        pureopname = opname.rstrip('_')
        exec py.code.Source("""
            def %(opnameprefix)s_%(pureopname)s(x, y):
                assert isinstance(x, %(typname)s)
                assert isinstance(y, %(typname)s)
                func = opimpls[%(opname)r]
                return %(adjust_result)s(func(x, y))
        """ % locals()).compile()
    for opname in 'is_true', 'neg':
        assert opname in opimpls
        if typ is int and opname not in ops_returning_a_bool:
            adjust_result = 'intmask'
        else:
            adjust_result = ''
        exec py.code.Source("""
            def %(opnameprefix)s_%(opname)s(x):
                assert isinstance(x, %(typname)s)
                func = opimpls[%(opname)r]
                return %(adjust_result)s(func(x))
        """ % locals()).compile()

for opname in ('gt', 'lt', 'ge', 'ne', 'le', 'eq'):
    assert opname in opimpls
    exec py.code.Source("""
        def char_%(opname)s(x, y):
            assert isinstance(x, str) and len(x) == 1
            assert isinstance(y, str) and len(y) == 1
            func = opimpls[%(opname)r]
            return func(x, y)
    """ % locals()).compile()


# by default we route all logging messages to nothingness
# e.g. tests can then switch on logging to get more help
# for failing tests
py.log.setconsumer('llinterp', None)
