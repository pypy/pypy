"""

This is an experimental hack - use it at your peril!  I (rxe) needed some sanity
check when (attempting) to write gencpp.py and this ended up being a useful
exercise.  I doubt it much use to anyone else or the rest of the project, but it
might have some interesting possiblities later on once we have full translation.
:-)

The idea is simple - take the basic blocks output via the flow object space and
evaluate them against the standard object space.  It is effectively the same as
creating a C extension to the CPython interpreter to use the CPython API instead
of interpreting bytecodes - except in this case the we don't need to compile
anything and all space operations are emitted on the fly.  One might call this a
flow interpreter - I wouldn't go that far!

"""
import autopath
from pypy.objspace.flow import FlowObjSpace
from pypy.objspace.flow.model import traverse, Constant, Variable, Block, Link
from pypy.translator.simplify import simplify_graph
from pypy.interpreter.baseobjspace import OperationError


class FlowTracer(object):

    def __init__(self, flow_space, space, debug = False, trace = True):
        self.space = space
        self.flow_space = flow_space
        self.trace = trace
        self.debug = debug

    def pprint(self, v):        
        s = self.space.unwrap(self.space.repr(v.e_value))
        if len(s) > 30:
            s = s[:27] + "..."

            if isinstance(v, Constant):
                s = "Const(%s)" % s

            elif isinstance(v, Variable):
                s = "%s(%s)" % (v, s)

            else:
                assert False, "really?"
        return s


    def get_blocknames(self, graph):
        blocknames = {}
        def visit(n):        
            if isinstance(n, Block):
                blocknames[n] = 'block%d' % len(blocknames)

        traverse(visit, graph)
        return blocknames

    
    def wrap_constants(self, graph):
        all = []
        
        def visit(n):
            # Note - be careful with uniqueitems and constants, as there can
            # multiple constant of the same value (XXX why?)
            if isinstance(n, Block):
                values = []
                values += n.inputargs
                for op in n.operations:
                    values += op.args

                for ii in values:
                    all.append(ii)

                all.append(n.exitswitch)
                
            if isinstance(n, Link):
                values = n.args
                for ii in values:
                    all.append(ii)
                
        traverse(visit, graph)
        for ii in all:
            
            if isinstance(ii, Constant) :
                ii.e_value = self.space.wrap(ii.value)

            else:
                assert (isinstance(ii, Variable) or ii is None)

    def wrap_linkexits(self, graph):
        all = []
        
        def visit(n):                        
            if isinstance(n, Link):
                all.append(n)

        traverse(visit, graph)

        for l in all:
            l.exitcase = self.space.wrap(l.exitcase)

        
    def execute_function(self, graph, *args_w):

        curblock = graph.startblock
        assert len(curblock.inputargs) == len(args_w)        

        # We add value as evaluated values during interpretation
        # to variables, constants and exit switches.
        # Variables are done on assignment (ie lazily)
        for input, arg in zip(curblock.inputargs, args_w):
            input.e_value = arg

        # Here we add value attribute with wrap
        self.wrap_constants(graph)
        self.wrap_linkexits(graph)
        
        blocknames = self.get_blocknames(graph)
        last_exception = None
        while True:
            
            if self.trace:
                print 'Entering %s:' % blocknames[curblock]
                print '  Input args :- %s' % (", ".join(map(self.pprint, curblock.inputargs)))
                print '  Operations :-'

            for op in curblock.operations:
                
                # Why does op.args have a list in it?
                opargs = [a.e_value for a in op.args]
                if self.trace:
                    print '    %s  = space.%s(%s)' % (op.result, 
                                                   op.opname,
                                                   ", ".join(map(self.pprint, op.args)))

                if op.opname == "exception":
                    assert (len(opargs) == 1)
                    # XXX What we suppose to do with argument???
                    if last_exception is not None:
                        res = last_exception
                        last_exception = None
                    else:
                        res = self.space.w_None

                elif op.opname == "simple_call":
                    assert (len(opargs) >= 1)
                    res = self.simple_call(opargs[0], *opargs[1:])

                else:
                    # More special cases
                    spaceop = getattr(self.space, op.opname)
                    
                    if op.opname in ("newlist", "newdict", "newtuple"):
                        # These expect a list, not a *args
                        res = spaceop(opargs)

                    else:
                        try:
                            res = spaceop(*opargs)

                            # More special case
                            if op.opname == "is_true":
                                # Rewrap it!
                                res = self.space.wrap(res)
                                
                        except OperationError, exc:
                            last_exception = exc.w_type
                            res = self.space.w_None
                        
                op.result.e_value = res
                
                if self.trace:
                    # Cases will likely not be a space object
                    if curblock.exits and curblock.exitswitch == op.result:
                        print '    %s := exit(%s)' % (op.result, op.result.e_value)
                    else:
                        print '    %s := %s' % (op.result, self.pprint(op.result))

            # Switch to next block
            if curblock.exits:

                # exits (safe code)                
                exit_link = None
                if len(curblock.exits) == 1:
                    exit_link = curblock.exits[0]

                else:
                    exit_res = curblock.exitswitch.e_value
                    for link in curblock.exits:
                        if self.space.is_true(self.space.eq(exit_res, link.exitcase)):
                            exit_link = link
                            break

                assert exit_link is not None
                
                if self.trace:
                    print '  Exit to %s :- ' % blocknames[exit_link.target]

                sourceargs = exit_link.args
                targetargs = exit_link.target.inputargs
                assert len(sourceargs) == len(targetargs)

                for s, t in zip(sourceargs, targetargs):                    
                    if self.trace:
                        print "    %s = %s" % (t, s)

                    t.e_value = s.e_value

                curblock = exit_link.target

                if self.trace:
                    print
                
            elif len(curblock.inputargs) == 2:   # exc_cls, exc_value
                exc_cls, exc_value = curblock.inputargs
                if self.trace:
                    print "Raising -",
                    print self.pprint(exc_cls), self.pprint(exc_value)
                raise exc_cls.e_value, exc_value.e_value

            else:
                result = curblock.inputargs[0]
                if self.trace:
                    print "Returning -", self.pprint(result)

                return result.e_value


    def simple_call(self, w_func, *args_w):
        
        func = self.space.unwrap(w_func)
        if hasattr(func, "func_code"):        
            graph = self.flow_space.build_flow(func)
            simplify_graph(graph)
            if self.debug:
                debug(func) 
            return self.execute_function(graph, *args_w)

        else:
            # XXX We could try creating the flow graph by runnning another
            # flow objspace under self.space.  Hmmm - if only I had
            # bigger computer. 

            # Instead we cheat (this is great fun when it is a fake type :-))
            if self.trace:
                print "WOA! Cheating!", w_func

            return self.space.call_function(w_func, *args_w)  
            

    def call(self, f, *args):
        w = self.space.wrap
        args_w = [w(ii) for ii in args]
        w_func = w(f)

        res = self.simple_call(w_func, *args_w)
        return self.space.unwrap(res)
            

