"""Flow Graph Simplification

'Syntactic-ish' simplifications on a flow graph.

simplify_graph() applies all simplifications defined in this file.
"""

from pypy.objspace.flow.model import *

def simplify_graph(graph):
    """inplace-apply all the existing optimisations to the graph."""
    checkgraph(graph)
    eliminate_empty_blocks(graph)
    remove_assertion_errors(graph)
    join_blocks(graph)
    transform_dead_op_vars(graph)
    remove_identical_vars(graph)
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
