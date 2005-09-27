#! /usr/bin/env python
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
              defaults to targetpypystandalone. The .py suffix is optional.
   -text      Don't start the Pygame viewer
   -no-a      Don't infer annotations, just translate everything
   -no-t      Don't type-specialize the graph operations with the C typer
   -t-insist  Specialize should not stop at the first error
   -no-o      Don't do backend-oriented optimizations
   -no-c      Don't generate the C code
   -fork      (UNIX) Create a restartable checkpoint after annotation
   -fork2     (UNIX) Create a restartable checkpoint after specializing
   -llvm      Use LLVM instead of C
   -c         Generate the C code, but don't compile it
   -boehm     Use the Boehm collector when generating C code
   -no-gc     Experimental: use no GC and no refcounting at all
   -o         Generate and compile the C code, but don't run it
   -tcc       Equivalent to the envvar PYPY_CC='tcc -shared -o "%s.so" "%s.c"'
                  -- http://fabrice.bellard.free.fr/tcc/
   -d         Enable recording of annotator debugging information
   -huge=%    Threshold in the number of functions after which only a local call
              graph and not a full one is displayed
   -use-snapshot
              Redirect imports to the translation snapshot
   -save filename
              saves the translator to a file. The file type can either
              be .py or .zip (recommended).
   -load filename
              restores the translator from a file. The file type must
              be either .py or .zip .
   -llinterpret
              interprets the flow graph after rtyping it
   -t-lowmem  try to save as much memory as possible, since many computers
              tend to have less than a gigabyte of memory (512 MB is typical).
              Currently, we avoid to use geninterplevel, which creates a lot
              of extra blocks, but gains only some 10-20 % of speed, because
              we are still lacking annotation of applevel code.
   -batch     don't use interactive helpers, like pdb
