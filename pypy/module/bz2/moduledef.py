from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    # The private part of the bz2 module.

    applevel_name = '_bz2'

    interpleveldefs = {
        'BZ2Compressor'      : 'interp_bz2.W_BZ2Compressor',
        'BZ2Decompressor'    : 'interp_bz2.W_BZ2Decompressor',
    }

    appleveldefs = {
    }

    def startup(self, space):
        from pypy.module.bz2 import interp_bz2
        space.setitem(self.w_dict, space.newtext('bzlib_version'),
                      space.newtext(interp_bz2.bzlib_version()))
        space.setitem(self.w_dict, space.newtext('bzlib_version_info'),
                      interp_bz2.get_version_info(space))
