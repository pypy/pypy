import autopath
from pypy.translator.translator import Translator
from pypy.translator.simplify import eliminate_empty_blocks, join_blocks
from pypy.translator.simplify import remove_identical_vars
from pypy.translator.simplify import transform_dead_op_vars
from pypy.translator.unsimplify import copyvar, split_block
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, last_exception
from pypy.objspace.flow.model import traverse, mkentrymap, checkgraph
from pypy.annotation import model as annmodel
from pypy.tool.unionfind import UnionFind
from pypy.rpython.lltype import Void, Bool
from pypy.rpython import rmodel, lltype

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
    traverse(visit, graph)
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
    op = block.operations[index_operation]
    graph_to_inline = translator.flowgraphs[op.args[0].value._obj._callable]
    exception_guarded = False
    if (block.exitswitch == Constant(last_exception) and
        index_operation == len(block.operations) - 1):
        exception_guarded = True
        assert len(collect_called_functions(graph_to_inline)) == 0, (
            "can't handle exceptions yet")
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

# ____________________________________________________________

class Blocked(Exception):
    pass

class LifeTime:

    def __init__(self, (block, var)):
        assert isinstance(var, Variable)
        self.variables = {(block, var) : True}
        self.creationpoints = {}   # set of ("type of creation point", ...)
        self.usepoints = {}        # set of ("type of use point",      ...)

    def update(self, other):
        self.variables.update(other.variables)
        self.creationpoints.update(other.creationpoints)
        self.usepoints.update(other.usepoints)


def compute_lifetimes(graph):
    """Compute the static data flow of the graph: returns a list of LifeTime
    instances, each of which corresponds to a set of Variables from the graph.
    The variables are grouped in the same LifeTime if a value can pass from
    one to the other by following the links.  Each LifeTime also records all
    places where a Variable in the set is used (read) or build (created).
    """
    lifetimes = UnionFind(LifeTime)

    def set_creation_point(block, var, *cp):
        _, _, info = lifetimes.find((block, var))
        info.creationpoints[cp] = True

    def set_use_point(block, var, *up):
        _, _, info = lifetimes.find((block, var))
        info.usepoints[up] = True

    def union(block1, var1, block2, var2):
        if isinstance(var1, Variable):
            lifetimes.union((block1, var1), (block2, var2))
        elif isinstance(var1, Constant):
            set_creation_point(block2, var2, "constant", var1)
        else:
            raise TypeError(var1)

    for var in graph.startblock.inputargs:
        set_creation_point(graph.startblock, var, "inputargs")
    set_use_point(graph.returnblock, graph.returnblock.inputargs[0], "return")
    set_use_point(graph.exceptblock, graph.exceptblock.inputargs[0], "except")
    set_use_point(graph.exceptblock, graph.exceptblock.inputargs[1], "except")

    def visit(node):
        if isinstance(node, Block):
            for op in node.operations:
                if op.opname in ("same_as", "cast_pointer"):
                    # special-case these operations to identify their input
                    # and output variables
                    union(node, op.args[0], node, op.result)
                else:
                    for i in range(len(op.args)):
                        if isinstance(op.args[i], Variable):
                            set_use_point(node, op.args[i], "op", node, op, i)
                    set_creation_point(node, op.result, "op", node, op)

        if isinstance(node, Link):
            if isinstance(node.last_exception, Variable):
                set_creation_point(node.prevblock, node.last_exception,
                                   "last_exception")
            if isinstance(node.last_exc_value, Variable):
                set_creation_point(node.prevblock, node.last_exc_value,
                                   "last_exc_value")
            for i in range(len(node.args)):
                union(node.prevblock, node.args[i],
                      node.target, node.target.inputargs[i])

    traverse(visit, graph)
    return lifetimes.infos()

