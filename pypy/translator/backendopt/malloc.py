from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, traverse
from pypy.tool.algo.unionfind import UnionFind
from pypy.rpython.lltypesystem import lltype
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


def equivalent_substruct(S, fieldname):
    # we consider a pointer to a GcStruct S as equivalent to a
    # pointer to a substructure 'S.fieldname' if it's the first
    # inlined sub-GcStruct.  As an extension we also allow a pointer
    # to a GcStruct containing just one Struct to be equivalent to
    # a pointer to that Struct only (although a mere cast_pointer
    # would not allow casting).  This is needed to malloc-remove
    # the 'wrapper' GcStructs introduced by previous passes of
    # malloc removal.
    if not isinstance(S, lltype.GcStruct):
        return False
    if fieldname != S._names[0]:
        return False
    FIELDTYPE = S._flds[fieldname]
    if isinstance(FIELDTYPE, lltype.GcStruct):
        return True
    if len(S._names) == 1 and isinstance(FIELDTYPE, lltype.Struct):
        return 'wrapper'
    return False


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
                    continue
                if op.opname == 'getsubstruct':
                    S = op.args[0].concretetype.TO
                    if equivalent_substruct(S, op.args[1].value):
                        # assumed to be similar to a cast_pointer
                        union(node, op.args[0], node, op.result)
                        continue
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

    # must be only ever accessed via getfield/setfield/getsubstruct
    # or touched by keepalive.  Note that same_as and cast_pointer
    # are not recorded in usepoints.
    VALID = dict.fromkeys([("getfield", 0),
                           ("setfield", 0),
                           ("getsubstruct", 0),
                           ("keepalive", 0)])
    for up in info.usepoints:
        if up[0] != "op":
            return False
        kind, node, op, index = up
        if (op.opname, index) in VALID:
            continue   # ok
        return False

    # must not remove mallocs of structures that have a RTTI with a destructor

    try:
        destr_ptr = lltype.getRuntimeTypeInfo(STRUCT)._obj.destructor_funcptr
        if destr_ptr:
            return False
    except (ValueError, AttributeError), e:
        pass
    
    # success: replace each variable with a family of variables (one per field)
    example = STRUCT._container_example()

    # 'flatnames' is a list of (STRUCTTYPE, fieldname_in_that_struct) that
    # describes the list of variables that should replace the single
    # malloc'ed pointer variable that we are about to remove.  For primitive
    # or pointer fields, the new corresponding variable just stores the
    # actual value.  For substructures, if pointers to them are "equivalent"
    # to pointers to the parent structure (see equivalent_substruct()) then
    # they are just merged, and flatnames will also list the fields within
    # that substructure.  Other substructures are replaced by a single new
    # variable which is a pointer to a GcStruct-wrapper; each is malloc'ed
    # individually, in an exploded way.  (The next malloc removal pass will
    # get rid of them again, in the typical case.)
    flatnames = []
    flatconstants = {}
    needsubmallocs = []
    newvarstype = {}       # map {item-of-flatnames: concretetype}

    def flatten(S, example):
        start = 0
        if S._names and equivalent_substruct(S, S._names[0]):
            flatten(S._flds[S._names[0]], getattr(example, S._names[0]))
            start = 1
        for name in S._names[start:]:
            key = S, name
            flatnames.append(key)
            FIELDTYPE = S._flds[name]
            if isinstance(FIELDTYPE, lltype.ContainerType):
                needsubmallocs.append(key)
                newvarstype[key] = lltype.Ptr(lltype.GcStruct('wrapper',
                                                          ('data', FIELDTYPE)))
            else:
                constant = Constant(getattr(example, name))
                constant.concretetype = FIELDTYPE
                flatconstants[key] = constant
                newvarstype[key] = FIELDTYPE

    flatten(STRUCT, example)

    variables_by_block = {}
    for block, var in info.variables:
        vars = variables_by_block.setdefault(block, {})
        vars[var] = True

    count = [0]

    for block, vars in variables_by_block.items():

        def flowin(var, newvarsmap, insert_keepalive=False):
            # in this 'block', follow where the 'var' goes to and replace
            # it by a flattened-out family of variables.  This family is given
            # by newvarsmap, whose keys are the 'flatnames'.
            vars = {var: True}
            last_removed_access = None

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
                        last_removed_access = len(newops)
                    elif op.opname == "setfield":
                        S = op.args[0].concretetype.TO
                        fldname = op.args[1].value
                        assert (S, fldname) in newvarsmap
                        newvarsmap[S, fldname] = op.args[2]
                        last_removed_access = len(newops)
                    elif op.opname in ("same_as", "cast_pointer"):
                        assert op.result not in vars
                        vars[op.result] = True
                        # Consider the two pointers (input and result) as
                        # equivalent.  We can, and indeed must, use the same
                        # flattened list of variables for both, as a "setfield"
                        # via one pointer must be reflected in the other.
                    elif op.opname == 'keepalive':
                        last_removed_access = len(newops)
                    elif op.opname == "getsubstruct":
                        S = op.args[0].concretetype.TO
                        fldname = op.args[1].value
                        equiv = equivalent_substruct(S, fldname)
                        if equiv == "wrapper":
                            # reading the only Struct field of a GcStruct:
                            # do it with a getsubstruct on the wrapper ptr var
                            v = newvarsmap[S, fldname]
                            newop = SpaceOperation("getsubstruct",
                                                   [v, op.args[1]],
                                                   op.result)
                            newops.append(newop)
                        elif equiv:
                            # exactly like a cast_pointer
                            assert op.result not in vars
                            vars[op.result] = True
                        else:
                            # (S, fldname) in flatnames and in needsubmallocs
                            newop = SpaceOperation("same_as",
                                                   [newvarsmap[S, fldname]],
                                                   op.result)
                            newops.append(newop)
                            last_removed_access = len(newops)
                    else:
                        raise AssertionError, op.opname
                elif op.result in vars:
                    assert op.opname == "malloc"
                    assert vars == {var: True}
                    count[0] += 1
                    # drop the "malloc" operation
                    newvarsmap = flatconstants.copy()   # zero initial values
                    # if there are substructures, they are now individually
                    # malloc'ed in an exploded way.  (They will typically be
                    # removed again by the next malloc removal pass.)
                    for key in needsubmallocs:
                        v = Variable()
                        v.concretetype = newvarstype[key]
                        c = Constant(v.concretetype.TO, lltype.Void)
                        newop = SpaceOperation("malloc", [c], v)
                        newops.append(newop)
                        newvarsmap[key] = v
                else:
                    newops.append(op)

            assert block.exitswitch not in vars

            for link in block.exits:
                newargs = []
                for arg in link.args:
                    if arg in vars:
                        newargs += list_newvars()
                        insert_keepalive = False   # kept alive by the link
                    else:
                        newargs.append(arg)
                link.args[:] = newargs

            if insert_keepalive and last_removed_access is not None:
                keepalives = []
                for v in list_newvars():
                    T = v.concretetype
                    if isinstance(T, lltype.Ptr) and T._needsgc():
                        v0 = Variable()
                        v0.concretetype = lltype.Void
                        newop = SpaceOperation('keepalive', [v], v0)
                        keepalives.append(newop)
                newops[last_removed_access:last_removed_access] = keepalives

            block.operations[:] = newops

        # look for variables arriving from outside the block
        for var in vars:
            if var in block.inputargs:
                i = block.inputargs.index(var)
                newinputargs = block.inputargs[:i]
                newvarsmap = {}
                for key in flatnames:
                    newvar = Variable()
                    newvar.concretetype = newvarstype[key]
                    newvarsmap[key] = newvar
                    newinputargs.append(newvar)
                newinputargs += block.inputargs[i+1:]
                block.inputargs[:] = newinputargs
                assert var not in block.inputargs
                flowin(var, newvarsmap, insert_keepalive=True)

        # look for variables created inside the block by a malloc
        vars_created_here = []
        for op in block.operations:
            if op.opname == "malloc" and op.result in vars:
                vars_created_here.append(op.result)
        for var in vars_created_here:
            flowin(var, newvarsmap=None)

    assert count[0]
    return count[0]

def remove_mallocs_once(graph):
    """Perform one iteration of malloc removal."""
    remove_identical_vars(graph)
    lifetimes = compute_lifetimes(graph)
    progress = 0
    for info in lifetimes:
        progress += _try_inline_malloc(info)
    return progress

def remove_simple_mallocs(graph):
    """Iteratively remove (inline) the mallocs that can be simplified away."""
    tot = 0
    while True:
        count = remove_mallocs_once(graph)
        if count:
            log.malloc('%d simple mallocs removed in %r' % (count, graph.name))
            tot += count
        else:
            break
    return tot
