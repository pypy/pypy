"""
Implementation of a translator from Python to interpreter level RPython.

The idea is that we can automatically transform app-space implementations
of methods into some equivalent representation at interpreter level.
Then, the RPython to C translation might hopefully spit out some
more efficient code than always interpreting these methods.

This module is very much under construction and not yet usable but
for testing.

XXX to do: Subclass parts of the flow space and translator and teach
them that this is not to be treated as RPython.
"""

from pypy.objspace.flow.model import traverse
from pypy.objspace.flow import FlowObjSpace
from pypy.objspace.flow.model import FunctionGraph, Block, Link, Variable, Constant
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.translator.simplify import simplify_graph
from pypy.interpreter.error import OperationError

from pypy.translator.translator import Translator

import sys

def somefunc(arg):
    pass

def f(a,b):
    print "start"
    a = []
    a.append(3)
    for i in range(3):
        print i
    if a > b:
        try:
            if b == 123:
                raise ValueError
            elif b == 321:
                raise IndexError
            return 123
        except ValueError:
            raise TypeError
    else:
        dummy = somefunc(23)
        return 42

def ff(a, b):
    try:
        raise SystemError, 42
        return a+b
    finally:
        a = 7

glob = 100
def fff():
    global glob
    return 42+glob

def app_str_decode__String_ANY_ANY(str, encoding=None, errors=None):
    if encoding is None and errors is None:
        return unicode(str)
    elif errors is None:
        return unicode(str, encoding)
    else:
        return unicode(str, encoding, errors)
        

def ordered_blocks(graph):
    # collect all blocks
    allblocks = []
    def visit(block):
        if isinstance(block, Block):
            # first we order by offset in the code string
            if block.operations:
                ofs = block.operations[0].offset
            else:
                ofs = sys.maxint
            # then we order by input variable name or value
            if block.inputargs:
                txt = str(block.inputargs[0])
            else:
                txt = "dummy"
            allblocks.append((ofs, txt, block))
    traverse(visit, graph)
    allblocks.sort()
    #for ofs, txt, block in allblocks:
    #    print ofs, txt, block
    return [block for ofs, txt, block in allblocks]


