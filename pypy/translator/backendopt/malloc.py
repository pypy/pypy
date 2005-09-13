from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, traverse
from pypy.tool.unionfind import UnionFind
from pypy.rpython import lltype

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
