
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule
import sys

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        "file": "interp_file.W_File",
        "set_file_encoding": "interp_file.set_file_encoding",
    }

    def shutdown(self, space):
        # at shutdown, flush all open streams.  Ignore I/O errors.
        from pypy.module._file.interp_file import getopenstreams, StreamErrors
        openstreams = getopenstreams(space)
        while openstreams:
            for stream in openstreams.keys():
                try:
                    del openstreams[stream]
                except KeyError:
                    pass    # key was removed in the meantime
                else:
                    try:
                        stream.flush()
                    except StreamErrors:
                        pass

    def setup_after_space_initialization(self):
        from pypy.module._file.interp_file import W_File
        from pypy.objspace.std.transparent import register_proxyable
        register_proxyable(self.space, W_File)
