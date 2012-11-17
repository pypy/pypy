from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevel_name = '_posixsubprocess'

    appleveldefs = {
        }
    
    interpleveldefs = {
        'fork_exec': 'interp_subprocess.fork_exec',
        'cloexec_pipe': 'interp_subprocess.cloexec_pipe',
        }
