"""Flow Graph Simplification

'Syntactic-ish' simplifications on a flow graph.

simplify_graph() applies all simplifications defined in this file.
"""

import py
from pypy.objspace.flow.model import SpaceOperation
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import c_last_exception
from pypy.objspace.flow.model import checkgraph, traverse, mkentrymap
from pypy.rpython.lltypesystem import lloperation

def get_graph(arg, translator):
    from pypy.translator.translator import graphof
    if isinstance(arg, Variable):
        return None
    f = arg.value
    from pypy.rpython.lltypesystem import lltype
    if not isinstance(f, lltype._ptr):
        return None
    try:
        callable = f._obj._callable
        # external function calls don't have a real graph
        if getattr(callable, "suggested_primitive", False):
            return None
    except (AttributeError, KeyError, AssertionError):
        return None
    try:
        return f._obj.graph
    except AttributeError:
        return None
    try:
        callable = f._obj._callable
        return graphof(translator, callable)
    except (AttributeError, KeyError, AssertionError):
        return None


def replace_exitswitch_by_constant(block, const):
    assert isinstance(const, Constant)
    assert const != c_last_exception
    newexits = [link for link in block.exits
                     if link.exitcase == const.value]
    assert len(newexits) == 1
    newexits[0].exitcase = None
    if hasattr(newexits[0], 'llexitcase'):
        newexits[0].llexitcase = None
    block.exitswitch = None
    block.recloseblock(*newexits)
    return newexits

# ____________________________________________________________

def eliminate_empty_blocks(graph):
    """Eliminate basic blocks that do not contain any operations.
    When this happens, we need to replace the preceeding link with the
    following link.  Arguments of the links should be updated."""
    def visit(link):
        if isinstance(link, Link):
            while not link.target.operations:
                if (len(link.target.exits) != 1 and
                    link.target.exitswitch != c_last_exception):
                    break
                assert link.target is not link.prevblock, (
                    "the graph contains an empty infinite loop")
                block1 = link.target
                exit = block1.exits[0]
                outputargs = []
                for v in exit.args:
                    if isinstance(v, Variable):
                        # this variable is valid in the context of block1
                        # but it must come from 'link'
                        i = block1.inputargs.index(v)
                        v = link.args[i]
                    outputargs.append(v)
                link.args = outputargs
                link.target = exit.target
                # the while loop above will simplify recursively the new link
    traverse(visit, graph)

