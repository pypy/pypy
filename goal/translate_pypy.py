#
#  
#
"""
Command-line options for translate_pypy:

   port       Listen on the given port number for connexions
                  (see pypy/translator/tool/pygame/graphclient.py)
   targetspec
              targetspec.py is a python file defining
              what is the translation target and setting things up for it,
              it should have a target function returning an entry_point ...;
              defaults to targetpypy. The .py suffix is optional.
   -text      Don't start the Pygame viewer
   -no-a      Don't infer annotations, just translate everything
   -no-s      Don't simplify the graph after annotation
   -no-t      Don't type-specialize the graph operations with the C typer
   -no-c      Don't generate the C code
   -c         Generate the C code, but don't compile it
   -o         Generate and compile the C code, but don't run it
   -no-mark-some-objects
              Do not mark functions that have SomeObject in their signature.
   -tcc       Equivalent to the envvar PYPY_CC='tcc -shared -o "%s.so" "%s.c"'
                  -- http://fabrice.bellard.free.fr/tcc/
   -no-d      Disable recording of debugging information
   -huge=%    Threshold in the number of functions after which only a local call
              graph and not a full one is displayed
"""
import autopath, sys, threading, pdb, os

from pypy.translator.translator import Translator
from pypy.translator.ann_override import pypy_overrides
from pypy.annotation import model as annmodel
from pypy.tool.cache import Cache
from pypy.annotation.model import SomeObject
from pypy.tool.udir import udir 
from pypy.tool.ansi_print import ansi_print


# XXX this tries to make compiling faster
from pypy.translator.tool import buildpyxmodule
buildpyxmodule.enable_fast_compilation()




# __________  Main  __________

def analyse(target):
    global t, entry_point

    entry_point, inputtypes = target()

    t = Translator(entry_point, verbose=True, simplifying=True)
    if listen_port:
        run_async_server()
    if not options['-no-a']:
        try:
            a = t.annotate(inputtypes, overrides=pypy_overrides)
        finally:
            worstblocks_topten(t.annotator)
        if not options['-no-s']:
            a.simplify()
        if not options['-no-t']:
            a.specialize()
        t.frozen = True   # cannot freeze if we don't have annotations
        if not options['-no-mark-some-objects']:
            options['-no-mark-some-objects'] = True # Do not do this again
            find_someobjects(t)


def find_someobjects(translator, quiet=False):
    """Find all functions in that have SomeObject in their signature."""
    annotator = translator.annotator
    if not annotator:
        return # no annotations available

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
            someobjnum += 1
            translator.highlight_functions[func] = True
            if not quiet:
                if header:
                    header = False
                    print "=" * 70
                    print "Functions that have SomeObject in their signature"
                    print "=" * 70
                print ("%(name)s(%(args)s) -> %(result)s\n"
                       "%(filename)s:%(lineno)s\n"
                       % {'name': graph.name,
                          'filename': func.func_globals.get('__name__', '?'),
                          'lineno': func.func_code.co_firstlineno,
                          'args': ', '.join(map(short_binding,
                                                graph.getargs())),
                          'result': short_binding(graph.getreturnvar())})
        num += 1
    if not quiet:
        print "=" * 70
        percent = int(num and (100.0*someobjnum / num) or 0)
        print "someobjectness: %2d percent" % (percent)
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

def run_async_server():
    from pypy.translator.tool import graphpage, graphserver
    homepage = graphpage.TranslatorPage(t)
    graphserver.run_server(homepage, port=listen_port, background=True)
    options['-text'] = True

def worstblocks_topten(ann, n=10):
    h = [(count, block) for block, count in ann.reflowcounter.iteritems()]
    h.sort()
    print
    ansi_print(',-----------------------  Top %d Most Reflown Blocks  -----------------------.' % n, 36)
    for i in range(n):
        if not h:
            break
        count, block = h.pop()
        ansi_print('                                                      #%3d: reflown %d times  |' % (i+1, count), 36)
        about(block)
    ansi_print("`----------------------------------------------------------------------------'", 36)
    print


