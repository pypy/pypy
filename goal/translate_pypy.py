#
#  
#
"""
Command-line options for translate_pypy:

   -text    Don't start the Pygame viewer
   -no-a    Don't infer annotations, just translate everything
   -no-c    Don't generate the C code
   -c       Generate the C code, but don't compile it
   -o       Generate and compile the C code, but don't run it
   -no-mark-some-objects
            Do not mark functions that have SomeObject in their signature.
   -tcc     Equivalent to the envvar PYPY_CC='tcc -shared -o "%s.so" "%s.c"'
                -- http://fabrice.bellard.free.fr/tcc/
"""
import autopath, sys, threading, pdb, os
from pypy.objspace.std.objspace import StdObjSpace, W_Object
from pypy.objspace.std.intobject import W_IntObject
from pypy.translator.translator import Translator
from pypy.annotation import model as annmodel
from pypy.tool.cache import Cache
from pypy.annotation.model import SomeObject
from pypy.tool.udir import udir 

# XXX this tries to make compiling faster
from pypy.translator.tool import buildpyxmodule
buildpyxmodule.enable_fast_compilation()

#from buildcache import buildcache
# __________  Entry point  __________

def entry_point():
    w_a = W_IntObject(space, -6)
    w_b = W_IntObject(space, -7)
    return space.mul(w_a, w_b)


# __________  Main  __________

def analyse(entry_point=entry_point):
    global t, space
    space = StdObjSpace()
    # call the entry_point once to trigger building of all 
    # caches (as far as analyzing the entry_point is concerned) 
    entry_point() 
    t = Translator(entry_point, verbose=True, simplifying=True)
    if not options['-no-a']:
        a = t.annotate([])
        a.simplify()
        t.frozen = True   # cannot freeze if we don't have annotations

        if not options['-no-mark-some-objects']:
            find_someobjects(a)


def find_someobjects(annotator):
    """Find all functions in that have SomeObject in their signature."""
    translator = annotator.translator
    translator.highlight_functions = {}

    def is_someobject(var):
        try:
            return annotator.binding(var).__class__ == SomeObject
        except KeyError:
            return False

    def short_binding(var):
        try:
            binding = annotator.binding(var)
        except KeyError:
            return "?"
        if binding.is_constant():
            return 'const %s' % binding.__class__.__name__
        else:
            return binding.__class__.__name__

    header = True
    items = [(graph.name, func, graph)
             for func, graph in translator.flowgraphs.items()]
    items.sort()
    num = someobjnum = 0
    for graphname, func, graph in items:
        unknown_input_args = len(filter(is_someobject, graph.getargs()))
        unknown_return_value = is_someobject(graph.getreturnvar())
        if unknown_input_args or unknown_return_value:
            if header:
                header = False
                print "=" * 70
                print "Functions that have SomeObject in their signature"
                print "=" * 70
            translator.highlight_functions[func] = True
            print ("%(name)s(%(args)s) -> %(result)s\n"
                   "%(filename)s:%(lineno)s\n"
                   % {'name': graph.name,
                      'filename': func.func_globals.get('__name__', '?'),
                      'lineno': func.func_code.co_firstlineno,
                      'args': ', '.join(map(short_binding, graph.getargs())),
                      'result': short_binding(graph.getreturnvar())})
            someobjnum += 1
        num += 1
    print "=" * 70
    percent = int(num and (100.0*someobjnum / num) or 0)
    print "somobjectness: %2d percent" % (percent)
    print "(%d out of %d functions get or return SomeObjects" % (
        someobjnum, num) 
    print "=" * 70

def update_usession_dir(stabledir = udir.dirpath('usession')): 
    from py import path 
    try:
        if stabledir.check(dir=1): 
            for x in udir.visit(path.checker(file=1)): 
                target = stabledir.join(x.relto(udir)) 
                if target.check():
                    target.remove()
                else:
                    target.dirpath().ensure(dir=1) 
                try:
                    target.mklinkto(x) 
                except path.Invalid: 
                    x.copy(target) 
    except path.Invalid: 
        print "ignored: couldn't link or copy to %s" % stabledir 

def run_in_thread(fn, args, cleanup=None, cleanup_args=()):
    def _run_in_thread():
        fn(*args)
        if cleanup is not None:
            cleanup(*cleanup_args)
    return threading.Thread(target=_run_in_thread, args=())

if __name__ == '__main__':

    options = {'-text': False,
               '-no-c': False,
               '-c':    False,
               '-o':    False,
               '-no-mark-some-objects': False,
               '-no-a': False,
               '-tcc':  False,
               }
    for arg in sys.argv[1:]:
        if arg in ('-h', '--help'):
            print __doc__.strip()
            sys.exit()
        assert arg in options, "unknown option %r" % (arg,)
        options[arg] = True
    if options['-tcc']:
        os.environ['PYPY_CC'] = 'tcc -shared -o "%s.so" "%s.c"'

    def about(x):
        """ interactive debugging helper """
        from pypy.objspace.flow.model import Block, flatten
        if isinstance(x, Block):
            for func, graph in t.flowgraphs.items():
                if x in flatten(graph):
                    funcname = func.func_name
                    cls = getattr(func, 'class_', None)
                    if cls:
                        funcname = '%s.%s' % (cls.__name__, funcname)
                    print '%s is a %s in the graph of %s' % (x,
                                x.__class__.__name__, funcname)
                    print 'at %s:%d' % (func.func_globals.get('__name__', '?'),
                                        func.func_code.co_firstlineno)
                    break
            else:
                print '%s is a %s at some unknown location' % (x,
                                x.__class__.__name__)
            print 'containing the following operations:'
            for op in x.operations:
                print op
            print '--end--'
            return
        print "don't know about", x

    def run_server():
        from pypy.translator.tool.pygame.flowviewer import TranslatorLayout
        from pypy.translator.tool.pygame.graphdisplay import GraphDisplay
        import pygame
        display = GraphDisplay(TranslatorLayout(t))
        async_quit = display.async_quit
        return display.run, async_quit, pygame.quit

    def debug(got_error):
        if got_error:
            import traceback
            exc, val, tb = sys.exc_info()
            print >> sys.stderr
            traceback.print_exception(exc, val, tb)
            print >> sys.stderr

            block = getattr(val, '__annotator_block', None)
            if block:
                print '-'*60
                about(block)
                print '-'*60

            print >> sys.stderr
            func, args = pdb.post_mortem, (tb,)
        else:
            print '-'*60
            print 'Done.'
            print
            func, args = pdb.set_trace, ()
        if options['-text']:
            func(*args)
        else:
            start, stop, cleanup = run_server()
            debugger = run_in_thread(func, args, stop)
            debugger.start()
            start()
            debugger.join()
            cleanup()

    try:
        analyse()
        print '-'*60
        if options['-no-c']:
            print 'Not generating C code.'
        elif options['-c']:
            print 'Generating C code without compiling it...'
            filename = t.ccompile(really_compile=False)
            update_usession_dir()
            print 'Written %s.' % (filename,)
        else:
            print 'Generating and compiling C code...'
            c_entry_point = t.ccompile()
            update_usession_dir()
            if not options['-o']:
                print 'Running!'
                w_result = c_entry_point()
                print w_result
                print w_result.intval
                assert w_result.intval == 42
    except:
        debug(True)
    else:
        debug(False)
    