def transform_ovfcheck(graph):
    """The special function calls ovfcheck and ovfcheck_lshift need to
    be translated into primitive operations. ovfcheck is called directly
    after an operation that should be turned into an overflow-checked
    version. It is considered a syntax error if the resulting <op>-ovf
    is not defined in baseobjspace.py .
    ovfcheck_lshift is special because there is no preceding operation.
    Instead, it will be replaced by an OP_LSHIFT_OVF operation.

    The exception handling of the original operation is completely
    ignored. Only exception handlers for the ovfcheck function call
    are taken into account. This gives us the best possible control
    over situations where we want exact contol over certain operations.
    Example:

    try:
        array1[idx-1] = ovfcheck(array1[idx-1] + array2[idx+1])
    except OverflowError:
        ...

    assuming two integer arrays, we are only checking the element addition
    for overflows, but the indexing is not checked.
    """
    # General assumption:
    # empty blocks have been eliminated.
    # ovfcheck can appear in the same block with its operation.
    # this is the case if no exception handling was provided.
    # Otherwise, we have a block ending in the operation,
    # followed by a block with a single ovfcheck call.
    from pypy.rpython.rarithmetic import ovfcheck, ovfcheck_lshift
    from pypy.objspace.flow.objspace import op_appendices
    from pypy.objspace.flow.objspace import implicit_exceptions
    covf = Constant(ovfcheck)
    covfls = Constant(ovfcheck_lshift)
    appendix = op_appendices[OverflowError]
    renaming = {}
    seen_ovfblocks = {}

    # get all blocks
    blocks = {}
    def visit(block):
        if isinstance(block, Block):
            blocks[block] = True
    traverse(visit, graph)

    def is_ovfcheck(bl):
        ops = bl.operations
        return (ops and ops[-1].opname == "simple_call"
                and ops[-1].args[0] == covf)
    def is_ovfshiftcheck(bl):
        ops = bl.operations
        return (ops and ops[-1].opname == "simple_call"
                and ops[-1].args[0] == covfls)
    def is_single(bl):
        return is_ovfcheck(bl) and len(bl.operations) > 1
    def is_paired(bl):
        if bl.exits:
            ovfblock = bl.exits[0].target
        return (bl.exits and is_ovfcheck(ovfblock) and
                len(ovfblock.operations) == 1)
    def rename(v):
        return renaming.get(v, v)
    def remove_last_op(bl):
        delop = bl.operations.pop()
        assert delop.opname == "simple_call"
        assert len(delop.args) == 2
        renaming[delop.result] = rename(delop.args[1])
        for exit in bl.exits:
            exit.args = [rename(a) for a in exit.args]
            
    def check_syntax(ovfblock, block=None):
        """check whether ovfblock is reachable more than once
        or if they cheated about the argument"""
        if block:
            link = block.exits[0]
            for lprev, ltarg in zip(link.args, ovfblock.inputargs):
                renaming[ltarg] = rename(lprev)
            arg = ovfblock.operations[0].args[-1]
            res = block.operations[-1].result
            opname = block.operations[-1].opname
        else:
            arg = ovfblock.operations[-1].args[-1]
            res = ovfblock.operations[-2].result
            opname = ovfblock.operations[-2].opname
        if rename(arg) != rename(res) or ovfblock in seen_ovfblocks:
            raise SyntaxError("ovfcheck in %s: The checked operation %s"
                              " is misplaced" % (graph.name, opname))
        exlis = implicit_exceptions.get("%s_%s" % (opname, appendix), [])
        if OverflowError not in exlis:
            raise SyntaxError("ovfcheck in %s: Operation %s has no"
                              " overflow variant" % (graph.name, opname))

    blocks_to_join = False
    for block in blocks:
        if is_ovfshiftcheck(block):
            # ovfcheck_lshift:
            # simply rewrite the operation
            op = block.operations[-1]
            op.opname = "lshift" # augmented later
            op.args = op.args[1:]
        elif is_single(block):
            # remove the call to ovfcheck and keep the exceptions
            check_syntax(block)
            remove_last_op(block)
            seen_ovfblocks[block] = True
        elif is_paired(block):
            # remove the block's exception links
            link = block.exits[0]
            ovfblock = link.target
            check_syntax(ovfblock, block)
            block.exits = [link]
            block.exitswitch = None
            # remove the ovfcheck call from the None target
            remove_last_op(ovfblock)
            seen_ovfblocks[ovfblock] = True
            blocks_to_join = True
        else:
            continue
        op = block.operations[-1]
        op.opname = "%s_%s" % (op.opname, appendix)
    if blocks_to_join:
        join_blocks(graph)

def simplify_exceptions(graph):
    """The exception handling caused by non-implicit exceptions
    starts with an exitswitch on Exception, followed by a lengthy
    chain of is_/issubtype tests. We collapse them all into
    the block's single list of exits.
    """
    clastexc = c_last_exception
    renaming = {}
    def rename(v):
        return renaming.get(v, v)

    def visit(block):
        if not (isinstance(block, Block)
                and block.exitswitch == clastexc
                and block.exits[-1].exitcase is Exception):
            return
        covered = [link.exitcase for link in block.exits[1:-1]]
        seen = []
        preserve = list(block.exits[:-1])
        exc = block.exits[-1]
        last_exception = exc.last_exception
        last_exc_value = exc.last_exc_value
        query = exc.target
        switches = []
        # collect the targets
        while len(query.exits) == 2:
            newrenaming = {}
            for lprev, ltarg in zip(exc.args, query.inputargs):
                newrenaming[ltarg] = rename(lprev)
            op = query.operations[0]
            if not (op.opname in ("is_", "issubtype") and
                    newrenaming.get(op.args[0]) == last_exception):
                break
            renaming.update(newrenaming)
            case = query.operations[0].args[-1].value
            assert issubclass(case, py.builtin.BaseException)
            lno, lyes = query.exits
            assert lno.exitcase == False and lyes.exitcase == True
            if case not in seen:
                is_covered = False
                for cov in covered:
                    if issubclass(case, cov):
                        is_covered = True
                        break
                if not is_covered:
                    switches.append( (case, lyes) )
                seen.append(case)
            exc = lno
            query = exc.target
        if Exception not in seen:
            switches.append( (Exception, exc) )
        # construct the block's new exits
        exits = []
        for case, oldlink in switches:
            link = oldlink.copy(rename)
            assert case is not None
            link.last_exception = last_exception
            link.last_exc_value = last_exc_value
            # make the above two variables unique
            renaming2 = {}
            def rename2(v):
                return renaming2.get(v, v)
            for v in link.getextravars():
                renaming2[v] = Variable(v)
            link = link.copy(rename2)
            link.exitcase = case
            link.prevblock = block
            exits.append(link)
        block.exits = tuple(preserve + exits)

    traverse(visit, graph)

