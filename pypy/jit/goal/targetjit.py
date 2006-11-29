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


class PyPyJITTarget(targetpypystandalone.PyPyTarget):

    usage = "target PyPy with JIT"

    #def target(self, driver, args):
    #    from pypy.jit.goal.x import main
    #    return main, None

    def handle_config(self, config):
        config.translation.backendopt.inline_threshold = 0
        config.translation.fork_before = 'hintannotate'

    def handle_translate_config(self, translateconfig):
        translateconfig.goals = ['hintannotate']


PyPyJITTarget().interface(globals())
