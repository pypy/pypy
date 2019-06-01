from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
    }

    interpleveldefs = {
        'write_input': 'interp_testconsole.write_input',
        'read_output': 'interp_testconsole.read_output',
    }