def remove_dead_exceptions(graph):
    """Exceptions can be removed if they are unreachable"""

    clastexc = c_last_exception

    def issubclassofmember(cls, seq):
        for member in seq:
            if member and issubclass(cls, member):
                return True
        return False

    def visit(block):
        if not (isinstance(block, Block) and block.exitswitch == clastexc):
            return
        exits = []
        seen = []
        for link in block.exits:
            case = link.exitcase
            # check whether exceptions are shadowed
            if issubclassofmember(case, seen):
                continue
            # see if the previous case can be merged
            while len(exits) > 1:
                prev = exits[-1]
                if not (issubclass(prev.exitcase, link.exitcase) and
                    prev.target is link.target and prev.args == link.args):
                    break
                exits.pop()
            exits.append(link)
            seen.append(case)
        block.exits = tuple(exits)

    traverse(visit, graph)

def join_blocks(graph):
    """Links can be deleted if they are the single exit of a block and
    the single entry point of the next block.  When this happens, we can
    append all the operations of the following block to the preceeding
    block (but renaming variables with the appropriate arguments.)
    """
    entrymap = mkentrymap(graph)
    block = graph.startblock
    seen = {block: True}
    stack = list(block.exits)
    while stack:
        link = stack.pop()
        if (len(link.prevblock.exits) == 1 and
            len(entrymap[link.target]) == 1 and
            link.target.exits):  # stop at the returnblock
            renaming = {}
            for vprev, vtarg in zip(link.args, link.target.inputargs):
                renaming[vtarg] = vprev
            def rename(v):
                return renaming.get(v, v)
            def rename_op(op):
                args = [rename(a) for a in op.args]
                op = SpaceOperation(op.opname, args, rename(op.result), op.offset)
                #op = SpaceOperation(op.opname, args, rename(op.result))
                return op
            for op in link.target.operations:
                link.prevblock.operations.append(rename_op(op))
            exits = []
            for exit in link.target.exits:
                newexit = exit.copy(rename)
                exits.append(newexit)
            newexitswitch = rename(link.target.exitswitch)
            link.prevblock.exitswitch = newexitswitch
            link.prevblock.recloseblock(*exits)
            if isinstance(newexitswitch, Constant) and newexitswitch != c_last_exception:
                exits = replace_exitswitch_by_constant(link.prevblock,
                                                       newexitswitch)
            stack.extend(exits)
        else:
            if link.target not in seen:
                stack.extend(link.target.exits)
                seen[link.target] = True

def remove_assertion_errors(graph):
    """Remove branches that go directly to raising an AssertionError,
    assuming that AssertionError shouldn't occur at run-time.  Note that
    this is how implicit exceptions are removed (see _implicit_ in
    flowcontext.py).
    """
    def visit(block):
        if isinstance(block, Block):
            for i in range(len(block.exits)-1, -1, -1):
                exit = block.exits[i]
                if not (exit.target is graph.exceptblock and
                        exit.args[0] == Constant(AssertionError)):
                    continue
                # can we remove this exit without breaking the graph?
                if len(block.exits) < 2:
                    break
                if block.exitswitch == c_last_exception:
                    if exit.exitcase is None:
                        break
                    if len(block.exits) == 2:
                        # removing the last non-exceptional exit
                        block.exitswitch = None
                        exit.exitcase = None
                # remove this exit
                lst = list(block.exits)
                del lst[i]
                block.exits = tuple(lst)
    traverse(visit, graph)


