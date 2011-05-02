from pypy.translator.simplify import get_funcobj
from pypy.jit.metainterp import history, quasiimmut
from pypy.rpython.lltypesystem import lltype, rclass
from pypy.tool.udir import udir

import py, sys
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('jitcodewriter')
py.log.setconsumer('jitcodewriter', ansi_log)


class JitPolicy(object):
    def __init__(self):
        self.unsafe_loopy_graphs = set()
        self.supports_floats = False
        self.supports_longlong = False

    def set_supports_floats(self, flag):
        self.supports_floats = flag

    def set_supports_longlong(self, flag):
        self.supports_longlong = flag

    def dump_unsafe_loops(self):
        f = udir.join("unsafe-loops.txt").open('w')
        strs = [str(graph) for graph in self.unsafe_loopy_graphs]
        strs.sort()
        for graph in strs:
            print >> f, graph
        f.close()

    def look_inside_function(self, func):
        return True # look into everything by default

    def _reject_function(self, func):
        if hasattr(func, '_jit_look_inside_'):
            return not func._jit_look_inside_
        # explicitly pure functions are always opaque
        if getattr(func, '_pure_function_', False):
            return True
        # pypy.rpython.module.* are opaque helpers
        mod = func.__module__ or '?'
        if mod.startswith('pypy.rpython.module.'):
            return True
        if mod.startswith('pypy.translator.'): # XXX wtf?
            return True
        # string builder interface
        if mod == 'pypy.rpython.lltypesystem.rbuilder':
            return True
        
        return False

    def look_inside_graph(self, graph):
        from pypy.translator.backendopt.support import find_backedges
        contains_loop = bool(find_backedges(graph))
        try:
            func = graph.func
        except AttributeError:
            see_function = True
        else:
            see_function = (self.look_inside_function(func) and not
                            self._reject_function(func))
            contains_loop = contains_loop and not getattr(
                    func, '_jit_unroll_safe_', False)

        res = see_function and not contains_unsupported_variable_type(graph,
                                                        self.supports_floats,
                                                        self.supports_longlong)
        if res and contains_loop:
            self.unsafe_loopy_graphs.add(graph)
        return res and not contains_loop

def contains_unsupported_variable_type(graph, supports_floats,
                                       supports_longlong):
    getkind = history.getkind
    try:
        for block in graph.iterblocks():
            for v in block.inputargs:
                getkind(v.concretetype, supports_floats, supports_longlong)
            for op in block.operations:
                for v in op.args:
                    getkind(v.concretetype, supports_floats, supports_longlong)
                v = op.result
                getkind(v.concretetype, supports_floats, supports_longlong)
                check_skip_operation(op)
    except NotImplementedError, e:
        log.WARNING('%s, ignoring graph' % (e,))
        log.WARNING('  %s' % (graph,))
        return True
    return False

def check_skip_operation(op):
    if op.opname == 'setfield':
        if quasiimmut.is_quasi_immutable(op.args[0].concretetype.TO,
                                         op.args[1].value):
            raise NotImplementedError("write to quasi-immutable field %r"
                                      % (op.args[1].value,))

# ____________________________________________________________

class StopAtXPolicy(JitPolicy):
    def __init__(self, *funcs):
        JitPolicy.__init__(self)
        self.funcs = funcs

    def look_inside_function(self, func):
        return func not in self.funcs
