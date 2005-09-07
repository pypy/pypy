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

   -no-a      Don't infer annotations, just translate everything
   -no-t      Don't type-specialize the graph operations with the C typer
   -t-insist  Specialize should not stop at the first error
   -no-o      Don't do backend-oriented optimizations
   -fork      (UNIX) Create a restartable checkpoint after annotation
   -fork2     (UNIX) Create a restartable checkpoint after specializing
   -t-lowmem  try to save as much memory as possible, since many computers
              tend to have less than a gigabyte of memory (512 MB is typical).
              Currently, we avoid to use geninterplevel, which creates a lot
              of extra blocks, but gains only some 10-20 % of speed, because
              we are still lacking annotation of applevel code.
   -d         Enable recording of annotator debugging information

   -no-c      Don't generate the C code
   -llvm      Use LLVM instead of C
   -c         Generate the C code, but don't compile it
   -boehm     Use the Boehm collector when generating C code
   -no-gc     Experimental: use no GC and no refcounting at all
   -o         Generate and compile the C code, but don't run it
   -tcc       Equivalent to the envvar PYPY_CC='tcc -shared -o "%s.so" "%s.c"'
                  -- http://fabrice.bellard.free.fr/tcc/
   -llinterpret
              interprets the flow graph after rtyping it

   -text      Don't start the Pygame viewer
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
from pypy.translator.tool.util import worstblocks_topten, find_someobjects 
from pypy.translator.tool.util import sanity_check_exceptblocks
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
    if not options['-no-o'] and not options['-llvm']:
        print 'Back-end optimizations...'
        t.backend_optimizations()
    if a and options['-fork2']:
        from pypy.translator.goal import unixcheckpoint
        unixcheckpoint.restartable_point(auto='run')
    if a:
        t.frozen = True   # cannot freeze if we don't have annotations

def assert_rpython_mostly_not_imported(): 
    prefix = 'pypy.rpython.'
    oknames = ('rarithmetic memory memory.lladdress extfunctable ' 
               'lltype objectmodel error'.split())
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
    
    def debug(got_error):
        from pypy.translator.tool.pdbplus import PdbPlusShow
        from pypy.translator.tool.pdbplus import run_debugger_in_thread
        
        pdb_plus_show = PdbPlusShow(t) # need a translator to support extended commands
        
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
                pdb_plus_show.install_show(show)
                debugger = run_debugger_in_thread(func, args, stop)
                debugger.start()
                start()
                debugger.join()
                cleanup()

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
            targetspec_dic['target'] = None
##            print 'options in effect:', options
##            try:
##                analyse(None)
##            except TyperError:
##                err = sys.exc_info()
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