# _____________________________________________________________________
# decide whether a function has side effects

def op_has_side_effects(op):
    return lloperation.LL_OPERATIONS[op.opname].sideeffects

def has_no_side_effects(translator, graph, seen=None):
    #is the graph specialized? if no we can't say anything
    #don't cache the result though
    if translator.rtyper is None:
        return False
    else:
        if graph.startblock not in translator.rtyper.already_seen:
            return False
    if seen is None:
        seen = {}
    elif graph in seen:
        return True
    newseen = seen.copy()
    newseen[graph] = True
    for block in graph.iterblocks():
        if block is graph.exceptblock:
            return False     # graphs explicitly raising have side-effects
        for op in block.operations:
            if op.opname == "direct_call":
                g = get_graph(op.args[0], translator)
                if g is None:
                    return False
                if not has_no_side_effects(translator, g, newseen):
                    return False
            elif op.opname == "indirect_call":
                graphs = op.args[-1].value
                if graphs is None:
                    return False
                for g in graphs:
                    if not has_no_side_effects(translator, g, newseen):
                        return False
            elif op_has_side_effects(op):
                return False
    return True

# ___________________________________________________________________________
# remove operations if their result is not used and they have no side effects

def transform_dead_op_vars(graph, translator=None):
    """Remove dead operations and variables that are passed over a link
    but not used in the target block. Input is a graph."""
    blocks = {}
    def visit(block):
        if isinstance(block, Block):
            blocks[block] = True
    traverse(visit, graph)
    return transform_dead_op_vars_in_blocks(blocks, translator)

# the set of operations that can safely be removed
# (they have no side effects, at least in R-Python)
CanRemove = {}
for _op in '''
        newtuple newlist newdict newslice is_true
        is_ id type issubtype repr str len hash getattr getitem
        pos neg nonzero abs hex oct ord invert add sub mul
        truediv floordiv div mod divmod pow lshift rshift and_ or_
        xor int float long lt le eq ne gt ge cmp coerce contains
        iter get'''.split():
    CanRemove[_op] = True
from pypy.rpython.lltypesystem.lloperation import enum_ops_without_sideeffects
for _op in enum_ops_without_sideeffects():
    CanRemove[_op] = True
del _op
CanRemoveBuiltins = {
    isinstance: True,
    hasattr: True,
    }

