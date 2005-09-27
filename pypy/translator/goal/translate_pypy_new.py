#! /usr/bin/env python
#  
"""
Command-line options for translate_pypy:

    See below
"""

opts = {
    'Annotation':[
        ['-m', '--lowmem', 'Try to save memory', [True,False], False],
        ['-n', '--no_annotations', "Don't infer annotations", [True,False], False],
        ['-d', '--debug', 'record debug information', [True,False], False],
        ['-i', '--insist', "Dont't stop on first error", [True,False], True]], 
            
    'Specialization':[
        ['-t', '--specialize', "Don't specialize", [True,False], True]],
            
    'Backend optimisation': [
        ['-o', '--optimize', "Don't optimize (should have different name)", 
                                                             [True,False], True ]],
                    
    'Process options':[
        ['-f', '--fork', 
               "(UNIX) Create restartable checkpoint after annotation [,specialization]",
                            [['fork1','fork2']], [] ],
        ['-l', '--load', "load translator from file", [str], ''],
        ['-s', '--save', "save translator to file", [str], '']], 
        
    'Codegeneration options':[
        ['-g', '--gc', 'Garbage collector', ['ref', 'boehm','none'], 'boehm'], 
        ['-b', '--backend', 'Backend selector', ['c','llvm'],'c'], 
        ['-w', '--gencode', "Don't generate code", [True,False], True], 
        ['-c', '--compile', "Don't compile generated code", [True,False], True]], 
            
    'Compilation options':[],
            
    'Run options':[
        ['-r', '--run', "Don't run the compiled code", [True,False], True], 
        ['-x', '--batch', "Dont run interactive helpers", [True,False], False]],
    'Pygame options':[
        ['-p', '--pygame', "Dont run pygame", [True,False], True], 
        ['-H', '--huge',
           "Threshold in the number of functions after which only a local call graph and not a full one is displayed", [int], 0 ]]}
           
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
from pypy.annotation.policy import AnnotatorPolicy
from pypy.translator.pickle.main import load, save
# catch TyperError to allow for post-mortem dump
from pypy.rpython.error import TyperError

from pypy.translator.goal import query

# XXX this tries to make compiling faster
from pypy.translator.tool import cbuild
cbuild.enable_fast_compilation()
from pypy.translator.tool.util import find_someobjects 
from pypy.translator.tool.util import sanity_check_exceptblocks, update_usession_dir
from pypy.translator.tool.util import assert_rpython_mostly_not_imported, mkexename

annmodel.DEBUG = False



# __________  Main  __________

def analyse(t, inputtypes):

    standalone = inputtypes is None
    if standalone:
        ldef = listdef.ListDef(None, annmodel.SomeString())
        inputtypes = [annmodel.SomeList(ldef)]
    
    if not cmd_line_opt.no_annotations:
        print 'Annotating...'
        print 'with policy: %s.%s' % (policy.__class__.__module__, policy.__class__.__name__) 
        a = t.annotate(inputtypes, policy=policy)
        sanity_check_exceptblocks(t)
        lost = query.sanity_check_methods(t)
        assert not lost, "lost methods, something gone wrong with the annotation of method defs"
        print "*** No lost method defs."
        find_someobjects(t)
    if a: #and not options['-no-s']:
        print 'Simplifying...'
        a.simplify()
        if 'fork1' in cmd_line_opt.fork:
            from pypy.translator.goal import unixcheckpoint
            assert_rpython_mostly_not_imported() 
            unixcheckpoint.restartable_point(auto='run')
    if a and cmd_line_opt.specialize:
        print 'Specializing...'
        t.specialize(dont_simplify_again=True,
                     crash_on_first_typeerror=not cmd_line_opt.insist)
    if cmd_line_opt.optimize:
        print 'Back-end optimizations...'
        t.backend_optimizations(ssa_form=cmd_line_opt.backend != 'llvm')
    if a and 'fork2' in cmd_line_opt.fork:
        from pypy.translator.goal import unixcheckpoint
        unixcheckpoint.restartable_point(auto='run')
    if a:
        t.frozen = True   # cannot freeze if we don't have annotations
    return  standalone

# graph servers

