import sys, os

from pypy.translator.translator import Translator
from pypy.translator.tool.taskengine import SimpleTaskEngine
from pypy.translator.goal import query
from pypy.annotation import model as annmodel
from pypy.annotation import listdef
from pypy.annotation import policy as annpolicy
import optparse

DEFAULT_OPTIONS = optparse.Values(defaults={
  'gc': 'ref',
  'debug': True,
  'insist': False,
  'backend': 'c',
  'lowmem': False,
})

def taskdef(taskfunc, deps, title, new_state=None, expected_states=[]):
    taskfunc.task_deps = deps
    taskfunc.task_title = title
    taskfunc.task_newstate = None
    taskfunc.task_expected_states = expected_states
    return taskfunc

# TODO:
# run is idempotent
# sanity-checks using states

class TranslationDriver(SimpleTaskEngine):

    def __init__(self, translator, inputtypes, policy=None, options=None,
                 runner=None, disable=[], default_goal = None):
        SimpleTaskEngine.__init__(self)

        self.translator = translator

        standalone = inputtypes is None
        if standalone:
            ldef = listdef.ListDef(None, annmodel.SomeString())
            inputtypes = [annmodel.SomeList(ldef)]
        self.inputtypes = inputtypes

        if policy is None:
            policy = annpolicy.AnnotatorPolicy()            
        self.policy = policy
        if options is None:
            options = DEFAULT_OPTIONS
        self.options = options
        self.standalone = standalone

        if runner is None and not standalone:
            def runner(f):
                f()
        self.runner = runner

        self.done = {}

        maybe_skip = []
        for goal in self.backend_select_goals(disable):
            maybe_skip.extend(self._depending_on_closure(goal))
        self.maybe_skip = dict.fromkeys(maybe_skip).keys()

        if default_goal:
            default_goal, = self.backend_select_goals([default_goal])
            if default_goal in self.maybe_skip:
                default_goal = None
        
        self.default_goal = default_goal

        # expose tasks
        def expose_task(task):
            backend_goal, = self.backend_select_goals([task])
            def proc():
                self.proceed(backend_goal)
            setattr(self, task, proc)

        for task in ('annotate', 'rtype', 'backendopt', 'source', 'compile', 'run'):
            expose_task(task)
            
    def backend_select_goals(self, goals):
        backend = self.options.backend
        assert backend
        l = []
        for goal in goals:
            if goal in self.tasks:
                l.append(goal)
            else:
                goal = "%s_%s" % (goal, backend)
                assert goal in self.tasks
                l.append(goal)
        return l

    def info(self, msg):
        print msg

    def _do(self, goal, func, *args, **kwds):
        title = func.task_title
        if goal in self.done:
            self.info("already done: %s" % title)
            return
        else:
            self.info("%s..." % title)
        func()
        self.done[goal] = True


    def task_annotate(self):  
        # includes annotation and annotatation simplifications
        translator = self.translator
        policy = self.policy
        self.info('with policy: %s.%s' % (policy.__class__.__module__, policy.__class__.__name__))

        annmodel.DEBUG = self.options.debug
        annotator = translator.annotate(self.inputtypes, policy=policy)
        sanity_check_annotation(translator)
        annotator.simplify()        
    #
    task_annotate = taskdef(task_annotate, [], "Annotating&simplifying")

    def task_rtype(self):
        opt = self.options
        self.translator.specialize(dont_simplify_again=True,
                                   crash_on_first_typeerror=not opt.insist)
    #
    task_rtype = taskdef(task_rtype, ['annotate'], "RTyping")

    def task_backendopt(self):
        opt = self.options
        self.translator.backend_optimizations(ssa_form=opt.backend != 'llvm')
    #
    task_backendopt = taskdef(task_backendopt, 
                                        ['rtype'], "Back-end optimisations") 

    def task_source_c(self):  # xxx messy
        translator = self.translator
        opt = self.options
        if translator.annotator is not None:
            translator.frozen = True

        standalone = self.standalone
        gcpolicy = None
        if opt.gc =='boehm':
            from pypy.translator.c import gc
            gcpolicy = gc.BoehmGcPolicy
        if opt.gc == 'none':
            from pypy.translator.c import gc
            gcpolicy = gc.NoneGcPolicy

        cbuilder = translator.cbuilder(standalone=standalone, gcpolicy=gcpolicy)
        c_source_filename = cbuilder.generate_source()
        self.cbuilder = cbuilder
    #
    task_source_c = taskdef(task_source_c, 
                            ['?backendopt', '?rtype', '?annotate'], 
                            "Generating c source")

    def task_compile_c(self): # xxx messy
        cbuilder = self.cbuilder
        cbuilder.compile()

        if self.standalone:
            self.c_entryp = cbuilder.executable_name
            self.info("written: %s" % (self.c_entryp,))
        else:
            cbuilder.import_module()    
            self.c_entryp = cbuilder.get_entry_point()
    #
    task_compile_c = taskdef(task_compile_c, ['source_c'], "Compiling c source")

    def backend_run(self, backend): # xxx mess
        c_entryp = self.c_entryp
        standalone = self.standalone 
        if standalone: # xxx fragile and messy
            import shutil
            exename = mkexename(c_entryp)
            newexename = mkexename('./pypy-' + backend)
            shutil.copy(exename, newexename)
            c_entryp = newexename
        if standalone:
            os.system(c_entryp)
        else:
            self.runner(c_entryp)

    def task_run_c(self):
        self.backend_run('c')
    #
    task_run_c = taskdef(task_run_c, ['compile_c'], "Running compiled c source")

    def task_llinterpret(self):
        raise NotImplementedError, "llinterpret" # xxx
    #
    task_llinterpret = taskdef(task_llinterpret, 
                               ['?backendopt', 'rtype'], 
                               "LLInterpeting")

    def task_source_llvm(self):
        raise NotImplementedError, "source_llvm" # xxx
    #
    task_source_llvm = taskdef(task_source_llvm, 
                               ['backendopt', 'rtype'], 
                               "Generating llvm source")

    def task_compile_llvm(self):
        raise NotImplementedError, "compile_llvm" # xxx
    #
    task_compile_llvm = taskdef(task_compile_llvm, 
                                ['backendopt', 'rtype'], 
                                "Compiling llvm source")

    def task_run_llvm(self):
        self.backend_run('llvm')
    #
    task_run_llvm = taskdef(task_run_llvm, ['compile_llvm'], 
                            "Running compiled llvm source")

    def proceed(self, goals):
        if not goals:
            if self.default_goal:
                goals = [self.default_goal]
            else:
                self.info("nothing to do")
                return
        elif isinstance(goals, str):
            goals = [goals]
        goals = self.backend_select_goals(goals)
        self._execute(goals, task_skip = self.maybe_skip)

    def from_targetspec(targetspec_dic, options=None, args=None, empty_translator=None, 
                        disable=[],
                        default_goal=None):
        if args is None:
            args = []
        if options is None:
            options = DEFAULT_OPTIONS.copy()
            
        target = targetspec_dic['target']        
        spec = target(options, args)
        try:
            entry_point, inputtypes, policy = spec
        except ValueError:
            entry_point, inputtypes = spec
            policy = None

        if empty_translator:
            # re-initialize it
            empty_translator.__init__(entry_point, verbose=True, simplifying=True)
            translator = empty_translator
        else:
            translator = Translator(entry_point, verbose=True, simplifying=True)
            
        driver = TranslationDriver(translator, inputtypes,
                                   policy, options, targetspec_dic.get('run'),
                                   disable=disable,
                                   default_goal = default_goal)

        return driver

    from_targetspec = staticmethod(from_targetspec)


# __________ helpers

def sanity_check_annotation(t):
    irreg = query.qoutput(query.check_exceptblocks_qgen(t))
    if not irreg:
        print "++ All exceptblocks seem sane"

    lost = query.qoutput(query.check_methods_qgen(t))
    assert not lost, "lost methods, something gone wrong with the annotation of method defs"
    print "++ No lost method defs"

    so = query.qoutput(query.polluted_qgen(t))
    tot = len(t.flowgraphs)
    percent = int(tot and (100.0*so / tot) or 0)
    print "-- someobjectness %2d%% (%d of %d functions polluted by SomeObjects)" % (percent, so, tot)

from pypy.translator.tool.util import mkexename
