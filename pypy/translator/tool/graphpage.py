import inspect
from pypy.objspace.flow.model import traverse
from pypy.translator.tool.make_dot import DotGen, make_dot, make_dot_graphs
from pypy.interpreter.pycode import CO_VARARGS, CO_VARKEYWORDS
from pypy.annotation import model
from pypy.annotation.classdef import ClassDef
from pypy.tool.uid import uid


class GraphPage:
    """Base class for the server-side content of one of the 'pages'
    (one graph) sent over to and displayed by the client.
    """
    def __init__(self, *args):
        self.args = args

    def content(self):
        """Compute the content of the page.
        This doesn't modify the page in place; it returns a new GraphPage.
        """
        if hasattr(self, 'source'):
            return self
        else:
            new = self.__class__()
            new.source = ''  # '''dot source'''
            new.links  = {}  # {'word': 'statusbar text'}
            new.compute(*self.args)   # defined in subclasses
            return new

    def followlink(self, word):
        raise KeyError

    def display(self):
        "Display a graph page locally."
        from pypy.translator.tool.pygame.graphclient import get_layout
        get_layout(self).display()


class SingleGraphPage(GraphPage):
    """ A GraphPage showing a single precomputed FlowGraph."""

    def compute(self, graph):
        self.source = make_dot(graph.name, graph, target=None)


class VariableHistoryGraphPage(GraphPage):
    """ A GraphPage showing the history of variable bindings. """

    def compute(self, translator, name, info, caused_by, history, func_names):
        self.linkinfo = {}
        self.translator = translator
        self.func_names = func_names
        dotgen = DotGen('binding')
        label = "Most recent binding of %s\\n\\n%s" % (name, nottoowide(info))
        if info.origin is not None:
            label += "\\n" + self.createlink(info.origin, 'Originated at')
        if caused_by is not None:
            label += '\\n' + self.createlink(caused_by)
        if info.caused_by_merge is not None:
            data = 'unionof%r' % (info.caused_by_merge,)
            label += '\\n%s' % nottoowide(data)
        
        dotgen.emit_node('0', shape="box", color="red", label=label)
        for n, (data, caused_by) in zip(range(len(history)), history):
            label = nottoowide(data)
            if data.origin is not None:
                label += "\\n" + self.createlink(data.origin, 'Originated at')
            if caused_by is not None:
                label += '\\n' + self.createlink(caused_by)
            dotgen.emit_node(str(n+1), shape="box", label=label)
            dotgen.emit_edge(str(n+1), str(n))
        self.source = dotgen.generate(target=None)

    def createlink(self, position_key, wording='Caused by a call from'):
        fn, block, pos = position_key
        basename = self.func_names.get(fn, fn.func_name)
        linkname = basename
        n = 1
        while self.linkinfo.get(linkname, position_key) != position_key:
            n += 1
            linkname = '%s_%d' % (basename, n)
        self.linkinfo[linkname] = position_key
        # It would be nice to get the block name somehow
        blockname = block.__class__.__name__
        self.links[linkname] = '%s, %s, position %r:\n%s' % (basename,
                                        blockname, pos, block.operations[pos])
        return '%s %s' % (wording, linkname)

    def followlink(self, funcname):
        fn, block, pos = self.linkinfo[funcname]
        # It would be nice to focus on the block
        return FlowGraphPage(self.translator, [fn], self.func_names)


class FlowGraphPage(GraphPage):
    """ A GraphPage showing a Flow Graph (or a few flow graphs).
    """
    def compute(self, translator, functions=None, func_names=None):
        self.translator = translator
        self.annotator = translator.annotator
        self.func_names = func_names or {}
        functions = functions or translator.functions
        graphs = [translator.getflowgraph(func) for func in functions]
        gs = [(graph.name, graph) for graph in graphs]
        if self.annotator and self.annotator.blocked_functions:
            for block, was_annotated in self.annotator.annotated.items():
                if not was_annotated:
                    block.fillcolor = "red"
        self.source = make_dot_graphs(graphs[0].name+"_graph", gs, target=None)
        # make the dictionary of links -- one per annotated variable
        self.binding_history = {}
        self.current_value = {}
        self.caused_by = {}
        if self.annotator:
            for var in self.annotator.bindings:
                s_value = self.annotator.binding(var)
                info = '%s: %s' % (var.name, s_value)
                self.links[var.name] = info
                self.current_value[var.name] = s_value
                self.caused_by[var.name] = (
                    self.annotator.binding_caused_by.get(var))
            for var, history in self.annotator.bindingshistory.items():
                cause_history = (
                    self.annotator.binding_cause_history.get(var, []))
                self.binding_history[var.name] = zip(history, cause_history)

    def followlink(self, varname):
        # clicking on a variable name shows its binding history
        cur_value = self.current_value[varname]
        caused_by = self.caused_by[varname]
        history = list(self.binding_history.get(varname, []))
        history.reverse()
        return VariableHistoryGraphPage(self.translator, varname, cur_value,
                                          caused_by, history, self.func_names)