def transform_dead_op_vars_in_blocks(blocks, translator=None):
    """Remove dead operations and variables that are passed over a link
    but not used in the target block. Input is a set of blocks"""
    read_vars = {}  # set of variables really used
    variable_flow = {}  # map {Var: list-of-Vars-it-depends-on}

    transport_flow = {} # map {Var: list-of-Vars-depending-on-it-through-links-or-indentity-ops}

    keepalive_vars = {} # set of variables in keepalives 

    def canremove(op, block):
        if op.opname not in CanRemove:
            return False
        if block.exitswitch != c_last_exception:
            return True
        # cannot remove the exc-raising operation
        return op is not block.operations[-1]

    # compute variable_flow and an initial read_vars
    for block in blocks:
        # figure out which variables are ever read
        for op in block.operations:
            if op.opname == 'keepalive':
                keepalive_vars[op.args[0]] = True
            elif not canremove(op, block):   # mark the inputs as really needed
                for arg in op.args:
                    read_vars[arg] = True
            else:
                # if CanRemove, only mark dependencies of the result
                # on the input variables
                deps = variable_flow.setdefault(op.result, [])
                deps.extend(op.args)
                if op.opname in ('cast_pointer', 'same_as'):
                    transport_flow.setdefault(op.args[0], []).append(op.result)

        if isinstance(block.exitswitch, Variable):
            read_vars[block.exitswitch] = True

        if block.exits:
            for link in block.exits:
                if link.target not in blocks:
                    for arg, targetarg in zip(link.args, link.target.inputargs):
                        read_vars[arg] = True
                        read_vars[targetarg] = True
                else:
                    for arg, targetarg in zip(link.args, link.target.inputargs):
                        deps = variable_flow.setdefault(targetarg, [])
                        deps.append(arg)
                        transport_flow.setdefault(arg, []).append(targetarg)                        
        else:
            # return and except blocks implicitely use their input variable(s)
            for arg in block.inputargs:
                read_vars[arg] = True
        # an input block's inputargs should not be modified, even if some
        # of the function's input arguments are not actually used
        if block.isstartblock:
            for arg in block.inputargs:
                read_vars[arg] = True

    # flow read_vars backwards so that any variable on which a read_vars
    # depends is also included in read_vars
    def flow_read_var_backward(pending):
        pending = list(pending)
        for var in pending:
            for prevvar in variable_flow.get(var, []):
                if prevvar not in read_vars:
                    read_vars[prevvar] = True
                    pending.append(prevvar)

    flow_read_var_backward(read_vars)
    
    # compute vars depending on a read-var through the transport-flow
    read_var_aliases = {}
    pending = []
    for var in transport_flow:
        if var in read_vars:
            pending.append(var)
            read_var_aliases[var] = True
    for var in pending:
        for nextvar in transport_flow.get(var, []):
            if nextvar not in read_var_aliases:
                read_var_aliases[nextvar] = True
                pending.append(nextvar)
        
    # a keepalive var is read-var if it's an alias reached from some read-var
    # through the transport flow
    new_read_vars = {}
    for var in keepalive_vars:
        if var in read_var_aliases:
            read_vars[var] = True
            new_read_vars[var] = True

    # flow backward the new read-vars
    flow_read_var_backward(new_read_vars)
    

    for block in blocks:

        # look for removable operations whose result is never used
        for i in range(len(block.operations)-1, -1, -1):
            op = block.operations[i]
            if op.result not in read_vars: 
                if canremove(op, block):
                    del block.operations[i]
                elif op.opname == 'keepalive':
                    if op.args[0] not in read_vars:
                        del block.operations[i]                        
                elif op.opname == 'simple_call': 
                    # XXX we want to have a more effective and safe 
                    # way to check if this operation has side effects
                    # ... 
                    if op.args and isinstance(op.args[0], Constant):
                        func = op.args[0].value
                        try:
                            if func in CanRemoveBuiltins:
                                del block.operations[i]
                        except TypeError:   # func is not hashable
                            pass
                elif op.opname == 'direct_call':
                    if translator is not None:
                        graph = get_graph(op.args[0], translator)
                        if (graph is not None and
                            has_no_side_effects(translator, graph) and
                            (block.exitswitch != c_last_exception or
                             i != len(block.operations)- 1)):
                            del block.operations[i]
        # look for output variables never used
        # warning: this must be completely done *before* we attempt to
        # remove the corresponding variables from block.inputargs!
        # Otherwise the link.args get out of sync with the
        # link.target.inputargs.
        for link in block.exits:
            assert len(link.args) == len(link.target.inputargs)
            for i in range(len(link.args)-1, -1, -1):
                if link.target.inputargs[i] not in read_vars:
                    del link.args[i]
            # the above assert would fail here

    for block in blocks:
        # look for input variables never used
        # The corresponding link.args have already been all removed above
        for i in range(len(block.inputargs)-1, -1, -1):
            if block.inputargs[i] not in read_vars:
                del block.inputargs[i]

