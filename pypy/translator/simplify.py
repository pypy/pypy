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
    traverse(visit, graph)

def simplify_graph(graph, rpython=True):
    """inplace-apply all the existing optimisations to the graph."""
    checkgraph(graph)
    eliminate_empty_blocks(graph)
    if rpython:
        remove_implicit_exceptions(graph)
    join_blocks(graph)
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
