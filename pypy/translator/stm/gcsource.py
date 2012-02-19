from pypy.objspace.flow.model import Variable
from pypy.rpython.lltypesystem import lltype, rclass
from pypy.translator.simplify import get_graph


COPIES_POINTER = set([
    'force_cast', 'cast_pointer', 'same_as', 'cast_opaque_ptr',
    ])


def _is_gc(var_or_const):
    TYPE = var_or_const.concretetype
    return isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc'

def enum_gc_dependencies(translator):
    """Enumerate pairs (var-or-const-or-op, var) that together describe
    the whole control flow of GC pointers in the program.  If the source
    is a SpaceOperation, it means 'produced by this operation but we can't
    follow what this operation does'.  The source is a string to describe
    special cases.
    """
    # Tracking dependencies of only GC pointers simplifies the logic here.
    # We don't have to worry about external calls and callbacks.
    # This works by assuming that each graph's calls are fully tracked
    # by the last argument to 'indirect_call'.  Graphs for which we don't
    # find any call like this are assumed to be called 'from the outside'
    # passing any random arguments to it.
    resultlist = []
    was_a_callee = set()
    #
    def call(graph, args, result):
        inputargs = graph.getargs()
        assert len(args) == len(inputargs)
        for v1, v2 in zip(args, inputargs):
            if _is_gc(v2):
                assert _is_gc(v1)
                resultlist.append((v1, v2))
        if _is_gc(result):
            v = graph.getreturnvar()
            assert _is_gc(v)
            resultlist.append((v, result))
        was_a_callee.add(graph)
    #
    for graph in translator.graphs:
        for block in graph.iterblocks():
            for op in block.operations:
                #
                if op.opname in COPIES_POINTER:
                    if _is_gc(op.result) and _is_gc(op.args[0]):
                        resultlist.append((op.args[0], op.result))
                        continue
                #
                if op.opname == 'direct_call':
                    tograph = get_graph(op.args[0], translator)
                    if tograph is not None:
                        call(tograph, op.args[1:], op.result)
                        continue
                #
                if op.opname == 'indirect_call':
                    tographs = op.args[-1].value
                    if tographs is not None:
                        for tograph in tographs:
                            call(tograph, op.args[1:-1], op.result)
                        continue
                    # special-case to detect 'instantiate'
                    is_instantiate = False
                    v_func = op.args[0]
                    for op1 in block.operations:
                        if (v_func is op1.result and
                            op1.opname == 'getfield' and
                            op1.args[0].concretetype == rclass.CLASSTYPE and
                            op1.args[1].value == 'instantiate'):
                            is_instantiate = True
                            break
                    if is_instantiate:
                        resultlist.append(('instantiate', op.result))
                        continue
                #
                if _is_gc(op.result):
                    resultlist.append((op, op.result))
            #
            for link in block.exits:
                for v1, v2 in zip(link.args, link.target.inputargs):
                    if _is_gc(v2):
                        assert _is_gc(v1)
                        if v1 is link.last_exc_value:
                            v1 = 'last_exc_value'
                        resultlist.append((v1, v2))
    #
    # also add as a callee the graphs that are explicitly callees in the
    # callgraph.  Useful because some graphs may end up not being called
    # any more, if they were inlined.
    was_originally_a_callee = set()
    for _, graph in translator.callgraph.itervalues():
        was_originally_a_callee.add(graph)
    #
    for graph in translator.graphs:
        if graph not in was_a_callee:
            if graph in was_originally_a_callee:
                src = 'originally_a_callee'
            else:
                src = 'unknown'
            for v in graph.getargs():
                if _is_gc(v):
                    resultlist.append((src, v))
    return resultlist


class GcSource(object):
    """Works like a dict {gcptr-var: set-of-sources}.  A source is a
    Constant, or a SpaceOperation that creates the value, or a string
    which describes a special case."""

    def __init__(self, translator):
        self.translator = translator
        self._backmapping = {}
        for v1, v2 in enum_gc_dependencies(translator):
            self._backmapping.setdefault(v2, []).append(v1)

    def __getitem__(self, variable):
        result = set()
        pending = [variable]
        seen = set(pending)
        for v2 in pending:
            # we get a KeyError here if 'variable' is not found,
            # or if one of the preceeding variables is not found
            for v1 in self._backmapping[v2]:
                if isinstance(v1, Variable):
                    if v1 not in seen:
                        seen.add(v1)
                        pending.append(v1)
                else:
                    result.add(v1)
        return result