"""
import autopath, sys, os

if '-use-snapshot' in sys.argv:
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    basedir = autopath.this_dir

    pypy_translation_snapshot_dir = os.path.join(basedir, 'pypy-translation-snapshot')

    if not os.path.isdir(pypy_translation_snapshot_dir):
        print """
    Translation will be performed on a specific revision of PyPy which lives on
    a branch. This needs to be checked out into translator/goal with:

    svn co http://codespeak.net/svn/pypy/branch/pypy-translation-snapshot
    """[1:]
        sys.exit(2)

    # override imports from pypy head with imports from pypy-translation-snapshot
    import pypy
    pypy.__path__.insert(0, pypy_translation_snapshot_dir)

    # complement imports from pypy.objspace (from pypy-translation-snapshot)
    # with pypy head objspace/
    import pypy.objspace
    pypy.objspace.__path__.append(os.path.join(autopath.pypydir, 'objspace'))

    print "imports redirected to pypy-translation-snapshot."

    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


import threading, pdb

from pypy.translator.translator import Translator
from pypy.annotation import model as annmodel
from pypy.annotation import listdef
from pypy.tool.cache import Cache
from pypy.annotation.model import SomeObject
from pypy.annotation.policy import AnnotatorPolicy
from pypy.tool.udir import udir 
from pypy.tool.ansi_print import ansi_print
from pypy.translator.pickle.main import load, save
# catch TyperError to allow for post-mortem dump
from pypy.rpython.error import TyperError

from pypy.translator.goal import query

# XXX this tries to make compiling faster
from pypy.translator.tool import cbuild
cbuild.enable_fast_compilation()

annmodel.DEBUG = False



# __________  Main  __________

def analyse(target):
    global t, entry_point, inputtypes, standalone

    policy = AnnotatorPolicy()
    if target:
        spec = target(not options['-t-lowmem'])
        try:
            entry_point, inputtypes, policy = spec
        except ValueError:
            entry_point, inputtypes = spec
        t = Translator(entry_point, verbose=True, simplifying=True)
        a = None
    else:
        # otherwise we have been loaded
        a = t.annotator
        t.frozen = False

    standalone = inputtypes is None
    if standalone:
        ldef = listdef.ListDef(None, annmodel.SomeString())
        inputtypes = [annmodel.SomeList(ldef)]

    if listen_port:
        run_async_server()
    if not options['-no-a']:
        print 'Annotating...'
        print 'with policy: %s.%s' % (policy.__class__.__module__, policy.__class__.__name__) 
        a = t.annotate(inputtypes, policy=policy)
        sanity_check_exceptblocks(t)
        lost = query.sanity_check_methods(t)
        assert not lost, "lost methods, something gone wrong with the annotation of method defs"
        print "*** No lost method defs."
        worstblocks_topten(a, 3)
        find_someobjects(t)
    if a: #and not options['-no-s']:
        print 'Simplifying...'
        a.simplify()
    if a and options['-fork']:
        from pypy.translator.goal import unixcheckpoint
        assert_rpython_mostly_not_imported() 
        unixcheckpoint.restartable_point(auto='run')
    if a and not options['-no-t']:
        print 'Specializing...'
        t.specialize(dont_simplify_again=True,
                     crash_on_first_typeerror=not options['-t-insist'])
    if not options['-no-o']:
        print 'Back-end optimizations...'
        t.backend_optimizations(ssa_form=not options['-llvm'])
    if a and options['-fork2']:
        from pypy.translator.goal import unixcheckpoint
        unixcheckpoint.restartable_point(auto='run')
    if a:
        t.frozen = True   # cannot freeze if we don't have annotations

def assert_rpython_mostly_not_imported(): 
    prefix = 'pypy.rpython.'
    oknames = ('rarithmetic memory memory.lladdress extfunctable ' 
               'lltype objectmodel error ros'.split())
    wrongimports = []
    for name, module in sys.modules.items(): 
        if module is not None and name.startswith(prefix): 
            sname = name[len(prefix):]
            for okname in oknames: 
                if sname.startswith(okname): 
                    break
            else:
                wrongimports.append(name) 
    if wrongimports: 
       raise RuntimeError("cannot fork because improper rtyper code"
                          " has already been imported: %r" %(wrongimports,))
                
def sanity_check_exceptblocks(translator):
    annotator = translator.annotator
    irreg = 0
    for graph in translator.flowgraphs.itervalues():
        et, ev = graph.exceptblock.inputargs
        s_et = annotator.binding(et, extquery=True)
        s_ev = annotator.binding(ev, extquery=True)
        if s_et:
            if s_et.knowntype == type:
                if s_et.__class__ == SomeObject:
                    if hasattr(s_et, 'is_type_of') and  s_et.is_type_of == [ev]:
                        continue
                else:
                    if s_et.__class__ == annmodel.SomePBC:
                        continue
            print "*****", graph.name, "exceptblock is not completely sane"
            irreg += 1
    if irreg == 0:
        print "*** All exceptblocks seem sane."

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

def worstblocks_topten(ann, n=10):
    h = [(count, block) for block, count in ann.reflowcounter.iteritems()]
    h.sort()
    if not h:
        return
    print
    ansi_print(',-----------------------  Top %d Most Reflown Blocks  -----------------------.' % n, 36)
    for i in range(n):
        if not h:
            break
        count, block = h.pop()
        ansi_print('                                                      #%3d: reflown %d times  |' % (i+1, count), 36)
        ann.translator.about(block)
    ansi_print("`----------------------------------------------------------------------------'", 36)
    print


def update_usession_dir(stabledir = udir.dirpath('usession')): 
    from py import path 
    try:
        if stabledir.check(dir=1): 
            for x in udir.visit(lambda x: x.check(file=1)): 
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

def run_debugger_in_thread(fn, args, cleanup=None, cleanup_args=()):
    def _run_in_thread():
        try:
            try:
                fn(*args)
                pass # for debugger to land
            except pdb.bdb.BdbQuit:
                pass
        finally:
            if cleanup is not None:
                cleanup(*cleanup_args)
    return threading.Thread(target=_run_in_thread, args=())


# graph servers

serv_start, serv_show, serv_stop, serv_cleanup = None, None, None, None

def run_async_server():
    global serv_start, serv_show, serv_stop, serv_cleanup
    from pypy.translator.tool import graphpage, graphserver
    homepage = graphpage.TranslatorPage(t)
    (serv_start, serv_show, serv_stop, serv_cleanup
     )=graphserver.run_server(homepage, port=listen_port, background=True)
    

def run_server():
    from pypy.translator.tool import graphpage
    import pygame
    from pypy.translator.tool.pygame.graphclient import get_layout
    from pypy.translator.tool.pygame.graphdisplay import GraphDisplay    

    if len(t.functions) <= huge:
        page = graphpage.TranslatorPage(t)
    else:
        page = graphpage.LocalizedCallGraphPage(t, entry_point)

    layout = get_layout(page)

    show, async_quit = layout.connexion.initiate_display, layout.connexion.quit

    display = layout.get_display()
        
    return display.run, show, async_quit, pygame.quit

def mkexename(name):
    if sys.platform == 'win32':
        name = os.path.normpath(name + '.exe')
    return name

if __name__ == '__main__':

    targetspec = 'targetpypystandalone'
    huge = 100
    load_file = None
    save_file = None

    options = {'-text': False,
               '-no-c': False,
               '-c':    False,
               '-boehm': False,
               '-no-gc': False,
               '-o':    False,
               '-llvm': False,
               '-no-mark-some-objects': False,
               '-no-a': False,
               '-no-t': False,
               '-t-insist': False,
               '-no-o': False,
               '-tcc':  False,
               '-d': False,
               '-use-snapshot' : False,
               '-load': False,
               '-save': False,
               '-fork': False,
               '-fork2': False,
               '-llinterpret': False,
               '-t-lowmem': False,
               '-batch': False,
               }
    listen_port = None
    argiter = iter(sys.argv[1:])
    for arg in argiter:
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
                if arg == '-load':
                    load_file = argiter.next()
                    loaded_dic = load(load_file)
                if arg == '-save':
                    save_file = argiter.next()
    if options['-tcc']:
        os.environ['PYPY_CC'] = 'tcc -shared -o "%s.so" "%s.c"'
    if options['-d']:
        annmodel.DEBUG = True

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

        def _mygetval(self, arg, errmsg):
            try:
                return eval(arg, self.curframe.f_globals,
                        self.curframe.f_locals)
            except:
                t, v = sys.exc_info()[:2]
                if isinstance(t, str):
                    exc_type_name = t
                else: exc_type_name = t.__name__
                if not isinstance(arg, str):
                    print '*** %s' % errmsg, "\t[%s: %s]" % (exc_type_name, v)
                else:
                    print '*** %s:' % errmsg, arg, "\t[%s: %s]" % (exc_type_name, v)
                raise

        def _getobj(self, name):
            if '.' in name:
                for pfx in self.TRYPREFIXES:
                    try:
                        return self._importobj(pfx+name)
                    except NameError:
                        pass
            try:
                return self._mygetval(name, "Not found")
            except (KeyboardInterrupt, SystemExit, MemoryError):
                raise
            except:
                pass
            return None

        def do_find(self, arg):
            """find obj [as var]
