import datetime, sys
from pypy.objspace.flow.model import traverse
from pypy.objspace.flow import FlowObjSpace
from pypy.objspace.flow.model import Constant, Variable, Block
from pypy.objspace.flow.model import last_exception, checkgraph
from pypy.translator.gensupp import NameManager
from pypy.translator.unsimplify import remove_direct_loops
from pypy.translator.simplify import simplify_graph
from pypy.rpython.ootypesystem.ootype import Instance, ROOT
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

    sqnames = {
        Constant(None).key:  'nil',
        Constant(False).key: 'false',
        Constant(True).key:  'true',
    }
    
    def __init__(self, sqdir, translator, modname=None):
        self.sqdir = sqdir
        self.translator = translator
        self.modname = (modname or
                        translator.graphs[0].name)

        self.name_manager = NameManager(number_sep="")
        self.unique_name_mapping = {}
        self.pending_nodes = []
        self.generated_nodes = set()

        if conftest.option.view:
            self.translator.view()

        graph = self.translator.graphs[0]
        self.pending_nodes.append(FunctionNode(self, graph))
        self.filename = '%s.st' % graph.name
        file = self.sqdir.join(self.filename).open('w')
        self.gen_source(file)
        file.close()

    def gen_source(self, file):
        while self.pending_nodes:
            node = self.pending_nodes.pop()
            self.gen_node(node, file)

    def gen_node(self, node, f):
        for dep in node.dependencies():
            if dep not in self.generated_nodes:
                self.pending_nodes.append(node)
                self.schedule_node(dep)
                return
        self.generated_nodes.add(node)
        for line in node.render():
            print >> f, line
        print >> f, ""

    def schedule_node(self, node):
        if node not in self.generated_nodes:
            if node in self.pending_nodes:
                # We move the node to the front so we can enforce
                # the generation of dependencies.
                self.pending_nodes.remove(node)
            self.pending_nodes.append(node)

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
        self.schedule_node(ClassNode(self, INSTANCE))
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
        
    def unique_name(self, key, basename):
        if self.unique_name_mapping.has_key(key):
            unique = self.unique_name_mapping[key]
        else:
            camel_basename = camel_case(basename)
            unique = self.name_manager.uniquename(camel_basename)
            self.unique_name_mapping[key] = unique
        return unique


class CodeNode:

    def __hash__(self):
        return hash(self.hash_key)
    
    def __eq__(self, other):
        return isinstance(other, CodeNode) \
                and self.hash_key == other.hash_key
    
    # XXX need other comparison methods?

    def render_fileout_header(self, class_name, category):
        return "!%s methodsFor: '%s' stamp: 'pypy %s'!" % (
                class_name, category,
                datetime.datetime.now().strftime("%m/%d/%Y %H:%M"))

class ClassNode(CodeNode):

    def __init__(self, gen, INSTANCE):
        self.gen = gen
        self.INSTANCE = INSTANCE
        self.hash_key = INSTANCE

    def dependencies(self):
        if self.INSTANCE._superclass is not None: # not root
            return [ClassNode(self.gen, self.INSTANCE._superclass)]
        else:
            return []

    def render(self):
        yield "%s subclass: #%s" % (
            self.gen.nameof_Instance(self.INSTANCE._superclass), 
            self.gen.nameof_Instance(self.INSTANCE))
        yield "    instanceVariableNames: '%s'" % \
            ' '.join(self.INSTANCE._fields.iterkeys())
        yield "    classVariableNames: ''"
        yield "    poolDictionaries: ''"
        yield "    category: 'PyPy-Test'!"

class CallableNode(CodeNode):

    def render_body(self, startblock):
        self.loops = LoopFinder(startblock).loops
        args = startblock.inputargs
        sel = Selector(self.name, len(args))
        yield sel.signature([self.expr(v) for v in args])
 
        # XXX should declare local variables here
        for line in self.render_block(startblock):
            yield "    %s" % line
        yield '! !'

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
            self.gen.schedule_node(
                    MethodNode(self.gen, op.args[1].concretetype, name))
        elif op.opname == "oogetfield":
            receiver = args[0]
            name = op.args[1].value
            args = args[2:]
        elif op.opname == "oosetfield":
            receiver = args[0]
            name = op.args[1].value
            args = args[2:]
            # XXX should only generate setter if field is set from outside
            self.gen.schedule_node(
                    SetterNode(self.gen, op.args[0].concretetype, name))
        elif op.opname == "direct_call":
            # XXX not sure if static methods of a specific class should
            # be treated differently.
            receiver = "PyFunctions"
            name = args[0]
            args = args[1:]
            self.gen.schedule_node(
                FunctionNode(self.gen, op.args[0].value.graph))
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

class MethodNode(CallableNode):

    def __init__(self, gen, INSTANCE, method_name):
        self.gen = gen
        self.INSTANCE = INSTANCE
        self.name = method_name
        self.hash_key = (INSTANCE, method_name)

    def dependencies(self):
        return [ClassNode(self.gen, self.INSTANCE)]

    def render(self):
        yield self.render_fileout_header(
                self.gen.nameof(self.INSTANCE), "methods")
        graph = self.INSTANCE._methods[self.name].graph
        for line in self.render_body(graph.startblock):
            yield line

class FunctionNode(CallableNode):
    
    FUNCTIONS = Instance("Functions", ROOT)

    def __init__(self, gen, graph):
        self.gen = gen
        self.graph = graph
        self.name = gen.nameof(graph.func)
        self.hash_key = graph

    def dependencies(self):
        return [ClassNode(self.gen, self.FUNCTIONS)]

    def render(self):
        yield self.render_fileout_header("PyFunctions class", "functions")
        for line in self.render_body(self.graph.startblock):
            yield line

class SetterNode(CodeNode):

    def __init__(self, gen, INSTANCE, field_name):
        self.gen = gen
        self.INSTANCE = INSTANCE
        self.field_name = field_name
        self.hash_key = (INSTANCE, field_name)

    def dependencies(self):
        return [ClassNode(self.gen, self.INSTANCE)]

    def render(self):
        yield self.render_fileout_header(
                self.gen.nameof_Instance(self.INSTANCE), "accessors")
        yield "%s: value" % self.field_name
        yield "    %s := value" % self.field_name
        yield "! !"

