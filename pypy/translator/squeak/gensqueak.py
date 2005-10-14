import sys
from pypy.objspace.flow.model import traverse
from pypy.objspace.flow import FlowObjSpace
from pypy.objspace.flow.model import Constant, Variable, Block
from pypy.objspace.flow.model import last_exception, checkgraph
from pypy.translator.unsimplify import remove_direct_loops
from pypy.translator.simplify import simplify_graph

selectormap = {
    'setitem:with:': 'at:put:',
    'getitem:':      'at:',
}

def camel_case(str):
    words = str.split('_')
    for i in range(1, len(words)):
	words[i] = words[i].capitalize()
    return ''.join(words)

def arg_names(func, names = None):
    #XXX need to handle more args, see 
    #    http://docs.python.org/ref/types.html#l2h-139
    co = func.func_code
    if not names:
	names = co.co_varnames
    return names[:co.co_argcount]

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
	while args:
	    parts.append(names.pop(0) + ': ' + args.pop(0))
	return ' '.join(parts)
    else:
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
                        translator.functions[0].__name__)
        self.sqnames = {
	    Constant(None).key:  'nil',
	    Constant(False).key: 'false',
	    Constant(True).key:  'true',
	}
        self.seennames = {}
        self.pendingfunctions = []
	self.methods = [] 

	t = self.translator
	func = t.functions[0]
	graph = t.getflowgraph(func)
	simplify_graph(graph)
        remove_direct_loops(t, graph)
        checkgraph(graph)
	#self.translator.view()

        self.nameof(func) #add to pending
        file = self.sqdir.join('%s.st' % func.__name__).open('w')
        self.gen_source(file)
	file.close()
	#self.translator.view()


    def gen_source(self, file):
        while self.pendingfunctions:
            func = self.pendingfunctions.pop()
            self.gen_sqfunction(func, file)

    def gen_sqfunction(self, func, f):

        def expr(v):
            if isinstance(v, Variable):
                return camel_case(v.name)
            elif isinstance(v, Constant):
                return self.nameof(v.value)
            else:
                raise TypeError, "expr(%r)" % (v,)

	def oper(op):
	    args = [expr(arg) for arg in op.args]
	    name = 'py_'+op.opname
	    receiver = args[0]
	    args = args[1:]
	    argnames = ['with'] * len(args)
	    if argnames:
		argnames[0] = ''
	    sel = selector(name, argnames)
	    try:
		sel = selectormap[sel]
	    except KeyError:
		pass
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
#	    if len(block.exits) == 0:
#		#short-cut return block
#		for line in render_return(link.args):
#		    yield line
#		return
	    if link.args:
#		yield '| %s |' % repr(block.inputargs[0])
		for i in range(len(link.args)):
		    yield '%s := %s.' % (expr(block.inputargs[i]), expr(link.args[i]))
	    for line in render_block(block):
		yield line

	def render_block(block):
            #yield '"%s"' % repr(block)
#	    temps = []
#	    for op in block.operations:
#		if isinstance(op.result, Variable):
#		    temps.append(expr(op.result))
#	    if temps:
#		yield "| %s | " % ' '.join(temps)
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

        t = self.translator
        graph = t.getflowgraph(func)

        start = graph.startblock
	args = [expr(arg) for arg in start.inputargs]
	print >> f, '%s' % signature(self.nameof(func), args)
    
	loops = LoopFinder(start).loops

	for line in render_block(start):
	    print >> f, '    %s' % line
	print >> f

    def nameof(self, obj):
        key = Constant(obj).key
        try:
            return self.sqnames[key]
        except KeyError:
            if (type(obj).__module__ != '__builtin__' and
                not isinstance(obj, type)):   # skip user-defined metaclasses
                # assume it's a user defined thingy
                name = self.nameof_instance(obj)
            else:
                for cls in type(obj).__mro__:
                    meth = getattr(self,
                                   'nameof_' + cls.__name__.replace(' ', ''),
                                   None)
                    if meth:
                        break
                else:
		    types = ['nameof_'+t.__name__ for t in type(obj).mro()]
                    raise Exception, "nameof(%r): no method %s" % (obj, types)
                name = meth(obj)
            self.sqnames[key] = name
            return name

    def nameof_int(self, i):
	return str(i)

    def nameof_function(self, func):
        printable_name = '(%s:%d) %s' % (
            func.func_globals.get('__name__', '?'),
            func.func_code.co_firstlineno,
            func.__name__)
        if self.translator.frozen:
            if func not in self.translator.flowgraphs:
                print "NOT GENERATING", printable_name
                return self.skipped_function(func)
        else:
            if (func.func_doc and
                func.func_doc.lstrip().startswith('NOT_RPYTHON')):
                print "skipped", printable_name
                return self.skipped_function(func)
        name = self.unique_name(func.__name__)
	args = arg_names(func)
	sel = selector(name, args)
        self.pendingfunctions.append(func)
        return sel


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
