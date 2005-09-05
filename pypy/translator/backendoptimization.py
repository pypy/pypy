import autopath
from pypy.translator.translator import Translator
from pypy.translator.simplify import eliminate_empty_blocks, join_blocks, remove_identical_vars
from pypy.translator.unsimplify import copyvar, split_block
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, last_exception
from pypy.objspace.flow.model import traverse, mkentrymap, checkgraph
from pypy.annotation import model as annmodel
from pypy.tool.unionfind import UnionFind
from pypy.rpython.lltype import Void, Bool
from pypy.rpython import rmodel

def remove_same_as(graph):
    """Remove all 'same_as' operations.
    """
    same_as_positions = []
    def visit(node): 
        if isinstance(node, Block): 
            for i, op in enumerate(node.operations):
                if op.opname == 'same_as': 
                    same_as_positions.append((node, i))
    traverse(visit, graph)
    while same_as_positions:
        block, index = same_as_positions.pop()
        same_as_result = block.operations[index].result
        same_as_arg = block.operations[index].args[0]
        # replace the new variable (same_as_result) with the old variable
        # (from all subsequent positions)
        for op in block.operations[index:]:
            if op is not None:
                for i in range(len(op.args)):
                    if op.args[i] == same_as_result:
                        op.args[i] = same_as_arg
        for link in block.exits:
            for i in range(len(link.args)):
                if link.args[i] == same_as_result:
                    link.args[i] = same_as_arg
        if block.exitswitch == same_as_result:
            block.exitswitch = same_as_arg
        block.operations[index] = None
       
    # remove all same_as operations
    def visit(node): 
        if isinstance(node, Block) and node.operations:
            node.operations[:] = filter(None, node.operations)
    traverse(visit, graph)


def remove_void(translator):
    for func, graph in translator.flowgraphs.iteritems():
        args = [arg for arg in graph.startblock.inputargs
                    if arg.concretetype is not Void]
        graph.startblock.inputargs = args
    def visit(block): 
        if isinstance(block, Block):
            for op in block.operations:
                if op.opname == 'direct_call':
                    args = [arg for arg in op.args
                                if arg.concretetype is not Void]
                    op.args = args
    for func, graph in translator.flowgraphs.iteritems():
        traverse(visit, graph)
 
def rename_extfunc_calls(translator):
    from pypy.rpython.extfunctable import table as extfunctable
    def visit(block): 
        if isinstance(block, Block):
            for op in block.operations:
                if op.opname != 'direct_call':
                    continue
                functionref = op.args[0]
                if not isinstance(functionref, Constant):
                    continue
                _callable = functionref.value._obj._callable
                for func, extfuncinfo in extfunctable.iteritems():  # precompute a dict?
                    if _callable is not extfuncinfo.ll_function or not extfuncinfo.backend_functiontemplate:
                        continue
                    language, functionname = extfuncinfo.backend_functiontemplate.split(':')
                    if language is 'C':
                        old_name = functionref.value._obj._name[:]
                        functionref.value._obj._name = functionname
                        #print 'rename_extfunc_calls: %s -> %s' % (old_name, functionref.value._obj._name)
                        break
    for func, graph in translator.flowgraphs.iteritems():
        traverse(visit, graph)
 
def SSI_to_SSA(graph):
    """Rename the variables in a flow graph as much as possible without
    violating the SSA rule.  'SSI' means that each Variable in a flow graph is
    defined only once in the whole graph; all our graphs are SSI.  This
    function does not break that rule, but changes the 'name' of some
    Variables to give them the same 'name' as other Variables.  The result
    looks like an SSA graph.  'SSA' means that each var name appears as the
    result of an operation only once in the whole graph, but it can be
    passed to other blocks across links.
    """
    entrymap = mkentrymap(graph)
    consider_blocks = entrymap
    variable_families = UnionFind()

    # group variables by families; a family of variables will be identified.
    while consider_blocks:
        blocklist = consider_blocks.keys()
        consider_blocks = {}
        for block in blocklist:
            if block is graph.startblock:
                continue
            links = entrymap[block]
            assert links
            mapping = {}
            for i in range(len(block.inputargs)):
                # list of possible vars that can arrive in i'th position
                v1 = block.inputargs[i]
                v1 = variable_families.find_rep(v1)
                inputs = {v1: True}
                key = []
                for link in links:
                    v = link.args[i]
                    if not isinstance(v, Variable):
                        break
                    v = variable_families.find_rep(v)
                    inputs[v] = True
                else:
                    if len(inputs) == 2:
                        variable_families.union(*inputs)
                        # mark all the following blocks as subject to
                        # possible further optimization
                        for link in block.exits:
                            consider_blocks[link.target] = True
    # rename variables to give them the name of their familiy representant
    for v in variable_families.keys():
        v1 = variable_families.find_rep(v)
        if v1 != v:
            v._name = v1.name

    # sanity-check that the same name is never used several times in a block
    variables_by_name = {}
    for block in entrymap:
        vars = [op.result for op in block.operations]
        for link in block.exits:
            vars += link.getextravars()
        assert len(dict.fromkeys([v.name for v in vars])) == len(vars), (
            "duplicate variable name in %r" % (block,))
        for v in vars:
            variables_by_name.setdefault(v.name, []).append(v)
    # sanity-check that variables with the same name have the same concretetype
    for vname, vlist in variables_by_name.items():
        vct = [getattr(v, 'concretetype', None) for v in vlist]
        assert vct == vct[:1] * len(vct), (
            "variables called %s have mixed concretetypes: %r" % (vname, vct))

