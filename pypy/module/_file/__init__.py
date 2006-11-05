
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
        "file": "app_file.file",
    }

    interpleveldefs = {
        "open_file_as_stream": "interp_file.open_file_as_stream",
        "fdopen_as_stream": "interp_file.fdopen_as_stream",
    }

