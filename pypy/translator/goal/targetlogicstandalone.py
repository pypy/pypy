import os, sys

from pypy.translator.goal.targetpypystandalone import PyPyTarget


# _____ Define and setup target ___

opt_defaults = {'translation.stackless' : True,
                'translation.debug': True,
                'translation.gc': 'framework',
                'objspace.name': 'logic',
                'objspace.usemodules._stackless': True}

class LogicPyPyTarget(PyPyTarget):
    usage = "target logic standalone"

    def handle_config(self, config):
        config.set(**opt_defaults)

LogicPyPyTarget().interface(globals())