def collect_called_functions(graph):
    funcs = {}
    def visit(obj):
        if not isinstance(obj, Block):
            return
        for op in obj.operations:
            if op.opname == "direct_call":
                funcs[op.args[0]] = True
    return funcs

def inline_function(translator, inline_func, graph):
    callsites = []
    def find_callsites(block):
        if isinstance(block, Block):
            for i, op in enumerate(block.operations):
                if not (op.opname == "direct_call" and
                    isinstance(op.args[0], Constant)):
                    continue
                if op.args[0].value._obj._callable is inline_func:
                    callsites.append((block, i))
    traverse(find_callsites, graph)
    while callsites != []:
        block, index_operation = callsites.pop()
        _inline_function(translator, graph, block, index_operation)
        callsites = []
        traverse(find_callsites, graph)
        checkgraph(graph)

def _find_exception_type(block):
    #XXX slightly brittle: find the exception type for simple cases
    #(e.g. if you do only raise XXXError) by doing pattern matching
    ops = block.operations
    if (len(ops) < 6 or
        ops[-6].opname != "malloc" or ops[-5].opname != "cast_pointer" or
        ops[-4].opname != "setfield" or ops[-3].opname != "cast_pointer" or
        ops[-2].opname != "getfield" or ops[-1].opname != "cast_pointer" or
        len(block.exits) != 1 or block.exits[0].args[0] != ops[-2].result or
        block.exits[0].args[1] != ops[-1].result or
        not isinstance(ops[-4].args[1], Constant) or
        ops[-4].args[1].value != "typeptr"):
        return None
    return ops[-4].args[2].value

