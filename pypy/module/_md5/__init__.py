from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {}
  
    interpleveldefs = {
    # constants / module definitions
    'digest_size'   : 'space.wrap(16)',
    'new'           : 'interp_md5.new_md5',
    'md5'           : 'interp_md5.new_md5'}