def remove_identical_vars(graph):
    """When the same variable is passed multiple times into the next block,
    pass it only once.  This enables further optimizations by the annotator,
    which otherwise doesn't realize that tests performed on one of the copies
    of the variable also affect the other."""

    # This algorithm is based on DataFlowFamilyBuilder, used as a
    # "phi node remover" (in the SSA sense).  'variable_families' is a
    # UnionFind object that groups variables by families; variables from the
    # same family can be identified, and if two input arguments of a block
    # end up in the same family, then we really remove one of them in favor
    # of the other.
    #
    # The idea is to identify as much variables as possible by trying
    # iteratively two kinds of phi node removal:
    #
    #  * "vertical", by identifying variables from different blocks, when
    #    we see that a value just flows unmodified into the next block without
    #    needing any merge (this is what backendopt.ssa.SSI_to_SSA() would do
    #    as well);
    #
    #  * "horizontal", by identifying two input variables of the same block,
    #    when these two variables' phi nodes have the same argument -- i.e.
    #    when for all possible incoming paths they would get twice the same
    #    value (this is really the purpose of remove_identical_vars()).
    #
    from pypy.translator.backendopt.ssa import DataFlowFamilyBuilder
    builder = DataFlowFamilyBuilder(graph)
    variable_families = builder.get_variable_families()  # vertical removal
    while True:
        if not builder.merge_identical_phi_nodes():    # horizontal removal
            break
        if not builder.complete():                     # vertical removal
            break

    for block, links in mkentrymap(graph).items():
        if block is graph.startblock:
            continue
        renaming = {}
        family2blockvar = {}
        kills = []
        for i, v in enumerate(block.inputargs):
            v1 = variable_families.find_rep(v)
            if v1 in family2blockvar:
                # already seen -- this variable can be shared with the
                # previous one
                renaming[v] = family2blockvar[v1]
                kills.append(i)
            else:
                family2blockvar[v1] = v
        if renaming:
            block.renamevariables(renaming)
            # remove the now-duplicate input variables
            kills.reverse()   # starting from the end
            for i in kills:
                del block.inputargs[i]
                for link in links:
                    del link.args[i]


def coalesce_is_true(graph):
    """coalesce paths that go through an is_true and a directly successive
       is_true both on the same value, transforming the link into the
       second is_true from the first to directly jump to the correct
       target out of the second."""
    candidates = []

    def has_is_true_exitpath(block):
        tgts = []
        start_op = block.operations[-1]
        cond_v = start_op.args[0]
        if block.exitswitch == start_op.result:
            for exit in block.exits:
                tgt = exit.target
                if tgt == block:
                    continue
                rrenaming = dict(zip(tgt.inputargs,exit.args))
                if len(tgt.operations) == 1 and tgt.operations[0].opname == 'is_true':
                    tgt_op = tgt.operations[0]
                    if tgt.exitswitch == tgt_op.result and rrenaming.get(tgt_op.args[0]) == cond_v:
                        tgts.append((exit.exitcase, tgt))
        return tgts

    def visit(block):
        if isinstance(block, Block) and block.operations and block.operations[-1].opname == 'is_true':
            tgts = has_is_true_exitpath(block)
            if tgts:
                candidates.append((block, tgts))
    traverse(visit, graph)

    while candidates:
        cand, tgts = candidates.pop()
        newexits = list(cand.exits) 
        for case, tgt in tgts:
            exit = cand.exits[case]
            rrenaming = dict(zip(tgt.inputargs,exit.args))
            rrenaming[tgt.operations[0].result] = cand.operations[-1].result
            def rename(v):
                return rrenaming.get(v,v)
            newlink = tgt.exits[case].copy(rename)
            newexits[case] = newlink
        cand.recloseblock(*newexits)
        newtgts = has_is_true_exitpath(cand)
        if newtgts:
            candidates.append((cand, newtgts))
            
# ____ all passes & simplify_graph

all_passes = [
    eliminate_empty_blocks,
    remove_assertion_errors,
    join_blocks,
    coalesce_is_true,
    transform_dead_op_vars,
    remove_identical_vars,
    transform_ovfcheck,
    simplify_exceptions,
    remove_dead_exceptions,
    ]

def simplify_graph(graph, passes=True): # can take a list of passes to apply, True meaning all
    """inplace-apply all the existing optimisations to the graph."""
    if passes is True:
        passes = all_passes
    checkgraph(graph)
    for pass_ in passes:
        pass_(graph)
    checkgraph(graph)

def cleanup_graph(graph):
    checkgraph(graph)
    eliminate_empty_blocks(graph)
    join_blocks(graph)
    remove_identical_vars(graph)
    checkgraph(graph)    
    
