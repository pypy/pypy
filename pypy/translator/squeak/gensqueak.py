import datetime, sys
from pypy.objspace.flow.model import traverse
from pypy.objspace.flow import FlowObjSpace
from pypy.objspace.flow.model import Constant, Variable, Block
from pypy.objspace.flow.model import last_exception, checkgraph
from pypy.translator.unsimplify import remove_direct_loops
from pypy.translator.simplify import simplify_graph
from pypy import conftest
try:
    set
except NameError:
    from sets import Set as set

def camel_case(identifier):
    identifier = identifier.replace(".", "_")
    words = identifier.split('_')
    return ''.join([words[0]] + [w.capitalize() for w in words[1:]])


class Selector:

    def __init__(self, function_name, arg_count):
        self.parts = [camel_case(function_name)]
        self.arg_count = arg_count
        self.infix = False
        if not self.parts[0].isalnum():
            # Binary infix selector, e.g. "+"
            assert arg_count == 1
            self.infix = True
        if arg_count > 1:
            self.parts += ["with"] * (arg_count - 1)

    def __str__(self):
        if self.arg_count == 0 or self.infix:
            return self.parts[0]
        else:
            return "%s:%s" % (self.parts[0],
                    "".join([p + ":" for p in self.parts[1:]]))

    def symbol(self):
        return str(self)

    def signature(self, arg_names):
        assert len(arg_names) == self.arg_count
        if self.arg_count == 0:
            return self.parts[0]
        elif self.infix:
            return "%s %s" % (self.parts[0], arg_names[0])
        else:
            return " ".join(["%s: %s" % (p, a)
                    for (p, a) in zip(self.parts, arg_names)])

selectormap = {
    #'setitem:with:': 'at:put:',
    #'getitem:':      'at:',
    'new':           Selector('new', 0),
    'runtimenew':    Selector('new', 0),
    'classof':       Selector('class', 0),
    'sameAs':        Selector('yourself', 0), 
    'intAdd:':       Selector('+', 1),
}


class LoopFinder:
    def __init__(self, startblock):
        self.loops = {}
        self.parents = {startblock: startblock}
        self.temps = {}
        self.seen = []
        self.visit_Block(startblock)
    def visit_Block(self, block, switches=[]):
        #self.temps.has_key()
        self.seen.append(block)
        if block.exitswitch:
            switches.append(block)
            self.parents[block] = block
        for link in block.exits:
            self.visit_Link(link, switches) 
    def visit_Link(self, link, switches):
        if link.target in switches:
            self.loops[link.target] = True
        if not link.target in self.seen:
            self.parents[link.target] = self.parents[link.prevblock]
            self.visit_Block(link.target, switches)

