import autopath
import inspect
from drawgraph import GraphLayout
from pypy.translator.tool.make_dot import DotGen
from pypy.interpreter.pycode import CO_VARARGS, CO_VARKEYWORDS
from pypy.annotation import model, factory


class FlowGraphLayout(GraphLayout):
    """ A GraphLayout showing a Flow Graph (or a few flow graphs).
    """
    def __init__(self, translator, functions=None):
        from pypy.translator.tool.make_dot import make_dot_graphs
        self.translator = translator
        self.annotator = translator.annotator
        functions = functions or translator.functions
        graphs = [translator.getflowgraph(func) for func in functions]
        gs = [(graph.name, graph) for graph in graphs]
        fn = make_dot_graphs(graphs[0].name, gs, target='plain')
        GraphLayout.__init__(self, fn)
        # make the dictionary of links -- one per annotated variable
        self.binding_history = {}
        if self.annotator:
            for var in self.annotator.bindings:
                s_value = self.annotator.binding(var)
                info = '%s: %s' % (var.name, s_value)
                self.links[var.name] = info
            for var, history in self.annotator.bindingshistory.items():
                self.binding_history[var.name] = history

    def followlink(self, varname):
        # clicking on a variable name shows its binding history
        dotgen = DotGen('binding')
        data = "Most recent binding\\n\\n%s" % nottoowide(self.links[varname])
        dotgen.emit_node('0', shape="box", color="red", label=data)
        history = list(self.binding_history.get(varname, []))
        history.reverse()
        for n, data in zip(range(len(history)), history):
            dotgen.emit_node(str(n+1), shape="box", label=nottoowide(data))
            dotgen.emit_edge(str(n+1), str(n))
        return GraphLayout(dotgen.generate(target='plain'))


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


class ClassDefLayout(GraphLayout):
    """A GraphLayout showing the attributes of a class.
    """
    def __init__(self, translator, cdef):
        self.translator = translator
        dotgen = DotGen(cdef.cls.__name__)

        def writecdef(cdef):
            dotgen.emit_node(nameof(cdef), color="red", shape="octagon",
                             label=repr(cdef.cls))
            attrs = cdef.attrs.items()
            attrs.sort()
            for name, s_value in attrs:
                dotgen.emit_node(name, shape="box", label=nottoowide(s_value))
                dotgen.emit_edge(nameof(cdef), name, label=name)

        prevcdef = None
        while cdef is not None:
            writecdef(cdef)
            if prevcdef:
                dotgen.emit_edge(nameof(cdef), nameof(prevcdef), color="red")
            prevcdef = cdef
            cdef = cdef.basedef
        
        GraphLayout.__init__(self, dotgen.generate(target='plain'))


class TranslatorLayout(GraphLayout):
    """A GraphLayout showing a the call graph between functions
    as well as the class hierarchy."""

    def __init__(self, translator):
        self.translator = translator
        self.object_by_name = {}
        dotgen = DotGen('translator')
        
        # show the call graph
        functions = translator.functions
        dotgen.emit_node('entry', fillcolor="green", shape="octagon",
                         label="Translator\\nEntry Point")
        for func in functions:
            data = self.labelof(func, func.func_name)
            dotgen.emit_node(nameof(func), label=data, shape="box")
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
        
        GraphLayout.__init__(self, dotgen.generate(target='plain'))

        # link the function names to the individual flow graphs
        for name, obj in self.object_by_name.iteritems():
            if isinstance(obj, factory.ClassDef):
                #data = '%s.%s' % (obj.cls.__module__, obj.cls.__name__)
                data = repr(obj.cls)
            else:
                func = obj
                try:
                    source = inspect.getsource(func)
                except IOError:   # e.g. when func is defined interactively
                    source = func.func_name
                data = '%s:%d  %s' % (func.func_globals.get('__name__', '?'),
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
        return name

    def followlink(self, name):
        obj = self.object_by_name[name]
        if isinstance(obj, factory.ClassDef):
            return ClassDefLayout(self.translator, obj)
        else:
            return FlowGraphLayout(self.translator, [obj])


def nameof(obj, cache={}):
    # NB. the purpose of the cache is not performance, but to ensure that
    # two objects that compare equal get the same name
    try:
        return cache[obj]
    except KeyError:
        result = '%s__0x%x' % (getattr(obj, '__name__', ''), id(obj))
        cache[obj] = result
        return result

# ____________________________________________________________

if __name__ == '__main__':
    from pypy.translator.translator import Translator
    from pypy.translator.test import snippet
    from graphdisplay import GraphDisplay
    
    t = Translator(snippet.powerset)
    #t.simplify()
    a = t.annotate([int])
    a.simplify()
    GraphDisplay(FlowGraphLayout(t)).run()

##    t = Translator(snippet._methodcall1)
##    t.simplify()
##    a = t.annotate([int])
##    a.simplify()
##    GraphDisplay(TranslatorLayout(t)).run()