find dotted named obj, possibly using prefixing with some packages 
in pypy (see help pypyprefixes); the result is assigned to var or _."""
            objarg, var = self._parse_modif(arg)
            obj = self._getobj(objarg)
            if obj is None:
                return
            print obj
            self._setvar(var, obj)

        def _parse_modif(self, arg, modif='as'):
            var = '_'
            aspos = arg.rfind(modif+' ')
            if aspos != -1:
                objarg = arg[:aspos].strip()
                var = arg[aspos+(1+len(modif)):].strip()
            else:
                objarg = arg
            return objarg, var

        def _setvar(self, var, obj):
            self.curframe.f_locals[var] = obj

        class GiveUp(Exception):
            pass

        def _make_flt(self, expr):
            try:
                expr = compile(expr, '<filter>', 'eval')
            except SyntaxError:
                print "*** syntax: %s" % expr
                return None
            def flt(c):
                marker = object()
                try:
                    old = self.curframe.f_locals.get('cand', marker)
                    self.curframe.f_locals['cand'] = c
                    try:
                        return self._mygetval(expr, "oops")
                    except (KeyboardInterrupt, SystemExit, MemoryError):
                        raise
                    except:
                        raise self.GiveUp
                finally:
                    if old is not marker:
                        self.curframe.f_locals['cand'] = old
                    else:
                        del self.curframe.f_locals['cand']
            return flt

        def do_findclasses(self, arg):
            """findclasses expr [as var]
find annotated classes for which expr is true, cand in it referes to
the candidate class; the result list is assigned to var or _."""
            expr, var = self._parse_modif(arg)
            flt = self._make_flt(expr)
            if flt is None:
                return
            cls = []
            try:
                for c in t.annotator.getuserclasses():
                    if flt(c):
                        cls.append(c)
            except self.GiveUp:
                return
            self._setvar(var, cls)

        def do_findfuncs(self, arg):
            """findfuncs expr [as var]