class GenRpy:
    def __init__(self, f, translator):
        self.f = f
        self.translator = translator
        self.rpynames = {}

        # special constructors:
        self.has_listarg = {}
        for name in "newtuple newlist newdict newstring".split():
            self.has_listarg[name] = name

    def nameof(self, obj):
        key = Constant(obj).key
        try:
            return self.rpynames[key]
        except KeyError:
            name = "w(%s)" % str(obj)
            self.rpynames[key] = name
            return name

    def gen_rpyfunction(self, func):

        local_names = {}

        def expr(v, wrapped = True):
            if isinstance(v, Variable):
                n = v.name
                if n.startswith("v") and n[1:].isdigit():
                    ret = local_names.get(v.name)
                    if not ret:
                        if wrapped:
                            local_names[v.name] = ret = "w_%d" % len(local_names)
                        else:
                            local_names[v.name] = ret = "v%d" % len(local_names)
                    return ret
                return v.name
            elif isinstance(v, Constant):
                return self.nameof(v.value)
            else:
                #raise TypeError, "expr(%r)" % (v,)
                # XXX how do I resolve these?
                return "space.%s" % str(v)

        def arglist(args):
            res = [expr(arg) for arg in args]
            return ", ".join(res)
        
        def oper(op):
            # specialcase is_true
            if op.opname in self.has_listarg:
                fmt = "%s = %s([%s])"
            else:
                fmt = "%s = %s(%s)"
            if op.opname == "is_true":
                return fmt % (expr(op.result, False), expr(op.opname), arglist(op.args))    
            return fmt % (expr(op.result), expr(op.opname), arglist(op.args))    

        def gen_link(link, linklocalvars=None):
            "Generate the code to jump across the given Link."
            linklocalvars = linklocalvars or {}
            left, right = [], []
            for a1, a2 in zip(link.args, link.target.inputargs):
                if a1 in linklocalvars:
                    src = linklocalvars[a1]
                else:
                    src = expr(a1)
                left.append(expr(a2))
                right.append(src)
            yield "%s = %s" % (", ".join(left), ", ".join(right))
            goto = blocknum[link.target]
            yield 'goto = %d' % goto
            if goto <= blocknum[block]:
                yield 'continue'
        
        f = self.f
        t = self.translator
        t.simplify(func, rpython=False)
        graph = t.getflowgraph(func)

        start = graph.startblock
        blocks = ordered_blocks(graph)
        nblocks = len(blocks)
        assert blocks[0] is start

        blocknum = {}
        for block in blocks:
            blocknum[block] = len(blocknum)+1

        # create function declaration
        name = func.__name__  # change this
        args = [expr(var) for var in start.inputargs]
        argstr = ", ".join(args)
        print >> f, "def %s(space, %s):" % (name, argstr)
        print >> f, "    w = space.wrap"
        print >> f, "    goto = 1 # startblock"
        print >> f, "    while True:"
        
        def render_block(block):
            catch_exception = block.exitswitch == Constant(last_exception)
            regular_op = len(block.operations) - catch_exception
            # render all but maybe the last op
            for op in block.operations[:regular_op]:
                yield "%s" % oper(op)
            # render the last op if it is exception handled
            for op in block.operations[regular_op:]:
                yield "try:"
                yield "    %s" % oper(op)

            if len(block.exits) == 0:
                if len(block.inputargs) == 2:   # exc_cls, exc_value
                    # exceptional return block
                    exc_cls = expr(block.inputargs[0])
                    exc_val = expr(block.inputargs[1])
                    yield "raise OperationError(%s, %s)" % (exc_cls, exc_val)
                else:
                    # regular return block
                    retval = expr(block.inputargs[0])
                    yield"return %s" % retval
                return
            elif block.exitswitch is None:
                # single-exit block
                assert len(block.exits) == 1
                for op in gen_link(block.exits[0]):
                    yield "    %s" % op
            elif catch_exception:
                # block catching the exceptions raised by its last operation
                # we handle the non-exceptional case first
                link = block.exits[0]
                assert link.exitcase is None
                for op in gen_link(link):
                    yield "    %s" % op
                # we must catch the exception raised by the last operation,
                # which goes to the last err%d_%d label written above.
                yield "except OperationError, e:"
                for link in block.exits[1:]:
                    assert issubclass(link.exitcase, Exception)
                    for op in gen_link(link, {
                                Constant(last_exception): 'e.w_type',
                                Constant(last_exc_value): 'e.w_value'}):
                        yield "    %s" % op
            else:
                # block ending in a switch on a value
                exits = list(block.exits)
                if len(exits) == 2 and (
                    exits[0].exitcase is False and exits[1].exitcase is True):
                    # order these guys like Python does
                    exits.reverse()
                q = "if"
                for link in exits[:-1]:
                    yield "%s %s == %s:" % (q, expr(block.exitswitch),
                                                     link.exitcase)
                    for op in gen_link(link):
                        yield "    %s" % op
                    q = "elif"
                link = exits[-1]
                yield "else:"
                yield "    assert %s == %s" % (expr(block.exitswitch),
                                                    link.exitcase)
                for op in gen_link(exits[-1]):
                    yield "    %s" % op

        for block in blocks:
            blockno = blocknum[block]
            print >> f
            print "        if goto == %d:" % blockno
            for line in render_block(block):
                print "            %s" % line

entry_point = (f, ff, fff, app_str_decode__String_ANY_ANY) [0]

t = Translator(entry_point, verbose=False, simplifying=False)
#t.simplify(rpython=False)
#t.view()
gen = GenRpy(sys.stdout, t)
gen.gen_rpyfunction(t.functions[0])
# debugging
graph = t.getflowgraph()
ab = ordered_blocks(graph) # use ctrl-b in PyWin with ab

