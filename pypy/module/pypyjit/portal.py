from pypy.module.pypyjit.interp_jit import PORTAL
from pypy.module.pypyjit.newbool import NewBoolDesc
from pypy.translator.translator import graphof
from pypy.annotation.specialize import getuniquenondirectgraph
from pypy.jit.hintannotator.annotator import HintAnnotatorPolicy

class PyPyHintAnnotatorPolicy(HintAnnotatorPolicy):
    novirtualcontainer = True
    oopspec = True

    def __init__(self, timeshift_graphs):
        self.timeshift_graphs = timeshift_graphs

    def look_inside_graph(self, graph):
        if graph in self.timeshift_graphs:
            return self.timeshift_graphs[graph]
        try:
            func = graph.func
        except AttributeError:
            return True
        mod = func.__module__ or '?'
        if mod.startswith('pypy.objspace'):
            return False
        if '_geninterp_' in func.func_globals: # skip all geninterped stuff
            return False
        if mod.startswith('pypy.interpreter.astcompiler'):
            return False
        if mod.startswith('pypy.interpreter.pyparser'):
            return False
        if mod.startswith('pypy.module.'):
            if not mod.startswith('pypy.module.pypyjit.'):
                return False
        if mod in forbidden_modules:
            return False
        if func.__name__.startswith('_mm_') or '_mth_mm_' in func.__name__:
            return False
        if func.__name__.startswith('fastfunc_'):
            return False
        return True

forbidden_modules = {'pypy.interpreter.gateway': True,
                     #'pypy.interpreter.baseobjspace': True,
                     'pypy.interpreter.typedef': True,
                     'pypy.interpreter.eval': True,
                     'pypy.interpreter.function': True,
                     'pypy.interpreter.pytraceback': True,
                     }

def enumerate_reachable_graphs(translator, startgraph):
    from pypy.translator.backendopt.support import find_calls_from
    pending = [(startgraph, None)]
    yield pending[0]
    seen = {startgraph: True}
    while pending:
        yield None     # hack: a separator meaning "length increases now"
        nextlengthlist = []
        nextseen = {}
        for node in pending:
            head, tail = node
            for block, callee in find_calls_from(translator, head):
                if callee not in seen:
                    newnode = callee, node
                    yield newnode
                    nextlengthlist.append(newnode)
                    nextseen[callee] = True
        pending = nextlengthlist
        seen.update(nextseen)
    yield None

def graphs_on_the_path_to(translator, startgraph, targetgraphs):
    targetgraphs = targetgraphs.copy()
    result = {}
    found = {}
    for node in enumerate_reachable_graphs(translator, startgraph):
        if node is None:  # hack: a separator meaning "length increases now"
            for graph in found:
                del targetgraphs[graph]
            found.clear()
            if not targetgraphs:
                return result
        elif node[0] in targetgraphs:
            found[node[0]] = True
            while node is not None:
                head, tail = node
                result[head] = True
                node = tail
    raise Exception("did not reach all targets:\nmissing %r" % (
        targetgraphs.keys(),))