find flow-graphed functions for which expr is true, cand in it referes to
the candidate function; the result list is assigned to var or _."""
            expr, var = self._parse_modif(arg)
            flt = self._make_flt(expr)
            if flt is None:
                return
            funcs = []
            try:
                for f in t.flowgraphs:
                    if flt(f):
                        funcs.append(f)
            except self.GiveUp:
                return
            self._setvar(var, funcs)

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

        def _attrs(self, arg, pr):
            arg, expr = self._parse_modif(arg, 'match')
            if expr == '_':
                expr = 'True'
            obj = self._getobj(arg)
            if obj is None:
                return
            import types
            if isinstance(obj, (type, types.ClassType)):
                obj = [obj]
            else:
                obj = list(obj)
            def longname(c):
                return "%s.%s" % (c.__module__, c.__name__) 
            obj.sort(lambda x,y: cmp(longname(x), longname(y)))
            cls = t.annotator.getuserclasses()
            flt = self._make_flt(expr)
            if flt is None:
                return
            for c in obj:
                if c in cls:
                    try:
                        attrs = [a for a in cls[c].attrs.itervalues() if flt(a)]
                    except self.GiveUp:
                        return
                    if attrs:
                        print "%s:" % longname(c)
                        pr(attrs)

        def do_attrs(self, arg):
            """attrs obj [match expr]
list annotated attrs of class obj or list of classes obj,
obj can be an expression or a dotted name
(in which case prefixing with some packages in pypy is tried (see help pypyprefixes));
expr is an optional filtering expression; cand in it refer to the candidate Attribute
information object, which has a .name and .s_value."""
            def pr(attrs):
                print " " + ' '.join([a.name for a in attrs])
            self._attrs(arg, pr)

        def do_attrsann(self, arg):
            """attrsann obj [match expr]
list with their annotation annotated attrs of class obj or list of classes obj,
obj can be an expression or a dotted name
(in which case prefixing with some packages in pypy is tried (see help pypyprefixes));
expr is an optional filtering expression; cand in it refer to the candidate Attribute
information object, which has a .name and .s_value."""
            def pr(attrs):
                for a in attrs:
                    print ' %s %s' % (a.name, a.s_value)
            self._attrs(arg, pr)

        def do_readpos(self, arg):
            """readpos obj attrname [match expr] [as var]
