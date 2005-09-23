from pypy.translator.unsimplify import split_block
from pypy.objspace.flow.model import Block, Constant, Variable, Link, \
        last_exception, flatten, SpaceOperation
from pypy.annotation import model as annmodel
from pypy.rpython.lltype import Bool, Ptr


n_calls = n_calls_patched = 0

def create_exception_handling(translator, graph):
    """After an exception in a direct_call, that is not catched by an explicit
    except statement, we need to reraise the exception. So after this
    direct_call we need to test if an exception had occurred. If so, we return
    from the current graph with an unused value (false/0/0.0/null).
    Because of the added exitswitch we need an additional block.
    """
    global n_calls, n_calls_patched
    n_calls_begin = n_calls
    e = translator.rtyper.getexceptiondata()
    blocks = [x for x in flatten(graph) if isinstance(x, Block)]
    for block in blocks:
        last_operation = len(block.operations)-1
        if block.exitswitch == Constant(last_exception):
            last_operation -= 1
        for i in range(last_operation, -1, -1):
            op = block.operations[i]
            if op.opname != 'direct_call':
                continue
            n_calls += 1
            called_can_raise = True #XXX maybe we even want a list of possible exceptions
            if not called_can_raise:
                continue
            n_calls_patched += 1

            afterblock = split_block(translator, graph, block, i+1)

            res = Variable()
            res.concretetype = Bool
            translator.annotator.bindings[res] = annmodel.SomeBool()

            etype = Variable('etype')
            etype.concretetype = e.lltype_of_exception_type
            translator.annotator.bindings[etype] = e.lltype_of_exception_type

            #XXX better use 'load()' and instantiate '%last_exception_type' (here maybe?)
            block.operations.append(SpaceOperation("last_exception_type_ptr", [], etype))
            block.operations.append(SpaceOperation("ptr_iszero", [etype], res))

            block.exitswitch = res

            #non-exception case
            block.exits[0].exitcase = block.exits[0].llexitcase = True

            #exception occurred case
            noresulttype = graph.returnblock.inputargs[0].concretetype
            noresult     = Constant(noresulttype._defl(), noresulttype)
            l = Link([noresult], graph.returnblock)
            l.prevblock  = block
            l.exitcase   = l.llexitcase = False
            block.exits.insert(0, l)    #False case needs to go first
    if n_calls != n_calls_begin:
        print 'create_exception_handling: patched %d out of %d calls' % (n_calls_patched, n_calls)
