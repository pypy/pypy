#! /usr/bin/env python
#  
#
"""
Command-line options for translate_pypy:

    Option groups:
        Annotation:
            -m          --lowmem                Try to save memory
            -n          --no_annotations        Don't infer annotations
            -d          --debug                 record debug information
            -i          --insist                Dont't stop on first error
            
        Specialization:
            -t          --specialize            Don't specialize
            
        Backend optimisation
            -o          --optimize              Don't optimize (should have 
                                                different name)
            
        Process options:
            -f  fork1[fork2]  --fork fork1[fork2] (UNIX) Create restartable 
                                                checkpoint after annotation
                                                [,specialization]
            -l  file    --load file             load translator from file
            -s  file    --save file             save translator to file
        
        Codegeneration options:
            -g gc       --gc gc                 Garbage collector
            -b be       --backend be            Backend selector
            -c          --gencode               Don't generate code
            
        Compilation options:
            
        Run options:
            -r          --no_run                Don't run the compiled code
            -x          --batch                 Dont run interactive helpers
        Pygame options:
            -p          --pygame                Dont run pygame
            -H number   --huge number           Threshold in the number of 
                                                functions after which only a 
                                                local call graph and not a full 
                                                one is displayed
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
        spec = target(not options1.lowmem)
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
    if not options1.no_a:
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
        if 'fork1' in options1.fork:
            from pypy.translator.goal import unixcheckpoint
            assert_rpython_mostly_not_imported() 
            unixcheckpoint.restartable_point(auto='run')
    if a and options1.specialize:
        print 'Specializing...'
        t.specialize(dont_simplify_again=True,
                     crash_on_first_typeerror=not options1.insist)
    if options1.optimize and options1.backend != 'llvm':
        print 'Back-end optimizations...'
        t.backend_optimizations()
    if a and 'fork2' in options1.fork:
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

    if len(t.functions) <= options1.huge:
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
        if not options1.pygame:
            if options1.batch:
                print >>sys.stderr, "batch mode, not calling interactive helpers"
            else:
                func(*args)
        else:
            if options1.batch: 
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

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-u", "--usesnapshot", dest="snapshot", default=False,
                  action="store_true",help="use snapshot")

    parser.add_option("-f", "--fork", dest="fork", default=[],
                  action="append",help="(UNIX) Create restartable checkpoint after annotation,specialization")
    parser.add_option("-m", "--lowmem", dest="lowmem", default=False,
                  action="store_true",help="Try to save memory")
    parser.add_option("-t", "--specialize", dest="specialize", default=True,
                  action="store_false",help="Don't specialize")
    parser.add_option("-o", "--optimize", dest="optimize", default=True,
                  action="store_false",help="Don't do backend optimizations")
    parser.add_option("-n", "--no_annotations", dest="no_a", default=False,
                  action="store_true", help="Don't infer annotations")    
    parser.add_option("-l", "--load", dest="loadfile",
                  help="load translator from file")
    parser.add_option("-s", "--save", dest="savefile",
                  help="save translator to file")    
    parser.add_option("-i", "--insist", dest="insist", default=True,
                  action="store_true", help="Don't stop on first error")    
    parser.add_option("-d", "--debug", dest="debug", default=False,
                  action="store_true", help="record debug information")    

    parser.add_option("-g", "--gc", dest="gc", default="ref",
                  help="choose garbage collector (ref, boehm, none)")    
    parser.add_option("-b", "--backend", dest="backend", default='c',
                  help="choose backend (c, llvm, llinterpret)")    
    parser.add_option("-c", "--gencode", dest="really_compile", default=True,
                  action="store_false",help="Don't generate C code")

    parser.add_option("-r", "--no_run", dest="run", default=True,
                  action="store_false",help="compile but don't run")    
    parser.add_option("-H", "--huge", dest="huge", type="int",
                  help="Threshold in the number of functions after which only a local call\
              graph and not a full one is displayed")
    parser.add_option("-p", "--pygame", dest="pygame", default=True,
                  action="store_false", help="Don't start Pygame viewer")    
    parser.add_option("-x", "--batch", dest="batch", default=False,
                  action="store_true",help="Don't use interactive helpers, like pdb")
    (options1, args) = parser.parse_args()
    
    argiter = iter(args) #sys.argv[1:])
    for arg in argiter:
        try:
            listen_port = int(arg)
        except ValueError:
            if os.path.isfile(arg+'.py'):
                assert not os.path.isfile(arg), (
                    "ambiguous file naming, please rename %s" % arg)
                targetspec = arg
            elif os.path.isfile(arg) and arg.endswith('.py'):
                targetspec = arg[:-3]

    options = {}
    for opt in parser.option_list[1:]:
        options[opt.dest] = getattr(options1,opt.dest)
##    if options['-tcc']:
##        os.environ['PYPY_CC'] = 'tcc -shared -o "%s.so" "%s.c"'
    if options1.debug:
        annmodel.DEBUG = True
    try:
        err = None
        if options1.loadfile:
            loaded_dic = load(options1.filename)
            t = loaded_dic['trans']
            entry_point = t.entrypoint
            inputtypes = loaded_dic['inputtypes']
            targetspec_dic = loaded_dic['targetspec_dic']
            targetspec = loaded_dic['targetspec']
            old_options = loaded_dic['options']
            for name in 'no_a specialize optimize'.split():
                # if one of these options has not been set, before,
                # then the action has been done and must be prevented, now.
                if not old_options[name]:
                    if options[name]:
                        print 'option %s is implied by the load' % name
                    options[name] = True
            print "continuing Analysis as defined by %s, loaded from %s" %(
                targetspec, options1.loadname)
            targetspec_dic['target'] = None
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
        if options1.savefile:
            print 'saving state to %s' % options1.savefile
            if err:
                print '*** this save is done after errors occured ***'
            save(t, options1.savefile,
                 trans=t,
                 inputtypes=inputtypes,
                 targetspec=targetspec,
                 targetspec_dic=targetspec_dic,
                 options=options,
                 )
        if err:
            raise err[0], err[1], err[2]
        if options1.backend == 'c': #XXX probably better to supply gcpolicy as string to the backends
            gcpolicy = None
            if options1.gc =='boehm':
                from pypy.translator.c import gc
                gcpolicy = gc.BoehmGcPolicy
            if options1.gc == 'none':
                from pypy.translator.c import gc
                gcpolicy = gc.NoneGcPolicy
        elif options1.backend == 'llvm':
            gcpolicy = options1.gc

        if options1.backend == 'llinterpret':
            def interpret():
                import py
                from pypy.rpython.llinterp import LLInterpreter
                py.log.setconsumer("llinterp operation", None)    
                interp = LLInterpreter(t.flowgraphs, t.rtyper)
                interp.eval_function(entry_point,
                                     targetspec_dic['get_llinterp_args']())
            interpret()
        #elif options1.gencode:
        #    print 'Not generating C code.'
        else:
            print 'Generating %s %s code...' %(options1.really_compile and "and compiling " or "",options1.backend)
            keywords = {'really_compile' : options1.really_compile, 
                        'standalone' : standalone, 
                        'gcpolicy' : gcpolicy}
            c_entry_point = t.compile(options1.backend, **keywords)
                             
            if standalone and options1.backend == 'c': # xxx fragile and messy
                import shutil
                exename = mkexename(c_entry_point)
                newexename = mkexename('./pypy-c')
                shutil.copy(exename, newexename)
                c_entry_point = newexename
            update_usession_dir()
            print 'Written %s.' % (c_entry_point,)
            if options1.run:
                print 'Running!'
                if standalone:
                    os.system(c_entry_point)
                else:
                    targetspec_dic['run'](c_entry_point)
    except SystemExit:
        raise
    except:
        if t: debug(True)
        raise SystemExit(1)
    else:
        if t: debug(False)
