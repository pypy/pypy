from pypy.translator.simplify import get_funcobj
from pypy.jit.metainterp import support, history
from pypy.rpython.lltypesystem import lltype

class JitPolicy(object):

    def look_inside_function(self, func):
        if hasattr(func, '_look_inside_me_'):
            return func._look_inside_me_
        # explicitly pure functions are always opaque
        if getattr(func, '_pure_function_', False):
            return False
        # pypy.rpython.module.* are opaque helpers
        mod = func.__module__ or '?'
        if mod.startswith('pypy.rpython.module.'):
            return False
        return True

    def look_inside_graph(self, graph, supports_floats):
        try:
            func = graph.func
        except AttributeError:
            see_function = True
        else:
            see_function = self.look_inside_function(func)
        return (see_function and
                not contains_unsupported_variable_type(graph,
                                                       supports_floats))

    def graphs_from(self, op, supports_floats):
        if op.opname == 'direct_call':
            funcobj = get_funcobj(op.args[0].value)
            graph = funcobj.graph
            if self.look_inside_graph(graph, supports_floats):
                return [graph]     # common case: look inside this graph
        else:
            assert op.opname in ('indirect_call', 'oosend')
            if op.opname == 'indirect_call':
                graphs = op.args[-1].value
            else:
                v_obj = op.args[1].concretetype
                graphs = v_obj._lookup_graphs(op.args[0].value)
            if graphs is not None:
                for graph in graphs:
                    if self.look_inside_graph(graph, supports_floats):
                        return graphs  # common case: look inside at
                                       # least one of the graphs
        # residual call case: we don't need to look into any graph
        return None

    def guess_call_kind(self, op, supports_floats):
        if op.opname == 'direct_call':
            funcobj = get_funcobj(op.args[0].value)
            if isinstance(lltype.typeOf(funcobj), lltype.Ptr):
                try:
                    funcobj._obj
                except lltype.DelayedPointer:
                    return 'recursive'
            if (hasattr(funcobj, '_callable') and
                getattr(funcobj._callable, '_recursive_portal_call_', False)):
                return 'recursive'
            if getattr(funcobj, 'graph', None) is None:
                return 'residual'
            targetgraph = funcobj.graph
            if (hasattr(targetgraph, 'func') and
                hasattr(targetgraph.func, 'oopspec')):
                return 'builtin'
        elif op.opname == 'oosend':
            SELFTYPE, methname, opargs = support.decompose_oosend(op)
            if SELFTYPE.oopspec_name is not None:
                return 'builtin'
            # TODO: return 'recursive' if the oosend ends with calling the
            # portal
        if self.graphs_from(op, supports_floats) is None:
            return 'residual'
        return 'regular'

def contains_unsupported_variable_type(graph, supports_floats):
    getkind = history.getkind
    try:
        for block in graph.iterblocks():
            for v in block.inputargs:
                getkind(v.concretetype, supports_floats)
            for op in block.operations:
                for v in op.args:
                    getkind(v.concretetype, supports_floats)
                getkind(op.result.concretetype, supports_floats)
    except NotImplementedError, e:
        history.log.WARNING('%s, ignoring graph' % (e,))
        history.log.WARNING('  %s' % (graph,))
        return True
    return False

# ____________________________________________________________

class StopAtXPolicy(JitPolicy):
    def __init__(self, *funcs):
        self.funcs = funcs

    def look_inside_function(self, func):
        if func in self.funcs:
            return False
        return super(StopAtXPolicy, self).look_inside_function(func)
