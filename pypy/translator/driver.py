import sys, os

from pypy.translator.translator import TranslationContext
from pypy.translator.tool.taskengine import SimpleTaskEngine
from pypy.translator.goal import query
from pypy.annotation import model as annmodel
from pypy.annotation import listdef
from pypy.annotation import policy as annpolicy
import optparse

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("translation")
py.log.setconsumer("translation", ansi_log)


DEFAULT_OPTIONS = optparse.Values(defaults={
  'gc': 'ref',

  'thread': False, # influences GC policy

  'stackless': False,
  'debug': True,
  'insist': False,
  'backend': 'c',
  'lowmem': False,
  'fork_before': None,
  'merge_if_blocks': True
})

def taskdef(taskfunc, deps, title, new_state=None, expected_states=[], idemp=False):
    taskfunc.task_deps = deps
    taskfunc.task_title = title
    taskfunc.task_newstate = None
    taskfunc.task_expected_states = expected_states
    taskfunc.task_idempotent = idemp
    return taskfunc

# TODO:
# sanity-checks using states

class TranslationDriver(SimpleTaskEngine):

    def __init__(self, options=None, default_goal=None, disable=[],
                 exe_name=None, extmod_name=None):
        SimpleTaskEngine.__init__(self)

        self.log = log

        if options is None:
            options = DEFAULT_OPTIONS
        self.options = options
        self.exe_name = exe_name
        self.extmod_name = extmod_name

        self.done = {}

        self.disable(disable)

        if default_goal:
            default_goal, = self.backend_select_goals([default_goal])
            if default_goal in self._maybe_skip():
                default_goal = None
        
        self.default_goal = default_goal

        # expose tasks
        def expose_task(task):
            backend_goal, = self.backend_select_goals([task])
            def proc():
                return self.proceed(backend_goal)
            setattr(self, task, proc)

        if self.options.backend:
            for task in ('annotate', 'rtype', 'backendopt', 'source', 'compile', 'run', 'llinterpret'):
                expose_task(task)
        else:
            for task in self.tasks:
                expose_task(task)

    def backend_select_goals(self, goals):
        backend = self.options.backend
        l = []
        for goal in goals:
            if goal in self.tasks:
                l.append(goal)
            elif backend:
                goal = "%s_%s" % (goal, backend)
                assert goal in self.tasks
                l.append(goal)
        return l

    def disable(self, to_disable):
        self._disabled = to_disable

    def _maybe_skip(self):
        maybe_skip = []
        if self._disabled:
             for goal in  self.backend_select_goals(self._disabled):
                 maybe_skip.extend(self._depending_on_closure(goal))
        return dict.fromkeys(maybe_skip).keys()


    def setup(self, entry_point, inputtypes, policy=None, extra={}, empty_translator=None):
        standalone = inputtypes is None
        self.standalone = standalone

        if standalone:
            ldef = listdef.ListDef(None, annmodel.SomeString())
            ldef.resize()
            inputtypes = [annmodel.SomeList(ldef)]
        self.inputtypes = inputtypes

        if policy is None:
            policy = annpolicy.AnnotatorPolicy()            
        if standalone:
            policy.allow_someobjects = False
        self.policy = policy

        self.extra = extra

        if empty_translator:
            # set verbose flags
            empty_translator.flags['verbose'] = True
            translator = empty_translator
        else:
            translator = TranslationContext(verbose=True)

        self.entry_point = entry_point
        self.translator = translator


    def info(self, msg):
        log.info(msg)

    def _do(self, goal, func, *args, **kwds):
        title = func.task_title
        if goal in self.done:
            self.log.info("already done: %s" % title)
            return
        else:
            self.log.info("%s..." % title)
        res = func()
        if not func.task_idempotent:
            self.done[goal] = True
        return res

    def task_annotate(self):  
        # includes annotation and annotatation simplifications
        translator = self.translator
        policy = self.policy
        self.log.info('with policy: %s.%s' % (policy.__class__.__module__, policy.__class__.__name__))

        annmodel.DEBUG = self.options.debug
        annotator = translator.buildannotator(policy=policy)
        s = annotator.build_types(self.entry_point, self.inputtypes)
        self.sanity_check_annotation()
        if self.standalone and s.knowntype != int:
            raise Exception("stand-alone program entry point must return an "
                            "int (and not, e.g., None or always raise an "
                            "exception).")
        annotator.simplify()
        return s
    #
    task_annotate = taskdef(task_annotate, [], "Annotating&simplifying")


    def sanity_check_annotation(self):
        translator = self.translator
        irreg = query.qoutput(query.check_exceptblocks_qgen(translator))
        if not irreg:
            self.log.info("All exceptblocks seem sane")

        lost = query.qoutput(query.check_methods_qgen(translator))
        assert not lost, "lost methods, something gone wrong with the annotation of method defs"
        self.log.info("No lost method defs")

        so = query.qoutput(query.polluted_qgen(translator))
        tot = len(translator.graphs)
        percent = int(tot and (100.0*so / tot) or 0)
        if percent == 0:
            pr = self.log.info
        else:
            pr = log.WARNING
        pr("-- someobjectness %2d%% (%d of %d functions polluted by SomeObjects)" % (percent, so, tot))



    def task_rtype(self):
        opt = self.options
        rtyper = self.translator.buildrtyper()
        rtyper.specialize(dont_simplify_again=True,
                          crash_on_first_typeerror=not opt.insist)
    #
    task_rtype = taskdef(task_rtype, ['annotate'], "RTyping")

    def task_ootype(self):
        # Maybe type_system should simply be an option used in task_rtype
        opt = self.options
        rtyper = self.translator.buildrtyper(type_system="ootype")
        rtyper.specialize(dont_simplify_again=True,
                          crash_on_first_typeerror=not opt.insist)
    #
    task_ootype = taskdef(task_ootype, ['annotate'], "ootyping")

    def task_backendopt(self):
        from pypy.translator.backendopt.all import backend_optimizations
        opt = self.options
        backend_optimizations(self.translator,
                              merge_if_blocks_to_switch=opt.merge_if_blocks)
    #
    task_backendopt = taskdef(task_backendopt, 
                                        ['rtype'], "Back-end optimisations") 

    def task_stackcheckinsertion(self):
        from pypy.translator.transform import insert_ll_stackcheck
        insert_ll_stackcheck(self.translator)
        
    task_stackcheckinsertion = taskdef(
        task_stackcheckinsertion, 
        ['?backendopt', 'rtype', 'annotate'], 
        "inserting stack checks")

    def task_database_c(self):
        translator = self.translator
        opt = self.options
        if translator.annotator is not None:
            translator.frozen = True

        standalone = self.standalone
        gcpolicy = None
        if opt.gc =='boehm':
            from pypy.translator.c import gc
            gcpolicy = gc.BoehmGcPolicy
        if opt.gc =='exact_boehm':
            from pypy.translator.c import gc
            gcpolicy = gc.MoreExactBoehmGcPolicy
        if opt.gc == 'none':
            from pypy.translator.c import gc
            gcpolicy = gc.NoneGcPolicy
        if opt.gc == 'framework':
            from pypy.translator.c import gc
            gcpolicy = gc.FrameworkGcPolicy

        if standalone:
            from pypy.translator.c.genc import CStandaloneBuilder as CBuilder
        else:
            from pypy.translator.c.genc import CExtModuleBuilder as CBuilder
        cbuilder = CBuilder(self.translator, self.entry_point,
                            gcpolicy       = gcpolicy,
                            thread_enabled = getattr(opt, 'thread', False))
        cbuilder.stackless = opt.stackless
        if not standalone:     # xxx more messy
            cbuilder.modulename = self.extmod_name
        database = cbuilder.build_database()
        self.log.info("database for generating C source was created")
        self.cbuilder = cbuilder
        self.database = database
    #
    task_database_c = taskdef(task_database_c, 
                            ['stackcheckinsertion', '?backendopt', '?rtype', '?annotate'], 
                            "Creating database for generating c source")
    
    def task_source_c(self):  # xxx messy
        translator = self.translator
        cbuilder = self.cbuilder
        database = self.database
        c_source_filename = cbuilder.generate_source(database)
        self.log.info("written: %s" % (c_source_filename,))
    #
    task_source_c = taskdef(task_source_c, ['database_c'], "Generating c source")

    def create_exe(self):
        if self.exe_name is not None:
            import shutil
            exename = mkexename(self.c_entryp)
            newexename = self.exe_name % self.options.__dict__
            if '/' not in newexename and '\\' not in newexename:
                newexename = './' + newexename
            newexename = mkexename(newexename)
            shutil.copy(exename, newexename)
            self.c_entryp = newexename
        self.log.info("created: %s" % (self.c_entryp,))

    def task_compile_c(self): # xxx messy
        cbuilder = self.cbuilder
        cbuilder.compile()
        
        if self.standalone:
            self.c_entryp = cbuilder.executable_name
            self.create_exe()
        else:
            cbuilder.import_module()    
            self.c_entryp = cbuilder.get_entry_point()
    #
    task_compile_c = taskdef(task_compile_c, ['source_c'], "Compiling c source")

    def backend_run(self, backend):
        c_entryp = self.c_entryp
        standalone = self.standalone 
        if standalone:
            os.system(c_entryp)
        else:
            runner = self.extra.get('run', lambda f: f())
            runner(c_entryp)

    def task_run_c(self):
        self.backend_run('c')
    #
    task_run_c = taskdef(task_run_c, ['compile_c'], 
                         "Running compiled c source",
                         idemp=True)

    def task_llinterpret(self):
        from pypy.rpython.llinterp import LLInterpreter
        py.log.setconsumer("llinterp operation", None)
        
        translator = self.translator
        interp = LLInterpreter(translator.rtyper)
        bk = translator.annotator.bookkeeper
        graph = bk.getdesc(self.entry_point).cachedgraph(None)
        v = interp.eval_graph(graph,
                              self.extra.get('get_llinterp_args',
                                             lambda: [])())

        log.llinterpret.event("result -> %s" % v)
    #
    task_llinterpret = taskdef(task_llinterpret, 
                               ['stackcheckinsertion', '?backendopt', 'rtype'], 
                               "LLInterpreting")

    def task_source_llvm(self):
        translator = self.translator
        opts = self.options
        if translator.annotator is None:
            raise ValueError, "llvm requires annotation."

        from pypy.translator.llvm import genllvm

        # XXX Need more options for policies/llvm-backendoptions here?
        self.llvmgen = genllvm.GenLLVM(translator, self.options.gc,
                                       None, self.standalone)

        llvm_filename = self.llvmgen.gen_llvm_source(self.entry_point)
        self.log.info("written: %s" % (llvm_filename,))
    #
    task_source_llvm = taskdef(task_source_llvm, 
                               ['stackcheckinsertion', 'backendopt', 'rtype'], 
                               "Generating llvm source")

    def task_compile_llvm(self):
        gen = self.llvmgen
        if self.standalone:
            exe_name = (self.exe_name or 'testing') % self.options.__dict__
            self.c_entryp = gen.compile_llvm_source(exe_name=exe_name)
            self.create_exe()
        else:
            self.c_entryp = gen.compile_llvm_source(return_fn=True)
    #
    task_compile_llvm = taskdef(task_compile_llvm, 
                                ['source_llvm'], 
                                "Compiling llvm source")

    def task_run_llvm(self):
        self.backend_run('llvm')
    #
    task_run_llvm = taskdef(task_run_llvm, ['compile_llvm'], 
                            "Running compiled llvm source",
                            idemp=True)

    def task_source_cl(self):
        from pypy.translator.cl.gencl import GenCL
        self.gen = GenCL(self.translator, self.entry_point)
        filename = self.gen.emitfile()
        self.log.info("Wrote %s" % (filename,))
    task_source_cl = taskdef(task_source_cl, ['ootype'],
                             'Generating Common Lisp source')

    def task_compile_cl(self):
        pass
    task_compile_cl = taskdef(task_compile_cl, ['source_cl'],
                              'XXX')

    def task_run_cl(self):
        pass
    task_run_cl = taskdef(task_run_cl, ['compile_cl'],
                              'XXX')

    def task_source_squeak(self):
        from pypy.translator.squeak.gensqueak import GenSqueak
        self.gen = GenSqueak(dir, self.translator)
        filename = self.gen.gen()
        self.log.info("Wrote %s" % (filename,))
    task_source_squeak = taskdef(task_source_squeak, ['ootype'],
                             'Generating Squeak source')

    def task_compile_squeak(self):
        pass
    task_compile_squeak = taskdef(task_compile_squeak, ['source_squeak'],
                              'XXX')

    def task_run_squeak(self):
        pass
    task_run_squeak = taskdef(task_run_squeak, ['compile_squeak'],
                              'XXX')

    def proceed(self, goals):
        if not goals:
            if self.default_goal:
                goals = [self.default_goal]
            else:
                self.log.info("nothing to do")
                return
        elif isinstance(goals, str):
            goals = [goals]
        goals = self.backend_select_goals(goals)
        return self._execute(goals, task_skip = self._maybe_skip())

    def from_targetspec(targetspec_dic, options=None, args=None, empty_translator=None, 
                        disable=[],
                        default_goal=None):
        if args is None:
            args = []
        if options is None:
            options = DEFAULT_OPTIONS

        driver = TranslationDriver(options, default_goal, disable)
        target = targetspec_dic['target']
        spec = target(driver, args)

        try:
            entry_point, inputtypes, policy = spec
        except ValueError:
            entry_point, inputtypes = spec
            policy = None

        driver.setup(entry_point, inputtypes, 
                     policy=policy, 
                     extra=targetspec_dic,
                     empty_translator=empty_translator)

        return driver

    from_targetspec = staticmethod(from_targetspec)

    def prereq_checkpt_rtype(self):
        assert 'pypy.rpython.rmodel' not in sys.modules, (
            "cannot fork because the rtyper has already been imported")

    # checkpointing support
    def _event(self, kind, goal, func):
        if kind == 'pre':
            fork_before = self.options.fork_before
            if fork_before:
                fork_before, = self.backend_select_goals([fork_before])
                if not fork_before in self.done and fork_before == goal:
                    prereq = getattr(self, 'prereq_checkpt_%s' % goal, None)
                    if prereq:
                        prereq()
                    from pypy.translator.goal import unixcheckpoint
                    unixcheckpoint.restartable_point(auto='run')


def mkexename(name):
    if sys.platform == 'win32':
        name = os.path.normpath(name + '.exe')
    return name