def debug(func):
    """Shows the control flow graph with annotations if computed.
    Requires 'dot' and pygame."""
    from pypy.translator.tool.pygame.graphdisplay import GraphDisplay
    from pypy.translator.tool.pygame.flowviewer import FlowGraphLayout
    from pypy.translator.translator import Translator
    t = Translator(func)
    t.simplify()
    #t.annotate([int])
    GraphDisplay(FlowGraphLayout(t)).run()

def timeit(num, func, *args):
    from time import time as now
    start = now()
    for i in xrange(num):
        print func(*args)
    return now() - start

if __name__ == '__main__':
    from pypy.objspace.std import Space
    space = Space()

    def create_std_func(app_func):

        import new 
        from pypy.interpreter.gateway import app2interp
        from pypy.interpreter.argument import Arguments    

        # Horrible hack (ame needs to start with "app_")
        app_func = new.function(app_func.func_code,
                                app_func.func_globals,
                                "app_" + app_func.__name__)
        
        # Create our function
        func_gw = app2interp(app_func)
        func = func_gw.get_function(space)
        w_func = space.wrap(func)
          
        def f(*args):
            args_w = [space.wrap(ii) for ii in args]
            args_ = Arguments(space, args_w)
            w_result = space.call_args(w_func, args_)
            return space.unwrap(w_result) 
        return f
    
    def create_flow_func(f):
        flow_space = FlowObjSpace()
        interpreter = FlowTracer(flow_space, space)
        def func(*args):
            return interpreter.call(f, *args)
        return func
    
    def do(f, *args):
        print "doing %s(%s)" % (f.__name__, ", ".join(map(str, args)))
        f_flow = create_flow_func(f)
        res = f_flow(*args)
        f_norm = create_std_func(f)
        res_norm = f_norm(*args)
        assert res == res_norm 
        return res

    def do_flow_only(f, *args):
        print "doing %s(%s)" % (f.__name__, ", ".join(map(str, args)))
        f_flow = create_flow_func(f)
        res = f_flow(*args)
        return res

    #/////////////////////////////////////////////////////////////////////////////

    def tests():
        from pypy.translator.test import snippet
        
        tests = [
            (snippet.if_then_else, 1, 2, 3),
            (snippet.if_then_else, 0, 2, 3),
            (snippet.my_gcd, 256, 192),
            (snippet.is_perfect_number, 81),
            (snippet.my_bool, 1),
            (snippet.my_bool, 0),
            (snippet.two_plus_two,),
            #(snippet.sieve_of_eratosthenes,),
            (snippet.simple_func, 10),
            (snippet.nested_whiles, 1, 10),
            (snippet.simple_func, 10),
            (snippet.builtinusage,),
            (snippet.poor_man_range, 10),
            (snippet.poor_man_rev_range, 10),
            (snippet.simple_id, 2) ,
            (snippet.branch_id, 1, "k", 1.0) ,
            (snippet.branch_id, False, "k", 1.0) ,
            (snippet.builtinusage,),
            (snippet.yast, [1,2,3,4,5]),
            (snippet.time_waster, 5),
            (snippet.half_of_n, 20),
            (snippet.int_id, 20),
            (snippet.greet, "world"),
            (snippet.choose_last,),
            #(snippet.choose_last,), XXX Why does repeating this break?
            (snippet.poly_branch, 1),
            (snippet.s_and, 1, 1),
            (snippet.s_and, 0, 1),
            (snippet.s_and, 1, 0),
            (snippet.s_and, 0, 0),
            (snippet.break_continue, 15),
            (snippet.reverse_3, ("k", 1, 1.0)),
            (snippet.finallys, ("k", 1, 1.0)),
            (snippet.finallys, ("k",)),
            (snippet.finallys, []),
            (snippet._append_five, []),
            (snippet._append_five, [1,2,3]),
            ]
        for ii in tests:
            print do(*ii) 

        tests = [
            (snippet.factorial, 4),
            (snippet.factorial2, 4),
            (snippet.call_five,),
            (snippet.build_instance,),
            (snippet.set_attr,),
            (snippet.merge_setattr, 0),        
            (snippet.merge_setattr, 1),        
            # XXX These don't work from test.snippet (haven't tried anymore)
            #(snippet.inheritance1,),        
            #(snippet.inheritance2,),        

            ]

        for ii in tests:
            print do_flow_only(*ii) 

    tests()