def _try_inline_malloc(info):
    """Try to inline the mallocs creation and manipulation of the Variables
    in the given LifeTime."""
    # the values must be only ever created by a "malloc"
    lltypes = {}
    for cp in info.creationpoints:
        if cp[0] != "op":
            return False
        op = cp[2]
        if op.opname != "malloc":
            return False
        lltypes[op.result.concretetype] = True

    # there must be a single largest malloced GcStruct;
    # all variables can point to it or to initial substructures
    if len(lltypes) != 1:
        return False
    STRUCT = lltypes.keys()[0].TO
    assert isinstance(STRUCT, lltype.GcStruct)

    # must be only ever accessed via getfield/setfield
    for up in info.usepoints:
        if up[0] != "op":
            return False
        if (up[2].opname, up[3]) not in [("getfield", 0), ("setfield", 0)]:
            return False

    # success: replace each variable with a family of variables (one per field)
    example = STRUCT._container_example()
    flatnames = []
    flatconstants = {}
    def flatten(S, example):
        start = 0
        if S._names and isinstance(S._flds[S._names[0]], lltype.GcStruct):
            flatten(S._flds[S._names[0]], getattr(example, S._names[0]))
            start = 1
        for name in S._names[start:]:
            flatnames.append((S, name))
            constant = Constant(getattr(example, name))
            constant.concretetype = lltype.typeOf(constant.value)
            flatconstants[S, name] = constant
    flatten(STRUCT, example)

    pending = info.variables.keys()
    for block, var in pending:
        newvarsmap = {}

        def var_comes_from_outside():
            for key in flatnames:
                newvar = Variable()
                newvar.concretetype = flatconstants[key].concretetype
                newvarsmap[key] = newvar

        def var_is_created_here():
            newvarsmap.update(flatconstants)

        def make_newvars():
            return [newvarsmap[key] for key in flatnames]

        if var in block.inputargs:
            var_comes_from_outside()
            i = block.inputargs.index(var)
            block.inputargs = (block.inputargs[:i] + make_newvars() +
                               block.inputargs[i+1:])

        assert block.operations != ()
        newops = []
        try:
            for op in block.operations:
                assert var not in op.args[1:]   # should be the first arg only
                if op.args and var == op.args[0]:
                    if op.opname == "getfield":
                        S = var.concretetype.TO
                        fldname = op.args[1].value
                        newop = SpaceOperation("same_as",
                                               [newvarsmap[S, fldname]],
                                               op.result)
                        newops.append(newop)
                    elif op.opname == "setfield":
                        S = var.concretetype.TO
                        fldname = op.args[1].value
                        assert (S, fldname) in newvarsmap
                        newvarsmap[S, fldname] = op.args[2]
                    elif op.opname in ("same_as", "cast_pointer"):
                        # temporary pseudo-operation, should be removed below
                        newop = SpaceOperation("_tmp_same_as",
                                               make_newvars(),
                                               op.result)
                        newops.append(newop)
                    else:
                        raise AssertionError, op.opname
                elif var == op.result:
                    assert not newvarsmap
                    if op.opname == "malloc":
                        var_is_created_here()
                    elif op.opname in ("same_as", "cast_pointer"):
                        # in a 'v2=same_as(v1)', we must analyse v1 before
                        # we can analyse v2.  If we get them in the wrong
                        # order we cancel and reschedule v2.
                        raise Blocked
                    elif op.opname == "_tmp_same_as":
                        # pseudo-operation just introduced by the code
                        # some lines above.
                        for key, v in zip(flatnames, op.args):
                            newvarsmap[key] = v
                    else:
                        raise AssertionError, op.opname
                else:
                    newops.append(op)
        except Blocked:
            pending.append((block, var))
            continue
        block.operations[:] = newops

        for link in block.exits:
            while var in link.args:
                i = link.args.index(var)
                link.args = link.args[:i] + make_newvars() + link.args[i+1:]

    return True

def remove_mallocs_once(graph):
    """Perform one iteration of malloc removal."""
    lifetimes = compute_lifetimes(graph)
    progress = False
    for info in lifetimes:
        if _try_inline_malloc(info):
            progress = True
    return progress

def remove_simple_mallocs(graph):
    """Iteratively remove (inline) the mallocs that can be simplified away."""
    done_something = False
    while remove_mallocs_once(graph):
        done_something = True
    return done_something

# ____________________________________________________________

def backend_optimizations(graph):
    remove_same_as(graph)
    eliminate_empty_blocks(graph)
    checkgraph(graph)
    SSI_to_SSA(graph)
    #checkgraph(graph)
    if remove_simple_mallocs(graph):
        transform_dead_op_vars(graph)   # typical after malloc removal
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