def nottoowide(text, width=72):
    parts = str(text).split(' ')
    lines = []
    line = parts.pop(0)
    for s in parts:
        if len(line)+len(s) < width:
            line = line + ' ' + s
        else:
            lines.append(line)
            line = s
    lines.append(line)
    return '\\n'.join(lines)


class ClassDefPage(GraphPage):
    """A GraphPage showing the attributes of a class.
    """
    def compute(self, translator, cdef):
        self.translator = translator
        dotgen = DotGen(cdef.cls.__name__, rankdir="LR")

        def writecdef(cdef):
            dotgen.emit_node(nameof(cdef), color="red", shape="octagon",
                             label=repr(cdef.cls))
            attrs = cdef.attrs.items()
            attrs.sort()
            for name, attrdef in attrs:
                s_value = attrdef.s_value
                dotgen.emit_node(name, shape="box", label=nottoowide(s_value))
                dotgen.emit_edge(nameof(cdef), name, label=name)

        prevcdef = None
        while cdef is not None:
            writecdef(cdef)
            if prevcdef:
                dotgen.emit_edge(nameof(cdef), nameof(prevcdef), color="red")
            prevcdef = cdef
            cdef = cdef.basedef
        
        self.source = dotgen.generate(target=None)


class TranslatorPage(GraphPage):
    """A GraphPage showing a the call graph between functions
    as well as the class hierarchy."""

    def compute(self, translator):
        self.translator = translator
        self.object_by_name = {}
        self.name_by_object = {}
        dotgen = DotGen('translator')
        dotgen.emit('mclimit=15.0')

        # show the call graph
        functions = translator.functions
        blocked_functions = {}
        if translator.annotator:
            # don't use translator.annotator.blocked_functions here because
            # it is not populated until the annotator finishes.
            annotated = translator.annotator.annotated
            for fn, graph in translator.flowgraphs.items():
                def visit(node):
                    if annotated.get(node) is False:
                        blocked_functions[fn] = True
                traverse(visit, graph)
        highlight_functions = getattr(translator, 'highlight_functions', {}) # XXX
        dotgen.emit_node('entry', fillcolor="green", shape="octagon",
                         label="Translator\\nEntry Point")
        for func in functions:
            name = func.func_name
            class_ = getattr(func, 'class_', None)
            if class_ is not None:
                name = '%s.%s' % (class_.__name__, name)
            data = self.labelof(func, name)
            if func in blocked_functions:
                kw = {'fillcolor': 'red'}
            elif func in highlight_functions:
                kw = {'fillcolor': '#ffcccc'}
            else:
                kw = {}
            dotgen.emit_node(nameof(func), label=data, shape="box", **kw)
        dotgen.emit_edge('entry', nameof(functions[0]), color="green")
        for f1, f2 in translator.callgraph.itervalues():
            dotgen.emit_edge(nameof(f1), nameof(f2))

        # show the class hierarchy
        if self.translator.annotator:
            dotgen.emit_node(nameof(None), color="red", shape="octagon",
                             label="Root Class\\nobject")
            for classdef in self.translator.annotator.getuserclassdefinitions():
                data = self.labelof(classdef, classdef.cls.__name__)
                dotgen.emit_node(nameof(classdef), label=data, shape="box")
                dotgen.emit_edge(nameof(classdef.basedef), nameof(classdef))
        
        self.source = dotgen.generate(target=None)

        # link the function names to the individual flow graphs
        for name, obj in self.object_by_name.iteritems():
            if isinstance(obj, ClassDef):
                #data = '%s.%s' % (obj.cls.__module__, obj.cls.__name__)
                data = repr(obj.cls)
            else:
                func = obj
                try:
                    source = inspect.getsource(func)
                except IOError:   # e.g. when func is defined interactively
                    source = func.func_name
                data = '%s:%d\n%s' % (func.func_globals.get('__name__', '?'),
                                      func.func_code.co_firstlineno,
                                      source.split('\n')[0])
            self.links[name] = data

    def labelof(self, obj, objname):
        name = objname
        i = 1
        while name in self.object_by_name:
            i += 1
            name = '%s__%d' % (objname, i)
        self.object_by_name[name] = obj
        self.name_by_object[obj] = name
        return name

    def followlink(self, name):
        obj = self.object_by_name[name]
        if isinstance(obj, ClassDef):
            return ClassDefPage(self.translator, obj)
        else:
            return FlowGraphPage(self.translator, [obj], self.name_by_object)


def nameof(obj, cache={}):
    # NB. the purpose of the cache is not performance, but to ensure that
    # two objects that compare equal get the same name
    try:
        return cache[obj]
    except KeyError:
        result = '%s__0x%x' % (getattr(obj, '__name__', ''), uid(obj))
        cache[obj] = result
        return result
