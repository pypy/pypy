from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, traverse, checkgraph
from pypy.tool.algo.unionfind import UnionFind
from pypy.rpython import lltype
from pypy.translator.simplify import remove_identical_vars
from pypy.translator.backendopt.support import log

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
            if isinstance(node.exitswitch, Variable):
                set_use_point(node, node.exitswitch, "exitswitch", node)

        if isinstance(node, Link):
            if isinstance(node.last_exception, Variable):
                set_creation_point(node.prevblock, node.last_exception,
                                   "last_exception")
            if isinstance(node.last_exc_value, Variable):
                set_creation_point(node.prevblock, node.last_exc_value,
                                   "last_exc_value")
            d = {}
            for i, arg in enumerate(node.args):
                union(node.prevblock, arg,
                      node.target, node.target.inputargs[i])
                if isinstance(arg, Variable):
                    if arg in d:
                        # same variable present several times in link.args
                        # consider it as a 'use' of the variable, which
                        # will disable malloc optimization (aliasing problems)
                        set_use_point(node.prevblock, arg, "dup", node, i)
                    else:
                        d[arg] = True

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

    # must be only ever accessed via getfield/setfield or touched by keepalive
    for up in info.usepoints:
        if up[0] != "op":
            return False
        kind, node, op, index = up
        if (op.opname, index) in [("getfield", 0),
                                  ("setfield", 0),
                                  ("keepalive", 0)]:
            continue   # ok
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

    variables_by_block = {}
    for block, var in info.variables:
        vars = variables_by_block.setdefault(block, {})
        vars[var] = True

    for block, vars in variables_by_block.items():

        def flowin(var, newvarsmap):
            # in this 'block', follow where the 'var' goes to and replace
            # it by a flattened-out family of variables.  This family is given
            # by newvarsmap, whose keys are the 'flatnames'.
            vars = {var: True}

            def list_newvars():
                return [newvarsmap[key] for key in flatnames]

            assert block.operations != ()
            newops = []
            for op in block.operations:
                for arg in op.args[1:]:   # should be the first arg only
                    assert arg not in vars
                if op.args and op.args[0] in vars:
                    if op.opname == "getfield":
                        S = op.args[0].concretetype.TO
                        fldname = op.args[1].value
                        newop = SpaceOperation("same_as",
                                               [newvarsmap[S, fldname]],
                                               op.result)
                        newops.append(newop)
                    elif op.opname == "setfield":
                        S = op.args[0].concretetype.TO
                        fldname = op.args[1].value
                        assert (S, fldname) in newvarsmap
                        newvarsmap[S, fldname] = op.args[2]
                    elif op.opname in ("same_as", "cast_pointer"):
                        assert op.result not in vars
                        vars[op.result] = True
                        # Consider the two pointers (input and result) as
                        # equivalent.  We can, and indeed must, use the same
                        # flattened list of variables for both, as a "setfield"
                        # via one pointer must be reflected in the other.
                    elif op.opname == 'keepalive':
                        pass
                    else:
                        raise AssertionError, op.opname
                elif op.result in vars:
                    assert op.opname == "malloc"
                    assert vars == {var: True}
                    # drop the "malloc" operation
                else:
                    newops.append(op)
            block.operations[:] = newops
            assert block.exitswitch not in vars

            for link in block.exits:
                newargs = []
                for arg in link.args:
                    if arg in vars:
                        newargs += list_newvars()
                    else:
                        newargs.append(arg)
                link.args[:] = newargs

        # look for variables arriving from outside the block
        for var in vars:
            if var in block.inputargs:
                i = block.inputargs.index(var)
                newinputargs = block.inputargs[:i]
                newvarsmap = {}
                for key in flatnames:
                    newvar = Variable()
                    newvar.concretetype = flatconstants[key].concretetype
                    newvarsmap[key] = newvar
                    newinputargs.append(newvar)
                newinputargs += block.inputargs[i+1:]
                block.inputargs[:] = newinputargs
                assert var not in block.inputargs
                flowin(var, newvarsmap)

        # look for variables created inside the block by a malloc
        vars_created_here = []
        for op in block.operations:
            if op.opname == "malloc" and op.result in vars:
                vars_created_here.append(op.result)
        for var in vars_created_here:
            newvarsmap = flatconstants.copy()   # dummy initial values
            flowin(var, newvarsmap)

    return True

def remove_mallocs_once(graph):
    """Perform one iteration of malloc removal."""
    remove_identical_vars(graph)
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
        log.malloc('simple mallocs removed in %r' % graph.name)
        done_something = True
    return done_something