list the read positions of annotated attr with attrname of class obj,
obj can be an expression or a dotted name
(in which case prefixing with some packages in pypy is tried (see help pypyprefixes));
expr is an optional filtering expression; cand in it refer to the candidate read
position information, which has a .func and .block and .i;
the list of the read positions functions is set to var or _."""
            class Pos:
                def __init__(self, func, block, i):
                    self.func = func
                    self.block = block
                    self.i = i
            arg, var = self._parse_modif(arg, 'as')
            arg, expr = self._parse_modif(arg, 'match')
            if expr == '_':
                expr = 'True'
            args = arg.split()
            if len(args) != 2:
                print "*** expected obj attrname:", arg
                return
            arg, attrname = args
            # allow quotes around attrname
            if (attrname.startswith("'") and attrname.endswith("'")
                or attrname.startswith('"') and attrname.endswith('"')):
                attrname = attrname[1:-1]

            obj = self._getobj(arg)
            if obj is None:
                return
            cls = t.annotator.getuserclasses()
            if obj not in cls:
                return
            attrs = cls[obj].attrs
            if attrname not in attrs:
                print "*** bogus:", attrname
                return
            pos = attrs[attrname].read_locations
            if not pos:
                return
            flt = self._make_flt(expr)
            if flt is None:
                return
            r = {}
            try:
                for p in pos:
                    func, block, i = p
                    if flt(Pos(func, block, i)):
                        print func.__module__ or '?', func.__name__, block, i
                        if i >= 0:
                            op = block.operations[i]
                            print " ", op
                            print " ",
                            for arg in op.args:
                                print "%s: %s" % (arg, t.annotator.binding(arg)),
                            print
                        r[func] = True
            except self.GiveUp:
                return
            self._setvar(var, r.keys())
                

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

        def help_ann_other(self):
            print "other annotation related commands are: find, findclasses, findfuncs, attrs, attrsann, readpos"

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
                t.about(block)
                print '-'*60

            print >> sys.stderr
            func, args = pdb_plus_show.post_mortem, (tb,)
        else:
            print '-'*60
            print 'Done.'
            print
            func, args = pdb_plus_show.set_trace, ()
        if options['-text']:
            if options['-batch']:
                print >>sys.stderr, "batch mode, not calling interactive helpers"
            else:
                func(*args)
        else:
            if options['-batch']: 
                print >>sys.stderr, "batch mode, not calling interactive helpers"
            else:
                if serv_start:
                    start, show, stop, cleanup = serv_start, serv_show, serv_stop, serv_cleanup
                else:
                    start, show, stop, cleanup = run_server()
                pdb_plus_show.show = show
                debugger = run_debugger_in_thread(func, args, stop)
                debugger.start()
                start()
                debugger.join()
                cleanup()

    try:
        err = None
        if load_file:
            t = loaded_dic['trans']
            entry_point = t.entrypoint
            inputtypes = loaded_dic['inputtypes']
            targetspec_dic = loaded_dic['targetspec_dic']
            targetspec = loaded_dic['targetspec']
            old_options = loaded_dic['options']
            for name in '-no-a -no-t -no-o'.split():
                # if one of these options has not been set, before,
                # then the action has been done and must be prevented, now.
                if not old_options[name]:
                    if options[name]:
                        print 'option %s is implied by the load' % name
                    options[name] = True
            print "continuing Analysis as defined by %s, loaded from %s" %(
                targetspec, load_file)
            print 'options in effect:', options
            try:
                analyse(None)
            except TyperError:
                err = sys.exc_info()
        else:
            targetspec_dic = {}
            sys.path.insert(0, os.path.dirname(targetspec))
            execfile(targetspec+'.py', targetspec_dic)
            print "Analysing target as defined by %s" % targetspec
            print 'options in effect:'
            optnames = options.keys()
            optnames.sort()
            for name in optnames: 
                print '   %25s: %s' %(name, options[name])
            try:
                analyse(targetspec_dic['target'])
            except TyperError:
                err = sys.exc_info()
        print '-'*60
        if save_file:
            print 'saving state to %s' % save_file
            if err:
                print '*** this save is done after errors occured ***'
            save(t, save_file,
                 trans=t,
                 inputtypes=inputtypes,
                 targetspec=targetspec,
                 targetspec_dic=targetspec_dic,
                 options=options,
                 )
        if err:
            raise err[0], err[1], err[2]
        gcpolicy = None
        if options['-boehm']:
            from pypy.translator.c import gc
            gcpolicy = gc.BoehmGcPolicy
        if options['-no-gc']:
            from pypy.translator.c import gc
            gcpolicy = gc.NoneGcPolicy

        if options['-llinterpret']:
            def interpret():
                import py
                from pypy.rpython.llinterp import LLInterpreter
                py.log.setconsumer("llinterp operation", None)    
                interp = LLInterpreter(t.flowgraphs, t.rtyper)
                interp.eval_function(entry_point,
                                     targetspec_dic['get_llinterp_args']())
            interpret()
        elif options['-no-c']:
            print 'Not generating C code.'
        elif options['-c']:
            if options['-llvm']:
                print 'Generating LLVM code without compiling it...'
                filename = t.llvmcompile(really_compile=False,
                                      standalone=standalone)
            else:
                print 'Generating C code without compiling it...'
                filename = t.ccompile(really_compile=False,
                                      standalone=standalone, gcpolicy=gcpolicy)
            update_usession_dir()
            print 'Written %s.' % (filename,)
        else:
            if options['-llvm']:
                print 'Generating and compiling LLVM code...'
                c_entry_point = t.llvmcompile(standalone=standalone, exe_name='pypy-llvm')
            else:
                print 'Generating and compiling C code...'
                c_entry_point = t.ccompile(standalone=standalone, gcpolicy=gcpolicy)
                if standalone: # xxx fragile and messy
                    import shutil
                    exename = mkexename(c_entry_point)
                    newexename = mkexename('./pypy-c')
                    shutil.copy(exename, newexename)
                    c_entry_point = newexename
            update_usession_dir()
            if not options['-o']:
                print 'Running!'
                if standalone:
                    os.system(c_entry_point)
                else:
                    targetspec_dic['run'](c_entry_point)
    except SystemExit:
        raise
    except:
        debug(True)
        raise SystemExit(1)
    else:
        debug(False)
