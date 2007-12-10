
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        "file": "interp_file.W_File",
    }

    def shutdown(self, space):
        # at shutdown, flush all open streams
        from pypy.module._file.interp_file import getopenstreams
        openstreams = getopenstreams(space)
        while openstreams:
            for stream in openstreams.keys():
                try:
                    del openstreams[stream]
                except KeyError:
                    pass    # key was removed in the meantime
                else:
                    stream.flush()
