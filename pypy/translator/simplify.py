"""Flow Graph Simplification

'Syntactic-ish' simplifications on a flow graph.

simplify_graph() applies all simplifications defined in this file.
"""

from pypy.objspace.flow.model import SpaceOperation
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import last_exception
from pypy.objspace.flow.model import checkgraph, traverse, mkentrymap

def simplify_graph(graph):
    """inplace-apply all the existing optimisations to the graph."""
    checkgraph(graph)
    eliminate_empty_blocks(graph)
    remove_assertion_errors(graph)
    join_blocks(graph)
    transform_dead_op_vars(graph)
    remove_identical_vars(graph)
    transform_ovfcheck(graph)
    simplify_exceptions(graph)
    remove_dead_exceptions(graph)
    checkgraph(graph)

# ____________________________________________________________

def eliminate_empty_blocks(graph):
    """Eliminate basic blocks that do not contain any operations.
    When this happens, we need to replace the preceeding link with the
    following link.  Arguments of the links should be updated."""
    def visit(link):
        if isinstance(link, Link):
            while not link.target.operations and len(link.target.exits) == 1:
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
        ovfcheck(array1[idx-1] += array2[idx+1])
    except OverflowError:
        ...

    assuming two integer arrays, we are only checking the element addition
    for overflows, but the indexing is not checked.
    """
    # General assumption:
    # empty blocks have been eliminated.
    # ovfcheck can appear in the same blcok with its operation.
    # this is the case if no exception handling was provided.
    # Otherwise, we have a block ending in the operation,
    # followed by a block with a single ovfcheck call.
    from pypy.tool.rarithmetic import ovfcheck, ovfcheck_lshift
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
        return bl.exits and is_ovfcheck(bl.exits[0].target)
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
            raise SyntaxError("ovfcheck: The checked operation %s is misplaced"
                              % opname)
        exlis = implicit_exceptions.get("%s_%s" % (opname, appendix), [])
        if OverflowError not in exlis:
            raise SyntaxError("ovfcheck: Operation %s has no overflow variant"
                              % opname)

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
    the block's single list of exits and also remove unreachable
    cases.
    """
    clastexc = Constant(last_exception)
    renaming = {}
    def rename(v):
        return renaming.get(v, v)

    def visit(block):
        if not (isinstance(block, Block)
                and block.exitswitch == clastexc and len(block.exits) == 2
                and block.exits[1].exitcase is Exception):
            return
        seen = []
        norm, exc = block.exits
        query = exc.target
        switches = [ (None, norm) ]
        # collect the targets
        while len(query.exits) == 2:
            for lprev, ltarg in zip(exc.args, query.inputargs):
                renaming[ltarg] = rename(lprev)
            op = query.operations[0]
            if not (op.opname in ("is_", "issubtype") and
                    rename(op.args[0]) == clastexc):
                break
            case = query.operations[0].args[-1].value
            assert issubclass(case, Exception)
            lno, lyes = query.exits
            if case not in seen:
                switches.append( (case, lyes) )
                seen.append(case)
            exc = lno
            query = exc.target
        if Exception not in seen:
            switches.append( (Exception, exc) )
        # construct the block's new exits
        exits = []
        for case, oldlink in switches:
            args = [rename(arg) for arg in oldlink.args]
            link = Link(args, oldlink.target, case)
            link.prevblock = block
            exits.append(link)
        block.exits = tuple(exits)

    traverse(visit, graph)

def remove_dead_exceptions(graph):
    """Exceptions can be removed if they are unreachable"""

    clastexc = Constant(last_exception)

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
    
    def visit(link):
        if isinstance(link, Link):
            if (len(link.prevblock.exits) == 1 and
                len(entrymap[link.target]) == 1 and
                link.target.exits):  # stop at the returnblock
                renaming = {}
                for vprev, vtarg in zip(link.args, link.target.inputargs):
                    renaming[vtarg] = vprev
                def rename(v):
                    return renaming.get(v, v)
                for op in link.target.operations:
                    args = [rename(a) for a in op.args]
                    op = SpaceOperation(op.opname, args, rename(op.result))
                    link.prevblock.operations.append(op)
                exits = []
                for exit in link.target.exits:
                    args = [rename(a) for a in exit.args]
                    exits.append(Link(args, exit.target, exit.exitcase))
                link.prevblock.exitswitch = rename(link.target.exitswitch)
                link.prevblock.recloseblock(*exits)
                # simplify recursively the new links
                for exit in exits:
                    visit(exit)
    traverse(visit, graph)

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
                if block.exitswitch == Constant(last_exception):
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

