import sys, os

from pypy.translator.translator import TranslationContext
from pypy.translator.tool.taskengine import SimpleTaskEngine
from pypy.translator.goal import query
from pypy.annotation import model as annmodel
from pypy.annotation.listdef import s_list_of_strings
from pypy.annotation import policy as annpolicy
import optparse

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("translation")
py.log.setconsumer("translation", ansi_log)


DEFAULT_OPTIONS = {
  'gc': 'ref',
  'cc': None,

  'thread': False, # influences GC policy

  'stackless': False,
  'debug': True,
  'insist': False,
  'backend': 'c',
  'type_system': None,
  'lowmem': False,
  'fork_before': None,
  'raisingop2direct_call' : False,
  'merge_if_blocks': True
}

_default_options = optparse.Values(defaults=DEFAULT_OPTIONS)

def taskdef(taskfunc, deps, title, new_state=None, expected_states=[], idemp=False):
    taskfunc.task_deps = deps
    taskfunc.task_title = title
    taskfunc.task_newstate = None
    taskfunc.task_expected_states = expected_states
    taskfunc.task_idempotent = idemp
    return taskfunc

# TODO:
# sanity-checks using states

_BACKEND_TO_TYPESYSTEM = {
    'c': 'lltype',
    'llvm': 'lltype'
}

def backend_to_typesystem(backend):
    return _BACKEND_TO_TYPESYSTEM.get(backend, 'ootype')

