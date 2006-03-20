from pypy.translator.unsimplify import copyvar, split_block
from pypy.translator.backendopt import canraise, inline
from pypy.objspace.flow.model import Block, Constant, Variable, Link, \
    c_last_exception, SpaceOperation, checkgraph, FunctionGraph
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.lladdress import NULL
from pypy.rpython import rclass
from pypy.rpython.rarithmetic import r_uint

PrimitiveErrorValue = {lltype.Signed: -1,
                       lltype.Unsigned: r_uint(-1),
                       lltype.Float: -1.0,
                       lltype.Char: chr(255),
                       lltype.Bool: True,
                       llmemory.Address: NULL,
                       lltype.Void: None}

def error_value(T):
    if isinstance(T, lltype.Primitive):
        return Constant(PrimitiveErrorValue[T], T)
    elif isinstance(T, lltype.Ptr):
        return Constant(lltype.nullptr(T.TO), T)
    assert 0, "not implemented yet"

# dummy functions to make the resulting graphs runnable on the llinterpreter

class ExcData(object):
    exc_type = None
    exc_value = None

def rpyexc_occured():
    return ExcData.exc_type is not None

def rpyexc_fetch_type():
    return ExcData.exc_type

def rpyexc_fetch_value():
    return ExcData.exc_value

def rpyexc_clear():
    ExcData.exc_type = None
    ExcData.exc_value = None

def rpyexc_raise(etype, evalue):
    ExcData.exc_type = etype
    ExcData.exc_value = evalue

