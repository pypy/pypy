"""Flow Graph Simplification
"""

from pypy.objspace.flow.model import *

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

def remove_implicit_exceptions(graph):
    """An exception raised implicitely has a particular value of
    space.wrap(last_exception) -- see pypy.objspace.flow.objspace.make_op --
    which shows up in the flow graph if the exception is not caught.  This
    function removes such exceptions entierely.  This gets rid for example
    of possible IndexErrors by 'getitem', assuming they cannot happen unless
    there is an exception handler in the same function."""
    def visit(link):
        if isinstance(link, Link) and link in link.prevblock.exits:
            if (link.target is graph.exceptblock and
                link.prevblock.exitswitch == Constant(last_exception) and
                isinstance(link.exitcase, type(Exception)) and
                issubclass(link.exitcase, Exception) and
                len(link.args) == 2 and
                link.args[1] == Constant(last_exc_value) and
                link.args[0] in [Constant(last_exception),
                                 Constant(link.exitcase)]):
                # remove the link
                lst = list(link.prevblock.exits)
                lst.remove(link)
                link.prevblock.exits = tuple(lst)
                if len(lst) <= 1:
                    link.prevblock.exitswitch = None
    traverse(visit, graph)

def simplify_graph(graph):
    """inplace-apply all the existing optimisations to the graph."""
    checkgraph(graph)
    eliminate_empty_blocks(graph)
    remove_implicit_exceptions(graph)
    join_blocks(graph)
    transform_dead_op_vars(graph)
    checkgraph(graph)

def remove_direct_loops(graph):
    """This is useful for code generators: it ensures that no link has
    common input and output variables, which could occur if a block's exit
    points back directly to the same block.  It allows code generators to be
    simpler because they don't have to worry about overwriting input
    variables when generating a sequence of assignments."""
    def visit(link):
        if isinstance(link, Link) and link.prevblock is link.target:
            # insert an empty block with fresh variables.
            intermediate = [Variable() for a in link.args]
            b = Block(intermediate)
            b.closeblock(Link(intermediate, link.target))
            link.target = b
    traverse(visit, graph)

def transform_dead_op_vars(graph):
    """Remove dead operations and variables that are passed over a link
    but not used in the target block. Input is a graph."""
    blocklist = []
    def visit(block):
        if isinstance(block, Block):
            blocklist.append(block)
    traverse(visit, graph)
    return transform_dead_op_vars_blocklist(blocklist)

def transform_dead_op_vars_blocklist(blocklist):
    """Remove dead operations and variables that are passed over a link
    but not used in the target block. Input is a block list"""
    # the set of operations that can safely be removed (no side effects)
    CanRemove = {'newtuple': True,
                 'newlist': True,
                 'newdict': True,
                 'is_': True, 
                 'is_true': True}
    read_vars = {}  # set of variables really used
    variable_flow = {}  # map {Var: list-of-Vars-it-depends-on}
    
    # compute variable_flow and an initial read_vars
    for block in blocklist:
        # figure out which variables are ever read
        for op in block.operations:
            if op.opname not in CanRemove:  # mark the inputs as really needed
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
                if link.target not in blocklist:
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

    for block in blocklist:

        # look for removable operations whose result is never used
        for i in range(len(block.operations)-1, -1, -1):
            op = block.operations[i]
            if op.result not in read_vars: 
                if op.opname in CanRemove: 
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

    for block in blocklist:
        # look for input variables never used
        # The corresponding link.args have already been all removed above
        for i in range(len(block.inputargs)-1, -1, -1):
            if block.inputargs[i] not in read_vars:
                del block.inputargs[i]