if __name__ == '__main__':

    targetspec = 'targetpypy'
    huge = 100

    options = {'-text': False,
               '-no-c': False,
               '-c':    False,
               '-o':    False,
               '-no-mark-some-objects': False,
               '-no-a': False,
               '-no-s': False,
               '-no-t': False,
               '-tcc':  False,
               '-no-d': False,
               }
    listen_port = None
    for arg in sys.argv[1:]:
        if arg in ('-h', '--help'):
            print __doc__.strip()
            sys.exit()
        try:
            listen_port = int(arg)
        except ValueError:
            if os.path.isfile(arg+'.py'):
                assert not os.path.isfile(arg), (
                    "ambiguous file naming, please rename %s" % arg)
                targetspec = arg
            elif os.path.isfile(arg) and arg.endswith('.py'):
                targetspec = arg[:-3]
            elif arg.startswith('-huge='):
                huge = int(arg[6:])
            else:                
                assert arg in options, "unknown option %r" % (arg,)
                options[arg] = True
    if options['-tcc']:
        os.environ['PYPY_CC'] = 'tcc -shared -o "%s.so" "%s.c"'
    if options['-no-d']:
        annmodel.DEBUG = False

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
        from pypy.translator.tool import graphpage
        from pypy.translator.tool.pygame.graphclient import get_layout
        from pypy.translator.tool.pygame.graphdisplay import GraphDisplay
        import pygame

        if not options['-no-mark-some-objects']:
            find_someobjects(t, quiet=True)

        if len(t.functions) <= huge:
            page = graphpage.TranslatorPage(t)
        else:
            page = graphpage.LocalizedCallGraphPage(t, entry_point)

        display = GraphDisplay(get_layout(page))
        async_quit = display.async_quit
        def show(page):
            display.async_cmd(layout=get_layout(page))
        return display.run, show, async_quit, pygame.quit

    class PdbPlusShow(pdb.Pdb):

        def post_mortem(self, t):
            self.reset()
            while t.tb_next is not None:
                t = t.tb_next
            self.interaction(t.tb_frame, t)        

        show = None

        def _show(self, page):
            if not self.show:
                print "*** No display"
                return
            self.show(page)

        def _importobj(self, fullname):
            obj = None
            name = ''
            for comp in fullname.split('.'):
                name += comp
                obj = getattr(obj, comp, None)
                if obj is None:
                    try:
                        obj = __import__(name, {}, {}, ['*'])
                    except ImportError:
                        raise NameError
                name += '.'
            return obj

        TRYPREFIXES = ['','pypy.','pypy.objspace.','pypy.interpreter.', 'pypy.objspace.std.' ]

        def _getobj(self, name):
            if '.' in name:
                for pfx in self.TRYPREFIXES:
                    try:
                        return self._importobj(pfx+name)
                    except NameError:
                        pass
            try:
                return self._getval(name)
            except (NameError, AttributeError, LookupError):
                print "*** Not found:", name
            return None

        def do_showg(self, arg):
            """showg obj
show graph for obj, obj can be an expression or a dotted name
(in which case prefixing with some packages in pypy is tried (see help pypyprefixes)).
if obj is a function or method, the localized call graph is shown;
if obj is a class or ClassDef the class definition graph is shown"""            
            from pypy.annotation.classdef import ClassDef
            from pypy.translator.tool import graphpage            
            obj = self._getobj(arg)
            if obj is None:
                return
            if hasattr(obj, 'im_func'):
                obj = obj.im_func
            if obj in t.flowgraphs:
                page = graphpage.LocalizedCallGraphPage(t, obj)
            elif obj in getattr(t.annotator, 'getuserclasses', lambda: {})():
                page = graphpage.ClassDefPage(t, t.annotator.getuserclasses()[obj])
            elif isinstance(obj, ClassDef):
                page = graphpage.ClassDefPage(t, obj)
            else:
                print "*** Nothing to do"
                return
            self._show(page)

        def do_flowg(self, arg):
            """callg obj
show flow graph for function obj, obj can be an expression or a dotted name
(in which case prefixing with some packages in pypy is tried (see help pypyprefixes))"""            
            import types
            from pypy.translator.tool import graphpage                        
            obj = self._getobj(arg)
            if obj is None:
                return
            if hasattr(obj, 'im_func'):
                obj = obj.im_func
            if not isinstance(obj, types.FunctionType):
                print "*** Not a function"
                return
            self._show(graphpage.FlowGraphPage(t, [obj]))

        def do_callg(self, arg):
            """callg obj
show localized call-graph for function obj, obj can be an expression or a dotted name
(in which case prefixing with some packages in pypy is tried (see help pypyprefixes))"""
            import types
            from pypy.translator.tool import graphpage                        
            obj = self._getobj(arg)
            if obj is None:
                return
            if hasattr(obj, 'im_func'):
                obj = obj.im_func
            if not isinstance(obj, types.FunctionType):
                print "*** Not a function"
                return
            self._show(graphpage.LocalizedCallGraphPage(t, obj))

        def do_classhier(self, arg):
            """classhier
show class hierarchy graph"""
            from pypy.translator.tool import graphpage           
            self._show(graphpage.ClassHierarchyPage(t))

        def help_graphs(self):
            print "graph commands are: showg, flowg, callg, classhier"

        def help_pypyprefixes(self):
            print "these prefixes are tried for dotted names in graph commands:"
            print self.TRYPREFIXES

    def debug(got_error):
        pdb_plus_show = PdbPlusShow()
        
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
            func, args = pdb_plus_show.post_mortem, (tb,)
        else:
            print '-'*60
            print 'Done.'
            print
            func, args = pdb_plus_show.set_trace, ()
        if options['-text']:
            func(*args)
        else:
            start, show, stop, cleanup = run_server()
            pdb_plus_show.show = show
            debugger = run_in_thread(func, args, stop)
            debugger.start()
            start()
            debugger.join()
            cleanup()

    try:
        targetspec_dic = {}
        sys.path.insert(0, os.path.dirname(targetspec))
        execfile(targetspec+'.py',targetspec_dic)
        print "Analysing target as defined by %s" % targetspec
        analyse(targetspec_dic['target'])
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
                targetspec_dic['run'](c_entry_point)
    except:
        debug(True)
    else:
        debug(False)
    
