import py         # FINISHME - well, STARTME
py.test.skip("The _md5 module is not implemented at all. "
             "Only the app-level md5 module works so far.")

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {}
  
    interpleveldefs = {
    # constants / module definitions
    'digest_size'   : 'space.wrap(16)',
    'new'           : 'interp_md5.new_md5',
    'md5'           : 'interp_md5.new_md5'}
