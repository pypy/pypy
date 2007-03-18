"""
A translation target:   python pypy/translator/goal/translate.py targetjit
"""
from pypy.translator.goal import targetpypystandalone
from pypy.translator.driver import TranslationDriver, taskdef
from pypy.annotation.pairtype import extendabletype

class __extend__(TranslationDriver):
    __metaclass__ = extendabletype

    def task_prehannotatebackendopt(self):
        from pypy.translator.backendopt.all import backend_optimizations
        backend_optimizations(self.translator,
                              inline_threshold=0,
                              merge_if_blocks=False,
                              constfold=True,
                              remove_asserts=True)
    #
    task_prehannotatebackendopt = taskdef(task_prehannotatebackendopt,
                                         [TranslationDriver.RTYPE],
                                         "Backendopt before Hint-annotate")
    def task_hintannotate(self):
        from pypy.jit.goal import jitstep
        jitstep.hintannotate(self)
    #
    task_hintannotate = taskdef(task_hintannotate,
                                ['prehannotatebackendopt'],
                                "Hint-annotate")

    def task_timeshift(self):
        from pypy.jit.goal import jitstep
        jitstep.timeshift(self)
    #
    task_timeshift = taskdef(task_timeshift,
                             ["hintannotate"],
                             "Timeshift")


class PyPyJITTarget(targetpypystandalone.PyPyTarget):

    usage = "target PyPy with JIT"

    def target(self, driver, args):
        config = driver.config
        config.objspace.usemodules.pypyjit = True
        return super(PyPyJITTarget, self).target(driver, args)

    def handle_config(self, config):
        super(PyPyJITTarget, self).handle_config(config)
        config.translation.fork_before = 'hintannotate'
        config.translation.backendopt.inline_threshold = 20.1

    def handle_translate_config(self, translateconfig):
        super(PyPyJITTarget, self).handle_translate_config(translateconfig)
        translateconfig.goals = translateconfig.goals or ['timeshift']


PyPyJITTarget().interface(globals())
