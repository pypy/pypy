from pypy.translator.unsimplify import split_block
from pypy.translator.backendopt import canraise
from pypy.objspace.flow.model import Block, Constant, Variable, Link, \
        c_last_exception, SpaceOperation, checkgraph
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
    elif isinstance(T, Ptr):
        return Constant(None, T)
    assert 0, "not implemented yet"

class ExceptionTransformer(object):
    def __init__(self, translator):
        self.translator = translator
        self.raise_analyzer = canraise.RaiseAnalyzer(translator)
        RPYEXC_OCCURED_TYPE = lltype.FuncType([], lltype.Bool)
        self.rpyexc_occured_ptr = Constant(lltype.functionptr(
            RPYEXC_OCCURED_TYPE, "RPyExceptionOccurred", external="C"),
            lltype.Ptr(RPYEXC_OCCURED_TYPE))

    def create_exception_handling(self, graph):
        """After an exception in a direct_call (or indirect_call), that is not caught
        by an explicit
        except statement, we need to reraise the exception. So after this
        direct_call we need to test if an exception had occurred. If so, we return
        from the current graph with an unused value (false/0/0.0/null).
        Because of the added exitswitch we need an additional block.
        """
        exc_data = self.translator.rtyper.getexceptiondata()
        for block in list(graph.iterblocks()): #collect the blocks before changing them
            self.transform_block(graph, block)
        checkgraph(graph)

    def transform_block(self, graph, block):
        last_operation = len(block.operations)-1
        if block.exitswitch == c_last_exception:
            last_operation -= 1
        for i in range(last_operation, -1, -1):
            op = block.operations[i]
            print "considering op", op, i
            if not self.raise_analyzer.can_raise(op):
                continue

            afterblock = split_block(self.translator, graph, block, i+1)

            var_exc_occured = Variable()
            var_exc_occured.concretetype = lltype.Bool
            
            block.operations.append(SpaceOperation("direct_call", [self.rpyexc_occured_ptr], var_exc_occured))
            block.exitswitch = var_exc_occured

            #non-exception case
            block.exits[0].exitcase = block.exits[0].llexitcase = False

            #exception occurred case
            l = Link([error_value(graph.returnblock.inputargs[0].concretetype)], graph.returnblock)
            l.prevblock  = block
            l.exitcase = l.llexitcase = True

            block.exits.append(l)

