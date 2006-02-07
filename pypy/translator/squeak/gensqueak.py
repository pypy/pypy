import sys
from pypy.objspace.flow.model import traverse
from pypy.objspace.flow import FlowObjSpace
from pypy.objspace.flow.model import Constant, Variable, Block
from pypy.objspace.flow.model import last_exception, checkgraph
from pypy.translator.unsimplify import remove_direct_loops
from pypy.translator.simplify import simplify_graph
from pypy import conftest

selectormap = {
    'setitem:with:': 'at:put:',
    'getitem:':      'at:',
    'new':           'new',
    'runtimenew':    'new',
    'classof':       'class',
    'sameAs':        'yourself',
    'intAdd:':       '+',
}

def camel_case(str):
    words = str.split('_')
    for i in range(1, len(words)):
        words[i] = words[i].capitalize()
    return ''.join(words)

def arg_names(graph):
    #XXX need to handle more args, see 
    #    http://docs.python.org/ref/types.html#l2h-139
    names, vararg, kwarg = graph.signature
    assert vararg is None
    assert kwarg is None
    return names

def selector(name, args):
    s = name
    if args:
        s += '_'
        for arg in args:
            s += arg + ':'
    return camel_case(s)

def signature(sel, args):
    if (':' in sel):
        parts = []
        names = sel.split(':')
#       assert len(names) == len(args)
        while args:
            parts.append(names.pop(0) + ': ' + args.pop(0))
        return ' '.join(parts)
    elif not sel[0].isalnum():
#       assert len(args) == 1
        return "%s %s" %(sel, args[0])
    else:
#       assert len(args) == 0
        return sel


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
        self.seennames = {}
        self.pendinggraphs = []
        self.pendingclasses = []
        self.pendingmethods = []
        self.classes = [] 
        self.methods = [] 

        t = self.translator
        graph = t.graphs[0]
        simplify_graph(graph)
        remove_direct_loops(t, graph)
        checkgraph(graph)

        if conftest.option.view:
            self.translator.view()

        self.nameof(graph) #add to pending
        file = self.sqdir.join('%s.st' % graph.name).open('w')
        self.gen_source(file)
        file.close()


    def gen_source(self, file):
        while self.pendinggraphs or self.pendingclasses or self.pendingmethods:
            while self.pendinggraphs:
                graph = self.pendinggraphs.pop()
                self.gen_sqfunction(graph, file)
            while self.pendingclasses:
                inst = self.pendingclasses.pop()
                self.gen_sqclass(inst, file)
            while self.pendingmethods:
                (inst, meth) = self.pendingmethods.pop()
                self.gen_sqmethod(inst, meth, file)

    def gen_sqclass(self, inst, f):
        self.classes.append(inst)
        print >> f, """%s subclass: #%s
        instanceVariableNames: '%s'
        classVariableNames: ''
        poolDictionaries: ''
        category: 'PyPy-Test'!
        """ % (
            self.nameof_Instance(inst._superclass), 
            self.nameof_Instance(inst),
            ' '.join(inst._fields.iterkeys()))

    def gen_sqmethod(self, inst, meth, f):
        if (inst, meth) in self.methods:
            return
        self.methods.append((inst, meth))
        print >> f, "!%s methodsFor: 'methods' stamp: 'pypy 1/1/2000 00:00'!" % (
            self.nameof_Instance(inst))
        print >> f, "%s" % meth
        print >> f, '   "XXX methods not generated yet"'
        print >> f, "! !"
        print >> f


    def gen_sqfunction(self, graph, f):

        def expr(v):
            if isinstance(v, Variable):
                return camel_case(v.name)
            elif isinstance(v, Constant):
                return self.nameof(v.value)
            else:
                raise TypeError, "expr(%r)" % (v,)

        def oper(op):
            args = [expr(arg) for arg in op.args]
            if op.opname == "oosend":
                name = op.args[0].value
                receiver = args[1]
                args = args[2:]
                self.note_meth(op.args[1].concretetype, name)
            elif op.opname == "oogetfield":
                receiver = args[0]
                name = op.args[1].value
                args = args[2:]
            elif op.opname == "oosetfield":
                receiver = args[0]
                name = op.args[1].value
                args = args[2:]
            else:
                name = op.opname
                receiver = args[0]
                args = args[1:]
            argnames = ['with'] * len(args)
            if argnames:
                argnames[0] = ''
            sel = selector(name, argnames)
            if op.opname != "oosend":
                sel = selectormap.get(sel, sel)
            return "%s := %s %s." % (expr(op.result), receiver, signature(sel, args))

        def render_return(args):
            if len(args) == 2:
                # exception
                exc_cls = expr(args[0])
                exc_val = expr(args[1])
                yield "(PyOperationError class: %s value: %s) signal." % (exc_cls, exc_val)
            else:
                # regular return block
                retval = expr(args[0])
                yield "^%s" % retval

        def render_link(link):
            block = link.target
            if link.args:
                for i in range(len(link.args)):
                    yield '%s := %s.' % (expr(block.inputargs[i]), expr(link.args[i]))
            for line in render_block(block):
                yield line

        def render_block(block):
            if loops.has_key(block):
                if not loops[block]:
                    yield '"skip1"'
                    return
                yield "["
            for op in block.operations:
                yield "%s" % oper(op)
            if len(block.exits) == 0:
                for line in render_return(block.inputargs):
                    yield line
                return
            elif block.exitswitch is None:
                # single-exit block
                assert len(block.exits) == 1
                for line in render_link(block.exits[0]):
                    yield line
            else:
                #exitswitch
                if loops.has_key(block):
                    if loops[block]:
                        loops[block] = False
                        yield "%s] whileTrue: [" % expr(block.exitswitch)
                        for line in render_link(block.exits[True]):
                            yield "    %s" % line
                        yield "]."
                        for line in render_link(block.exits[False]):
                            yield "%s" % line
                else:
                    yield "%s ifTrue: [" % expr(block.exitswitch)
                    for line in render_link(block.exits[True]):
                        yield "    %s" % line
                    yield "] ifFalse: [" 
                    for line in render_link(block.exits[False]):
                        yield "    %s" % line
                    yield "]"

        start = graph.startblock
        args = [expr(arg) for arg in start.inputargs]
        print >> f, '%s' % signature(self.nameof(graph), args)
    
        loops = LoopFinder(start).loops

        for line in render_block(start):
            print >> f, '       %s' % line
        print >> f

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

    def nameof_FunctionGraph(self, graph):
        #XXX this should actually be a StaticMeth
        name = self.unique_name(graph.name.split('.')[-1])
        args = arg_names(graph)
        sel = selector(name, args)
        self.pendinggraphs.append(graph)
        return sel

    #def nameof_function(self, func):
    #    #XXX this should actually be a StaticMeth
    #    printable_name = '(%s:%d) %s' % (
    #        func.func_globals.get('__name__', '?'),
    #        func.func_code.co_firstlineno,
    #        func.__name__)
    #    if self.translator.frozen:
    #        if func not in self.translator.flowgraphs:
    #            print "NOT GENERATING", printable_name
    #            return self.skipped_function(func)
    #    else:
    #        if (func.func_doc and
    #            func.func_doc.lstrip().startswith('NOT_RPYTHON')):
    #            print "skipped", printable_name
    #            return self.skipped_function(func)
    #    name = self.unique_name(func.__name__)
    #    args = arg_names(func)
    #    sel = selector(name, args)
    #    self.pendingfunctions.append(func)
    #    return sel

    def nameof_Instance(self, inst):
        if inst is None:
            #empty superclass
            return "Object"
        self.note_Instance(inst)
        return "Py%s" % inst._name.capitalize()

    def note_Instance(self, inst):
        if inst not in self.classes:
            if inst not in self.pendingclasses:
                self.pendingclasses.append(inst)

    def note_meth(self, inst, meth):
        bm = (inst, meth)
        if bm not in self.methods:
            if bm not in self.pendingmethods:
                self.pendingmethods.append(bm)

    def unique_name(self, basename):
        n = self.seennames.get(basename, 0)
        self.seennames[basename] = n+1
        if n == 0:
            return basename
        else:
            return self.unique_name('%s_%d' % (basename, n))


    def skipped_function(self, func):
        # debugging only!  Generates a placeholder for missing functions
        # that raises an exception when called.
        name = self.unique_name(camel_case('skipped_' + func.__name__))
        return name