class GenSqueak:

    def __init__(self, sqdir, translator, modname=None):
        self.sqdir = sqdir
        self.translator = translator
        self.modname = (modname or
                        translator.graphs[0].name)
        self.sqnames = {
            Constant(None).key:  'nil',
            Constant(False).key: 'false',
            Constant(True).key:  'true',
        }
        self.seennames = set()
        self.name_mapping = {}
        self.pendinggraphs = []
        self.pendingclasses = []
        self.pendingmethods = []
        self.pendingsetters = [] # XXX ugly. should generalize methods/setters
        self.classes = [] 
        self.methods = [] 
        self.functions = []
        self.function_container = False

        t = self.translator
        graph = t.graphs[0]
        simplify_graph(graph)
        remove_direct_loops(t, graph)
        checkgraph(graph)

        if conftest.option.view:
            self.translator.view()

        self.pendinggraphs.append(graph)
        self.filename = '%s.st' % graph.name
        file = self.sqdir.join(self.filename).open('w')
        self.gen_source(file)
        file.close()


    def gen_source(self, file):
        while self.pendinggraphs or self.pendingclasses or self.pendingmethods \
            or self.pendingsetters:
            while self.pendinggraphs:
                graph = self.pendinggraphs.pop()
                self.gen_function(graph, file)
            while self.pendingclasses:
                INST = self.pendingclasses.pop(0)
                self.gen_class(INST, file)
            while self.pendingmethods:
                (INST, method_name) = self.pendingmethods.pop()
                self.gen_method(INST, method_name, file)
            while self.pendingsetters:
                (INST, field_name) = self.pendingsetters.pop()
                self.gen_setter(INST, field_name, file)

    def gen_fileout_header(self, class_name, category, f):
        print >> f, "!%s methodsFor: '%s' stamp: 'pypy %s'!" % (
                class_name, category,
                datetime.datetime.now().strftime("%m/%d/%Y %H:%M"))

    def gen_class(self, INSTANCE, f):
        self.classes.append(INSTANCE)
        print >> f, """%s subclass: #%s
        instanceVariableNames: '%s'
        classVariableNames: ''
        poolDictionaries: ''
        category: 'PyPy-Test'!
        """ % (
            self.nameof_Instance(INSTANCE._superclass), 
            self.nameof_Instance(INSTANCE),
            ' '.join(INSTANCE._fields.iterkeys()))

    def gen_method(self, INSTANCE, method_name, f):
        if (INSTANCE, method_name) in self.methods:
            return
        self.methods.append((INSTANCE, method_name))
        self.gen_fileout_header(self.nameof_Instance(INSTANCE), "methods", f)
        graph = INSTANCE._methods[method_name].graph
        self.gen_methodbody(camel_case(method_name), graph, f)

    def gen_setter(self, INSTANCE, field_name, f):
        if (INSTANCE, field_name) in self.methods:
            return
        self.methods.append((INSTANCE, field_name))
        self.gen_fileout_header(self.nameof_Instance(INSTANCE), "accessors", f)
        print >> f, "%s: value" % field_name
        print >> f, "  %s := value" % field_name
        print >> f, "! !"

    def gen_function(self, graph, f):
        if not self.function_container:
            self.gen_function_container(f)
            self.function_container = True
        func_name = self.nameof(graph.func)
        if func_name in self.functions:
            return
        self.functions.append(func_name)
        self.gen_fileout_header("PyFunctions class", "functions", f)
        self.gen_methodbody(func_name, graph, f)

    def gen_methodbody(self, method_name, graph, f):
        renderer = MethodBodyRenderer(self, method_name, graph)
        for line in renderer.render():
            print >> f, line
        print >> f, '! !'
        print >> f

    def gen_function_container(self, f):
        print >> f, """Object subclass: #PyFunctions
            instanceVariableNames: ''
            classVariableNames: ''
            poolDictionaries: ''
            category: 'PyPy'!"""
        
    def nameof(self, obj):
        key = Constant(obj).key
        try:
            return self.sqnames[key]
        except KeyError:
            for cls in type(obj).__mro__:
                meth = getattr(self,
                               'nameof_' + cls.__name__.replace(' ', ''),
                               None)
                if meth:
                    break
            else:
                types = ['nameof_'+t.__name__ for t in type(obj).__mro__]
                raise Exception, "nameof(%r): no method %s" % (obj, types)
            name = meth(obj)
            self.sqnames[key] = name
            return name

    def nameof_int(self, i):
        return str(i)

    def nameof_str(self, s):
        return "'s'"

    def nameof_Instance(self, INSTANCE):
        if INSTANCE is None:
            return "Object"
        self.note_Instance(INSTANCE)
        class_name = INSTANCE._name.split(".")[-1]
        squeak_class_name = self.unique_name(INSTANCE, class_name)
        return "Py%s" % squeak_class_name

    def nameof__instance(self, inst):
        return self.nameof_Instance(inst._TYPE)

    def nameof__callable(self, callable):
        return self.nameof_function(callable.graph.func)

    def nameof_function(self, function):
        squeak_func_name = self.unique_name(function, function.__name__)
        return squeak_func_name
        
    def note_Instance(self, inst):
        if inst not in self.classes:
            if inst not in self.pendingclasses:
                if inst._superclass is not None: # not root
                    # Need to make sure that superclasses appear first in
                    # the generated source.
                    self.note_Instance(inst._superclass)
                self.pendingclasses.append(inst)

    def note_meth(self, inst, meth):
        bm = (inst, meth)
        if bm not in self.methods:
            if bm not in self.pendingmethods:
                self.pendingmethods.append(bm)

    def note_function(self, function):
        # 'function' is actually a _static_meth (always?)
        graph = function.graph
        if graph not in self.pendinggraphs:
            self.pendinggraphs.append(graph)

    def unique_name(self, key, basename):
        if self.name_mapping.has_key(key):
            unique = self.name_mapping[key]
        else:
            camel_basename = camel_case(basename)
            unique = camel_basename
            ext = 0
            while unique in self.seennames:
               unique = camel_basename + str(ext)
               ext += 1 
            self.name_mapping[key] = unique
            self.seennames.add(unique)
        return unique

    def skipped_function(self, func):
        # debugging only!  Generates a placeholder for missing functions
        # that raises an exception when called.
        name = self.unique_name(camel_case('skipped_' + func.__name__))
        return name