def transform_dead_op_vars(graph):
    """Remove dead operations and variables that are passed over a link
    but not used in the target block. Input is a graph."""
    blocks = {}
    def visit(block):
        if isinstance(block, Block):
            blocks[block] = True
    traverse(visit, graph)
    return transform_dead_op_vars_in_blocks(blocks)

# the set of operations that can safely be removed
# (they have no side effects, at least in R-Python)
CanRemove = {}
for _op in '''
        newtuple newlist newdict newslice is_true
        is_ id type issubtype repr str len hash getattr getitem
        pos neg nonzero abs hex oct ord invert add sub mul
        truediv floordiv div mod divmod pow lshift rshift and_ or_
        xor int float long lt le eq ne gt ge cmp coerce contains
        iter get '''.split():
    CanRemove[_op] = True
del _op

def transform_dead_op_vars_in_blocks(blocks):
    """Remove dead operations and variables that are passed over a link
    but not used in the target block. Input is a set of blocks"""
    read_vars = {}  # set of variables really used
    variable_flow = {}  # map {Var: list-of-Vars-it-depends-on}

    def canremove(op, block):
        if op.opname not in CanRemove:
            return False
        if block.exitswitch != Constant(last_exception):
            return True
        # cannot remove the exc-raising operation
        return op is not block.operations[-1]

    # compute variable_flow and an initial read_vars
    for block in blocks:
        # figure out which variables are ever read
        for op in block.operations:
            if not canremove(op, block):   # mark the inputs as really needed
                for arg in op.args:
                    read_vars[arg] = True
            else:
                # if CanRemove, only mark dependencies of the result
                # on the input variables
                deps = variable_flow.setdefault(op.result, [])
                deps.extend(op.args)

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
    pending = list(read_vars)
    for var in pending:
        for prevvar in variable_flow.get(var, []):
            if prevvar not in read_vars:
                read_vars[prevvar] = True
                pending.append(prevvar)

    for block in blocks:

        # look for removable operations whose result is never used
        for i in range(len(block.operations)-1, -1, -1):
            op = block.operations[i]
            if op.result not in read_vars: 
                if canremove(op, block):
                    del block.operations[i]
                elif op.opname == 'simple_call': 
                    # XXX we want to have a more effective and safe 
                    # way to check if this operation has side effects
                    # ... 
                    if op.args and isinstance(op.args[0], Constant):
                        func = op.args[0].value
                        if func is isinstance:
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

    entrymap = mkentrymap(graph)
    consider_blocks = entrymap

    while consider_blocks:
        blocklist = consider_blocks.keys()
        consider_blocks = {}
        for block in blocklist:
            if not block.exits:
                continue
            links = entrymap[block]
            entryargs = {}
            for i in range(len(block.inputargs)):
                # list of possible vars that can arrive in i'th position
                key = tuple([link.args[i] for link in links])
                if key not in entryargs:
                    entryargs[key] = i
                else:
                    j = entryargs[key]
                    # positions i and j receive exactly the same input vars,
                    # we can remove the argument i and replace it with the j.
                    argi = block.inputargs[i]
                    if not isinstance(argi, Variable): continue
                    argj = block.inputargs[j]
                    block.renamevariables({argi: argj})
                    assert block.inputargs[i] == block.inputargs[j] == argj
                    del block.inputargs[i]
                    for link in links:
                        assert link.args[i] == link.args[j]
                        del link.args[i]
                    # mark this block and all the following ones as subject to
                    # possible further optimization
                    consider_blocks[block] = True
                    for link in block.exits:
                        consider_blocks[link.target] = True
                    break
