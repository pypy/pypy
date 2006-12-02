"""
A translation target:   python pypy/translator/goal/translate.py targetjit
"""
from pypy.translator.goal import targetpypystandalone
from pypy.translator.driver import TranslationDriver, taskdef
from pypy.annotation.pairtype import extendabletype

class __extend__(TranslationDriver):
    __metaclass__ = extendabletype

    def task_hintannotate(self):
        from pypy.jit.goal import jitstep
        jitstep.hintannotate(self)
    #
    task_hintannotate = taskdef(task_hintannotate,
                                [TranslationDriver.BACKENDOPT],
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

    #def target(self, driver, args):
    #    from pypy.jit.goal.x import main
    #    return main, None

    def handle_config(self, config):
        config.translation.backendopt.inline_threshold = 0
        config.translation.backendopt.merge_if_blocks = False
        config.translation.fork_before = 'hintannotate'

    def handle_translate_config(self, translateconfig):
        translateconfig.goals = ['timeshift']


PyPyJITTarget().interface(globals())