class ExceptionTransformer(object):
    def __init__(self, translator):
        self.translator = translator
        self.raise_analyzer = canraise.RaiseAnalyzer(translator)
        self.exc_data = translator.rtyper.getexceptiondata()
        RPYEXC_OCCURED_TYPE = lltype.FuncType([], lltype.Bool)
        self.rpyexc_occured_ptr = Constant(lltype.functionptr(
            RPYEXC_OCCURED_TYPE, "RPyExceptionOccurred", external="C",
            neverrraises=True, _callable=rpyexc_occured),
            lltype.Ptr(RPYEXC_OCCURED_TYPE))
        RPYEXC_FETCH_TYPE_TYPE = lltype.FuncType([], self.exc_data.lltype_of_exception_type)
        self.rpyexc_fetch_type_ptr = Constant(lltype.functionptr(
            RPYEXC_FETCH_TYPE_TYPE, "RPyFetchExceptionType", external="C",
            neverraises=True, _callable=rpyexc_fetch_type),
            lltype.Ptr(RPYEXC_FETCH_TYPE_TYPE))
        RPYEXC_FETCH_VALUE_TYPE = lltype.FuncType([], self.exc_data.lltype_of_exception_value)
        self.rpyexc_fetch_value_ptr = Constant(lltype.functionptr(
            RPYEXC_FETCH_VALUE_TYPE, "RPyFetchExceptionValue", external="C",
            neverraises=True, _callable=rpyexc_fetch_value),
            lltype.Ptr(RPYEXC_FETCH_VALUE_TYPE))
        RPYEXC_CLEAR = lltype.FuncType([], lltype.Void)
        self.rpyexc_clear_ptr = Constant(lltype.functionptr(
            RPYEXC_CLEAR, "RPyClearException", external="C",
            neverraises=True, _callable=rpyexc_clear),
            lltype.Ptr(RPYEXC_CLEAR))
        RPYEXC_RAISE = lltype.FuncType([self.exc_data.lltype_of_exception_type,
                                        self.exc_data.lltype_of_exception_value],
                                        lltype.Void)
        self.rpyexc_raise_ptr = Constant(lltype.functionptr(
            RPYEXC_RAISE, "RPyRaiseException", external="C",
            neverraises=True, _callable=rpyexc_raise),
            lltype.Ptr(RPYEXC_RAISE))
    
    def transform_completely(self):
        for graph in self.translator.graphs:
            self.create_exception_handling(graph)

    def create_exception_handling(self, graph):
        """After an exception in a direct_call (or indirect_call), that is not caught
        by an explicit
        except statement, we need to reraise the exception. So after this
        direct_call we need to test if an exception had occurred. If so, we return
        from the current graph with a special value (False/-1/-1.0/null).
        Because of the added exitswitch we need an additional block.
        """
        for block in list(graph.iterblocks()): #collect the blocks before changing them
            self.transform_block(graph, block)
        checkgraph(graph)

    def transform_block(self, graph, block):
        if block is graph.exceptblock:
            self.transform_except_block(graph, block)
            return
        elif block is graph.returnblock:
            return
        last_operation = len(block.operations) - 1
        if block.exitswitch == c_last_exception:
            need_exc_matching = True
            last_operation -= 1
        else:
            need_exc_matching = False
        for i in range(last_operation, -1, -1):
            op = block.operations[i]
            print "considering op", op, i
            if not self.raise_analyzer.can_raise(op):
                continue

            afterblock = split_block(self.translator, graph, block, i+1)

            var_exc_occured, block = self.gen_exc_checking_var(op, i, block, graph)

            #non-exception case
            block.exits[0].exitcase = block.exits[0].llexitcase = False
        if need_exc_matching:
            if not self.raise_analyzer.can_raise(op):
                print "XXX: operation %s cannot raise, but has exception guarding in graph %s" (op, graph)
                block.exitswitch = None
                block.exits = [block.exits[0]]
            else:
                self.insert_matching(afterblock, graph)

    def transform_except_block(self, graph, block):
        # attach an except block -- let's hope that nobody uses it
        graph.exceptblock = Block([Variable('etype'),   # exception class
                                   Variable('evalue')])  # exception value
        result = Variable()
        result.concretetype = lltype.Void
        block.operations = [SpaceOperation(
           "direct_call", [self.rpyexc_raise_ptr] + block.inputargs, result)]
        l = Link([error_value(graph.returnblock.inputargs[0].concretetype)], graph.returnblock)
        l.prevblock  = block
        block.exits = [l]

    def insert_matching(self, block, graph):
        proxygraph, op = self.create_proxy_graph(block.operations[-1])
        block.operations[-1] = op
        #non-exception case
        block.exits[0].exitcase = block.exits[0].llexitcase = None
        # use the dangerous second True flag :-)
        inliner = inline.Inliner(self.translator, graph, proxygraph, True, True)
        inliner.inline_all()
        block.exits[0].exitcase = block.exits[0].llexitcase = False

    def create_proxy_graph(self, op):
        """ creates a graph which calls the original function, checks for
        raised exceptions, fetches and then raises them again. If this graph is
        inlined, the correct exception matching blocks are produced."""
        # XXX slightly annoying: construct a graph by hand
        # but better than the alternative
        result = copyvar(self.translator, op.result)
        opargs = []
        inputargs = []
        callargs = []
        ARGTYPES = []
        for var in op.args:
            if isinstance(var, Variable):
                v = Variable()
                v.concretetype = var.concretetype
                inputargs.append(v)
                opargs.append(v)
                callargs.append(var)
                ARGTYPES.append(var.concretetype)
            else:
                opargs.append(var)
        newop = SpaceOperation(op.opname, opargs, result)
        startblock = Block(inputargs)
        startblock.operations.append(newop) 
        newgraph = FunctionGraph("dummy", startblock)
        startblock.closeblock(Link([result], newgraph.returnblock))
        startblock.exits = list(startblock.exits)
        newgraph.returnblock.inputargs[0].concretetype = op.result.concretetype
        var_exc_occured, block = self.gen_exc_checking_var(newop, 0, startblock, newgraph)
        startblock.exits[0].exitcase = startblock.exits[0].llexitcase = False
        excblock = Block([])
        var_value = Variable()
        var_value.concretetype = self.exc_data.lltype_of_exception_value
        var_type = Variable()
        var_type.concretetype = self.exc_data.lltype_of_exception_type
        var_void = Variable()
        var_void.concretetype = lltype.Void
        excblock.operations.append(SpaceOperation(
            "direct_call", [self.rpyexc_fetch_value_ptr], var_value))
        excblock.operations.append(SpaceOperation(
            "direct_call", [self.rpyexc_fetch_type_ptr], var_type))
        excblock.operations.append(SpaceOperation(
            "direct_call", [self.rpyexc_clear_ptr], var_void))
        newgraph.exceptblock.inputargs[0].concretetype = self.exc_data.lltype_of_exception_type
        newgraph.exceptblock.inputargs[1].concretetype = self.exc_data.lltype_of_exception_value
        excblock.closeblock(Link([var_type, var_value], newgraph.exceptblock))
        block.exits[True].target = excblock
        block.exits[True].args = []
        FUNCTYPE = lltype.FuncType(ARGTYPES, op.result.concretetype)
        fptr = Constant(lltype.functionptr(FUNCTYPE, "dummy", graph=newgraph),
                        lltype.Ptr(FUNCTYPE))
        self.translator.graphs.append(newgraph)
        return newgraph, SpaceOperation("direct_call", [fptr] + callargs, op.result) 

    def gen_exc_checking_var(self, op, i, block, graph):
        var_exc_occured = Variable()
        var_exc_occured.concretetype = lltype.Bool
        
        block.operations.append(SpaceOperation("direct_call", [self.rpyexc_occured_ptr], var_exc_occured))
        block.exitswitch = var_exc_occured
        #exception occurred case
        l = Link([error_value(graph.returnblock.inputargs[0].concretetype)], graph.returnblock)
        l.prevblock  = block
        l.exitcase = l.llexitcase = True

        block.exits.append(l)
        return var_exc_occured, block 