class TranslationDriver(SimpleTaskEngine):

    def __init__(self, options=None, default_goal=None, disable=[],
                 exe_name=None, extmod_name=None):
        SimpleTaskEngine.__init__(self)

        self.log = log

        if options is None:
            options = _default_options
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

        self.exposed = []

        # expose tasks
        def expose_task(task, backend_goal=None):
            if backend_goal is None:
                backend_goal = task
            def proc():
                return self.proceed(backend_goal)
            self.exposed.append(task)
            setattr(self, task, proc)

        backend, ts = self.get_backend_and_type_system()
        for task in self.tasks:
            explicit_task = task
            parts = task.split('_')
            if len(parts) == 1:
                if task in ('annotate'):
                    expose_task(task)
            else:
                task, postfix = parts
                if task in ('rtype', 'backendopt', 'llinterpret'):
                    if ts:
                        if ts == postfix:
                            expose_task(task, explicit_task)                        
                    else:
                        expose_task(explicit_task)
                elif task in ('source', 'compile', 'run'):
                    if backend:
                        if backend == postfix:
                            expose_task(task, explicit_task)
                    elif ts:
                        if ts == backend_to_typesystem(postfix):
                            expose_task(explicit_task)
                    else:
                        expose_task(explicit_task)

    def get_backend_and_type_system(self):
        type_system = None
        backend = None
        opts = self.options
        if opts.type_system:
            type_system = opts.type_system
        if opts.backend:
            backend = opts.backend
            ts = backend_to_typesystem(backend)
            if type_system:
                if ts != type_system:
                    raise ValueError, ("incosistent type-system and backend:"
                                       " %s and %s" % (type_system, backend))
            else:
                type_system = ts
        return backend, type_system

    def backend_select_goals(self, goals):
        backend, ts = self.get_backend_and_type_system()
        postfixes = [''] + ['_'+p for p in (backend, ts) if p]
        l = []
        for goal in goals:
            for postfix in postfixes:
                cand = "%s%s" % (goal, postfix)
                if cand in self.tasks:
                    new_goal = cand
                    break
            else:
                raise Exception, "cannot infer complete goal from: %r" % goal 
            l.append(new_goal)
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
            inputtypes = [s_list_of_strings]
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



    def task_rtype_lltype(self):
        opt = self.options
        rtyper = self.translator.buildrtyper(type_system='lltype')
        rtyper.specialize(dont_simplify_again=True,
                          crash_on_first_typeerror=not opt.insist)
    #
    task_rtype_lltype = taskdef(task_rtype_lltype, ['annotate'], "RTyping")
    RTYPE = 'rtype_lltype'

    def task_rtype_ootype(self):
        # Maybe type_system should simply be an option used in task_rtype
        opt = self.options
        rtyper = self.translator.buildrtyper(type_system="ootype")
        rtyper.specialize(dont_simplify_again=True,
                          crash_on_first_typeerror=not opt.insist)
    #
    task_rtype_ootype = taskdef(task_rtype_ootype, ['annotate'], "ootyping")
    OOTYPE = 'rtype_ootype'

    def task_backendopt_lltype(self):
        from pypy.translator.backendopt.all import backend_optimizations
        opt = self.options
        backend_optimizations(self.translator,
                              raisingop2direct_call_all=opt.raisingop2direct_call,
                              merge_if_blocks_to_switch=opt.merge_if_blocks)
    #
    task_backendopt_lltype = taskdef(task_backendopt_lltype, 
                                        [RTYPE], "Back-end optimisations")
    BACKENDOPT = 'backendopt_lltype'

    def task_stackcheckinsertion_lltype(self):
        from pypy.translator.transform import insert_ll_stackcheck
        insert_ll_stackcheck(self.translator)
        
    task_stackcheckinsertion_lltype = taskdef(
        task_stackcheckinsertion_lltype, 
        ['?'+BACKENDOPT, RTYPE, 'annotate'], 
        "inserting stack checks")
    STACKCHECKINSERTION = 'stackcheckinsertion_lltype'

    def task_database_c(self):
        translator = self.translator
        opt = self.options
        if translator.annotator is not None:
            translator.frozen = True

        standalone = self.standalone

        if standalone:
            from pypy.translator.c.genc import CStandaloneBuilder as CBuilder
        else:
            from pypy.translator.c.genc import CExtModuleBuilder as CBuilder
        cbuilder = CBuilder(self.translator, self.entry_point,
                            gcpolicy       = opt.gc,
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
                            [STACKCHECKINSERTION, '?'+BACKENDOPT, RTYPE, '?annotate'], 
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

    def task_llinterpret_lltype(self):
        from pypy.rpython.llinterp import LLInterpreter
        py.log.setconsumer("llinterp operation", None)
        
        translator = self.translator
        interp = LLInterpreter(translator.rtyper)
        bk = translator.annotator.bookkeeper
        graph = bk.getdesc(self.entry_point).getuniquegraph()
        v = interp.eval_graph(graph,
                              self.extra.get('get_llinterp_args',
                                             lambda: [])())

        log.llinterpret.event("result -> %s" % v)
    #
    task_llinterpret_lltype = taskdef(task_llinterpret_lltype, 
                                      [STACKCHECKINSERTION, '?'+BACKENDOPT, RTYPE], 
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
                               [STACKCHECKINSERTION, BACKENDOPT, RTYPE], 
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
    task_source_cl = taskdef(task_source_cl, [OOTYPE],
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
    task_source_squeak = taskdef(task_source_squeak, [OOTYPE],
                             'Generating Squeak source')

    def task_compile_squeak(self):
        pass
    task_compile_squeak = taskdef(task_compile_squeak, ['source_squeak'],
                              'XXX')

    def task_run_squeak(self):
        pass
    task_run_squeak = taskdef(task_run_squeak, ['compile_squeak'],
                              'XXX')

    def task_source_js(self):
        from pypy.translator.js.js import JS
        self.gen = JS(self.translator, functions=[self.entry_point],
                      stackless=self.options.stackless)
        filename = self.gen.write_source()
        self.log.info("Wrote %s" % (filename,))
    task_source_js = taskdef(task_source_js, 
                        [OOTYPE],
                        'Generating Javascript source')

    def task_compile_js(self):
        pass
    task_compile_js = taskdef(task_compile_js, ['source_js'],
                              'Skipping Javascript compilation')

    def task_run_js(self):
        pass
    task_run_js = taskdef(task_run_js, ['compile_js'],
                              'Please manually run the generated code')

    def task_source_cli(self):
        from pypy.translator.cli.gencli import GenCli
        from pypy.translator.cli.entrypoint import get_entrypoint
        from pypy.tool.udir import udir

        entry_point_graph = self.translator.graphs[0]
        self.gen = GenCli(udir, self.translator, get_entrypoint(entry_point_graph))
        filename = self.gen.generate_source()
        self.log.info("Wrote %s" % (filename,))
    task_source_cli = taskdef(task_source_cli, [OOTYPE],
                             'Generating CLI source')

    def task_compile_cli(self):
        from pypy.translator.cli.test.runtest import CliFunctionWrapper
        filename = self.gen.build_exe()
        self.c_entryp = CliFunctionWrapper(filename)
        self.log.info("Compiled %s" % filename)
    task_compile_cli = taskdef(task_compile_cli, ['source_cli'],
                              'Compiling CLI source')

    def task_run_cli(self):
        pass
    task_run_cli = taskdef(task_run_cli, ['compile_cli'],
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
            options = _default_options

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
    prereq_checkpt_rtype_lltype = prereq_checkpt_rtype
    prereq_checkpt_rtype_ootype = prereq_checkpt_rtype    

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