serv_start, serv_show, serv_stop, serv_cleanup = None, None, None, None

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
                t.about(block)
                print '-'*60

            print >> sys.stderr
            func, args = pdb_plus_show.post_mortem, (tb,)
        else:
            print '-'*60
            print 'Done.'
            print
            func, args = pdb_plus_show.set_trace, ()
        if not cmd_line_opt.pygame:
            if cmd_line_opt.batch:
                print >>sys.stderr, "batch mode, not calling interactive helpers"
            else:
                func(*args)
        else:
            if cmd_line_opt.batch: 
                print >>sys.stderr, "batch mode, not calling interactive helpers"
            else:
                if serv_start:
                    start, show, stop, cleanup = serv_start, serv_show, serv_stop, serv_cleanup
                else:
                    from pypy.translator.tool.pygame.server import run_translator_server
                    start, show, stop, cleanup = run_translator_server(t, entry_point, cmd_line_opt)
                pdb_plus_show.install_show(show)
                debugger = run_debugger_in_thread(func, args, stop)
                debugger.start()
                start()
                debugger.join()
                cleanup()

    from optparse import OptionParser
    parser = OptionParser()
    for group in opts:
        for option in opts[group]:
            if option[-1] in [True,False]:
                if option[-1] == True: 
                    action = "store_false"
                else:
                    action = "store_true"
                parser.add_option(option[0],option[1], default=option[-1], 
                dest=option[1].lstrip('--'), help=option[2], action=action)
            elif type(option[-2][0]) == list:
                parser.add_option(option[0],option[1], default=option[-1], 
                dest=option[1].lstrip('--'), help=option[2], action="append")
            else:
                parser.add_option(option[0],option[1], default=option[-1], 
                dest=option[1].lstrip('--'), help=option[2])
    
    (cmd_line_opt, args) = parser.parse_args()
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
    t = None
    options = {}
    for opt in parser.option_list[1:]:
        options[opt.dest] = getattr(cmd_line_opt,opt.dest)
        if options.get('gc') == 'boehm':
            options['-boehm'] = True
##    if options['-tcc']:
##        os.environ['PYPY_CC'] = 'tcc -shared -o "%s.so" "%s.c"'
    if cmd_line_opt.debug:
        annmodel.DEBUG = True
    try:
        err = None
        if cmd_line_opt.load:
            loaded_dic = load(cmd_line_opt.load)
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
                targetspec, cmd_line_opt.loadname)
            targetspec_dic['target'] = None
        else:
            targetspec_dic = {}
            sys.path.insert(0, os.path.dirname(targetspec))
            execfile(targetspec+'.py', targetspec_dic)
            print "Analysing target as defined by %s" % targetspec
            if targetspec_dic.get('options', None):
                targetspec_dic['options'].update(options)
                options = targetspec_dic['options']
                print options,targetspec_dic['options']
        print 'options in effect:'
        optnames = options.keys()
        optnames.sort()
        for name in optnames: 
            print '   %25s: %s' %(name, options[name])

        policy = AnnotatorPolicy()
        target = targetspec_dic['target']
        if target:
            spec = target(not cmd_line_opt.lowmem)
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
        if listen_port:
            from pypy.translator.tool.graphserver import run_async_server
            serv_start, serv_show, serv_stop, serv_cleanup = run_async_server(t, listen_port)
        try:
            standalone = analyse(t, inputtypes)
        except TyperError:
            err = sys.exc_info()
        print '-'*60
        if cmd_line_opt.save:
            print 'saving state to %s' % cmd_line_opt.save
            if err:
                print '*** this save is done after errors occured ***'
            save(t, cmd_line_opt.save,
                 trans=t,
                 inputtypes=inputtypes,
                 targetspec=targetspec,
                 targetspec_dic=targetspec_dic,
                 options=options,
                 )
        if err:
            raise err[0], err[1], err[2]
        if cmd_line_opt.backend == 'c': #XXX probably better to supply gcpolicy as string to the backends
            gcpolicy = None
            if cmd_line_opt.gc =='boehm':
                from pypy.translator.c import gc
                gcpolicy = gc.BoehmGcPolicy
            if cmd_line_opt.gc == 'none':
                from pypy.translator.c import gc
                gcpolicy = gc.NoneGcPolicy
        elif cmd_line_opt.backend == 'llvm':
            gcpolicy = cmd_line_opt.gc

        if cmd_line_opt.backend == 'llinterpret':
            def interpret():
                import py
                from pypy.rpython.llinterp import LLInterpreter
                py.log.setconsumer("llinterp operation", None)    
                interp = LLInterpreter(t.flowgraphs, t.rtyper)
                interp.eval_function(entry_point,
                                     targetspec_dic['get_llinterp_args']())
            interpret()
        elif not cmd_line_opt.gencode:
            print 'Not generating C code.'
        else:
            print 'Generating %s %s code...' %(cmd_line_opt.compile and "and compiling" or "",cmd_line_opt.backend)
            keywords = {'really_compile' : cmd_line_opt.compile, 
                        'standalone' : standalone, 
                        'gcpolicy' : gcpolicy}
            c_entry_point = t.compile(cmd_line_opt.backend, **keywords)
                             
            if standalone: # xxx fragile and messy
                import shutil
                exename = mkexename(c_entry_point)
                newexename = mkexename('./pypy-' + cmd_line_opt.backend)
                shutil.copy(exename, newexename)
                c_entry_point = newexename
            update_usession_dir()
            print 'Written %s.' % (c_entry_point,)
            if cmd_line_opt.run:
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