def _inline_function(translator, graph, block, index_operation):
    exception_guarded = False
    if (block.exitswitch == Constant(last_exception) and
        index_operation == len(block.operations) - 1):
        exception_guarded = True
        assert len(collect_called_functions(graph)) == 0, (
            "can't handle exceptions yet")
    op = block.operations[index_operation]
    graph_to_inline = translator.flowgraphs[op.args[0].value._obj._callable]
    entrymap = mkentrymap(graph_to_inline)
    beforeblock = block
    afterblock = split_block(translator, graph, block, index_operation)
    assert afterblock.operations[0] is op
    #vars that need to be passed through the blocks of the inlined function
    passon_vars = {beforeblock: [arg for arg in beforeblock.exits[0].args
                                     if isinstance(arg, Variable)]}
    copied_blocks = {}
    varmap = {}
    def get_new_name(var):
        if var is None:
            return None
        if isinstance(var, Constant):
            return var
        if var not in varmap:
            varmap[var] = copyvar(translator, var)
        return varmap[var]
    def get_new_passon_var_names(block):
        result = [copyvar(translator, var) for var in passon_vars[beforeblock]]
        passon_vars[block] = result
        return result
    def copy_operation(op):
        args = [get_new_name(arg) for arg in op.args]
        return SpaceOperation(op.opname, args, get_new_name(op.result))
    def copy_block(block):
        if block in copied_blocks:
            "already there"
            return copied_blocks[block]
        args = ([get_new_name(var) for var in block.inputargs] +
                get_new_passon_var_names(block))
        newblock = Block(args)
        copied_blocks[block] = newblock
        newblock.operations = [copy_operation(op) for op in block.operations]
        newblock.exits = [copy_link(link, block) for link in block.exits]
        newblock.exitswitch = get_new_name(block.exitswitch)
        newblock.exc_handler = block.exc_handler
        return newblock
    def copy_link(link, prevblock):
        newargs = [get_new_name(a) for a in link.args] + passon_vars[prevblock]
        newlink = Link(newargs, copy_block(link.target), link.exitcase)
        newlink.prevblock = copy_block(link.prevblock)
        newlink.last_exception = get_new_name(link.last_exception)
        newlink.last_exc_value = get_new_name(link.last_exc_value)
        if hasattr(link, 'llexitcase'):
            newlink.llexitcase = link.llexitcase
        return newlink
    linktoinlined = beforeblock.exits[0]
    assert linktoinlined.target is afterblock
    copiedstartblock = copy_block(graph_to_inline.startblock)
    copiedstartblock.isstartblock = False
    copiedreturnblock = copied_blocks[graph_to_inline.returnblock]
    #find args passed to startblock of inlined function
    passon_args = []
    for arg in op.args[1:]:
        if isinstance(arg, Constant):
            passon_args.append(arg)
        else:
            index = afterblock.inputargs.index(arg)
            passon_args.append(linktoinlined.args[index])
    passon_args += passon_vars[beforeblock]
    #rewire blocks
    linktoinlined.target = copiedstartblock
    linktoinlined.args = passon_args
    afterblock.inputargs = [op.result] + afterblock.inputargs
    afterblock.operations = afterblock.operations[1:]
    linkfrominlined = Link([copiedreturnblock.inputargs[0]] + passon_vars[graph_to_inline.returnblock], afterblock)
    linkfrominlined.prevblock = copiedreturnblock
    copiedreturnblock.exitswitch = None
    copiedreturnblock.exits = [linkfrominlined]
    assert copiedreturnblock.exits[0].target == afterblock
    if graph_to_inline.exceptblock in entrymap:
        #let links to exceptblock of the graph to inline go to graphs exceptblock
        copiedexceptblock = copied_blocks[graph_to_inline.exceptblock]
        if not exception_guarded:
            copiedexceptblock = copied_blocks[graph_to_inline.exceptblock]
            for link in entrymap[graph_to_inline.exceptblock]:
                copiedblock = copied_blocks[link.prevblock]
                assert len(copiedblock.exits) == 1
                copiedblock.exits[0].args = copiedblock.exits[0].args[:2]
                copiedblock.exits[0].target = graph.exceptblock
        else:
            def find_args_in_exceptional_case(link, block, etype, evalue):
                linkargs = []
                for arg in link.args:
                    if arg == link.last_exception:
                        linkargs.append(etype)
                    elif arg == link.last_exc_value:
                        linkargs.append(evalue)
                    elif isinstance(arg, Constant):
                        linkargs.append(arg)
                    else:
                        index = afterblock.inputargs.index(arg)
                        linkargs.append(passon_vars[block][index - 1])
                return linkargs
            exc_match = Constant(rmodel.getfunctionptr(
                translator,
                translator.rtyper.getexceptiondata().ll_exception_match))
            #try to match the exceptions for simple cases
            for link in entrymap[graph_to_inline.exceptblock]:
                copiedblock = copied_blocks[link.prevblock]
                copiedlink = copiedblock.exits[0]
                eclass = _find_exception_type(copiedblock)
                print copiedblock.operations
                if eclass is None:
                    continue
                etype = copiedlink.args[0]
                evalue = copiedlink.args[1]
                for exceptionlink in afterblock.exits[1:]:
                    if exc_match.value(eclass, exceptionlink.llexitcase):
                        copiedlink.target = exceptionlink.target
                        linkargs = find_args_in_exceptional_case(exceptionlink,
                                                                 copiedblock,
                                                                 etype, evalue)
                        copiedlink.args = linkargs
                        break
            #XXXXX don't look: insert blocks that do exception matching
            #for the cases where direct matching did not work
            blocks = []
            for i, link in enumerate(afterblock.exits[1:]):
                etype = copyvar(translator, copiedexceptblock.inputargs[0])
                evalue = copyvar(translator, copiedexceptblock.inputargs[1])
                block = Block([etype, evalue] + get_new_passon_var_names(link.target))
                res = Variable()
                res.concretetype = Bool
                translator.annotator.bindings[res] = annmodel.SomeBool()
                args = [exc_match, etype, Constant(link.llexitcase)]
                block.operations.append(SpaceOperation("direct_call", args, res))
                block.exitswitch = res
                linkargs = find_args_in_exceptional_case(link, link.target,
                                                         etype, evalue)
                l = Link(linkargs, link.target)
                l.prevblock = block
                l.exitcase = True
                block.exits.append(l)
                if i > 0:
                    l = Link(blocks[-1].inputargs, block)
                    l.prevblock = blocks[-1]
                    l.exitcase = False
                    blocks[-1].exits.insert(0, l)
                blocks.append(block)
            blocks[-1].exits = blocks[-1].exits[:1]
            blocks[-1].operations = []
            blocks[-1].exitswitch = None
            linkargs = copiedexceptblock.inputargs
            copiedexceptblock.closeblock(Link(linkargs, blocks[0]))
            afterblock.exits = [afterblock.exits[0]]
            afterblock.exitswitch = None
    #cleaning up -- makes sense to be here, because I insert quite
    #some empty blocks and blocks that can be joined
    eliminate_empty_blocks(graph)
    join_blocks(graph)
    remove_identical_vars(graph)

def backend_optimizations(graph):
    remove_same_as(graph)
    eliminate_empty_blocks(graph)
    checkgraph(graph)
    SSI_to_SSA(graph)
    checkgraph(graph)

# ____________________________________________________________

if __name__ == '__main__':

    def is_perfect_number(n=int):
        div = 1
        sum = 0
        while div < n:
            if n % div == 0:
                sum += div
            div += 1
        return n == sum

    t = Translator(is_perfect_number)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    graph = t.getflowgraph()
    remove_same_as(graph)
    SSI_to_SSA(graph)
    checkgraph(graph)
    t.view()
    f = t.ccompile()
    for i in range(1, 33):
        print '%3d' % i, is_perfect_number(i)