class MethodBodyRenderer:

    def __init__(self, gen, method_name, graph):
        self.gen = gen
        self.name = method_name
        self.start = graph.startblock
        self.loops = LoopFinder(self.start).loops

    def render(self):
        args = self.start.inputargs
        sel = Selector(self.name, len(args))
        yield sel.signature([self.expr(v) for v in args])
 
        # XXX should declare local variables here
        for line in self.render_block(self.start):
            yield "    %s" % line

    def expr(self, v):
        if isinstance(v, Variable):
            return camel_case(v.name)
        elif isinstance(v, Constant):
            return self.gen.nameof(v.value)
        else:
            raise TypeError, "expr(%r)" % (v,)

    def oper(self, op):
        args = [self.expr(arg) for arg in op.args]
        if op.opname == "oosend":
            name = op.args[0].value
            receiver = args[1]
            # For now, send nil as the explicit self. XXX will probably have
            # to do something more intelligent.
            args = ["nil"] + args[2:]
            self.gen.note_meth(op.args[1].concretetype, name)
        elif op.opname == "oogetfield":
            receiver = args[0]
            name = op.args[1].value
            args = args[2:]
        elif op.opname == "oosetfield":
            receiver = args[0]
            name = op.args[1].value
            args = args[2:]
            # XXX should only generate setter if field is set from outside
            self.gen.pendingsetters.append((op.args[0].concretetype, name))
        elif op.opname == "direct_call":
            # XXX not sure if static methods of a specific class should
            # be treated differently.
            receiver = "PyFunctions"
            name = args[0]
            args = args[1:]
            self.gen.note_function(op.args[0].value)
        else:
            name = op.opname
            receiver = args[0]
            args = args[1:]
        sel = Selector(name, len(args))
        if op.opname != "oosend":
            sel = selectormap.get(sel.symbol(), sel)
        return "%s := %s %s." \
                % (self.expr(op.result), receiver, sel.signature(args))

    def render_return(self, args):
        if len(args) == 2:
            # exception
            exc_cls = self.expr(args[0])
            exc_val = self.expr(args[1])
            yield "(PyOperationError class: %s value: %s) signal." % (exc_cls, exc_val)
        else:
            # regular return block
            retval = self.expr(args[0])
            yield "^%s" % retval

    def render_link(self, link):
        block = link.target
        if link.args:
            for i in range(len(link.args)):
                yield '%s := %s.' % \
                        (self.expr(block.inputargs[i]), self.expr(link.args[i]))
        for line in self.render_block(block):
            yield line

    def render_block(self, block):
        if self.loops.has_key(block):
            if not self.loops[block]:
                yield '"skip1"'
                return
            yield "["
        for op in block.operations:
            yield "%s" % self.oper(op)
        if len(block.exits) == 0:
            for line in self.render_return(block.inputargs):
                yield line
            return
        elif block.exitswitch is None:
            # single-exit block
            assert len(block.exits) == 1
            for line in self.render_link(block.exits[0]):
                yield line
        else:
            #exitswitch
            if self.loops.has_key(block):
                if self.loops[block]:
                    self.loops[block] = False
                    yield "%s] whileTrue: [" % self.expr(block.exitswitch)
                    for line in self.render_link(block.exits[True]):
                        yield "    %s" % line
                    yield "]."
                    for line in self.render_link(block.exits[False]):
                        yield "%s" % line
            else:
                yield "%s ifTrue: [" % self.expr(block.exitswitch)
                for line in self.render_link(block.exits[True]):
                    yield "    %s" % line
                yield "] ifFalse: [" 
                for line in self.render_link(block.exits[False]):
                    yield "    %s" % line
                yield "]"