def timeshift_graphs(t, portal_graph, log):
    import pypy
    result_graphs = {}

    bk = t.annotator.bookkeeper

    def _graph(func):
        func = getattr(func, 'im_func', func)
        desc = bk.getdesc(func)
        return getuniquenondirectgraph(desc)

    def seefunc(fromfunc, *tofuncs):
        targetgraphs = {}
        for tofunc in tofuncs:
            targetgraphs[_graph(tofunc)] = True
        graphs = graphs_on_the_path_to(t, _graph(fromfunc), targetgraphs)
        for graph in graphs:
            if graph not in result_graphs:
                log('including graph %s' % (graph,))
            result_graphs[graph] = True

    def seepath(*path):
        for i in range(1, len(path)):
            seefunc(path[i-1], path[i])

    def seegraph(func, look=True):
        graph = _graph(func)
        if look:
            extra = ""
            if look != True:
                extra = " substituted with %s" % look
            log('including graph %s%s' % (graph, extra))
        else:
            log('excluding graph %s' % (graph,))
        result_graphs[graph] = look

    def seebinary(opname):
        name2 = name1 = opname[:3].lower()
        if name1 in ('and', 'or'):
            name1 += '_'
        descr_impl = getattr(pypy.objspace.descroperation.DescrOperation, name1)
        obj_impl = getattr(pypy.objspace.std.intobject, name2 + '__Int_Int')
        seepath(getattr(pypy.interpreter.pyframe.PyFrame, 'BINARY_'+ opname),
                descr_impl,
                obj_impl)
        seepath(descr_impl,
                pypy.objspace.std.typeobject.W_TypeObject.is_heaptype)
        descr_impl = getattr(pypy.objspace.descroperation.DescrOperation,
                             'inplace_' + name2)
        seepath(getattr(pypy.interpreter.pyframe.PyFrame, 'INPLACE_'+ opname),
                descr_impl,
                obj_impl)
        seepath(descr_impl,
                pypy.objspace.std.typeobject.W_TypeObject.is_heaptype)
        
    def seeunary(opname, name=None):
        if name is None:
            name = opname.lower()
        descr_impl = getattr(pypy.objspace.descroperation.DescrOperation, name)
        seepath(getattr(pypy.interpreter.pyframe.PyFrame, 'UNARY_' + opname),
                descr_impl,
                getattr(pypy.objspace.std.intobject, name + '__Int'))
        seepath(descr_impl,
                pypy.objspace.std.typeobject.W_TypeObject.is_heaptype)

    def seecmp(name):
        descr_impl = getattr(pypy.objspace.descroperation.DescrOperation, name)
        seepath(pypy.interpreter.pyframe.PyFrame.COMPARE_OP,
                descr_impl,
                getattr(pypy.objspace.std.intobject, name +'__Int_Int'),
                pypy.objspace.std.Space.newbool)
        seepath(descr_impl,
                pypy.objspace.std.typeobject.W_TypeObject.is_heaptype)

    # --------------------
    for binop in 'ADD SUBTRACT MULTIPLY AND OR XOR'.split():
        seebinary(binop)
    for cmpname in 'lt le eq ne ge gt'.split():
        seecmp(cmpname)
    seepath(pypy.interpreter.pyframe.PyFrame.UNARY_NOT,
            pypy.objspace.std.Space.not_)
    seeunary('INVERT')
    seeunary('POSITIVE', 'pos')
    seeunary('NEGATIVE', 'neg')

    seepath(pypy.objspace.descroperation._invoke_binop,
            pypy.objspace.descroperation._check_notimplemented)
    seepath(pypy.objspace.std.intobject.add__Int_Int,
            pypy.objspace.std.inttype.wrapint,
            pypy.objspace.std.intobject.W_IntObject.__init__)
    seepath(pypy.objspace.descroperation.DescrOperation.add,
            pypy.objspace.std.Space.type,
            pypy.objspace.std.Space.gettypeobject)
    seepath(pypy.objspace.descroperation.DescrOperation.add,
            pypy.objspace.std.Space.is_w)
    seegraph(pypy.interpreter.pyframe.PyFrame.execute_frame, False)
    # --------------------
    # special timeshifting logic for newbool
    seegraph(pypy.objspace.std.Space.newbool, NewBoolDesc)
    seepath(pypy.interpreter.pyframe.PyFrame.JUMP_IF_TRUE,
            pypy.objspace.std.Space.is_true)
    seepath(pypy.interpreter.pyframe.PyFrame.JUMP_IF_FALSE,
            pypy.objspace.std.Space.is_true)

    #
    seepath(pypy.interpreter.pyframe.PyFrame.CALL_FUNCTION,
            pypy.interpreter.function.Function.funccall_valuestack)
    seepath(pypy.interpreter.pyframe.PyFrame.CALL_FUNCTION,
            pypy.interpreter.function.Function.funccall_obj_valuestack)

    return result_graphs


def get_portal(drv):
    t = drv.translator
    portal = getattr(PORTAL, 'im_func', PORTAL)
    portal_graph = graphof(t, portal)

    policy = PyPyHintAnnotatorPolicy(timeshift_graphs(t, portal_graph,
                                                      drv.log))
    return portal, policy
