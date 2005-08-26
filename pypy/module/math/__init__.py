
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
       'e'              : 'interp_math.get(space).w_e', 
       'pi'             : 'interp_math.get(space).w_pi', 
       'pow'            : 'interp_math.pow',
       'cosh'           : 'interp_math.cosh',
       'ldexp'          : 'interp_math.ldexp',
       'hypot'          : 'interp_math.hypot',
       'tan'            : 'interp_math.tan',
       'asin'           : 'interp_math.asin',
       'fabs'           : 'interp_math.fabs',
       'floor'          : 'interp_math.floor',
       'sqrt'           : 'interp_math.sqrt',
       'frexp'          : 'interp_math.frexp',
       'degrees'        : 'interp_math.degrees',
       'log'            : 'interp_math.log',
       'log10'          : 'interp_math.log10',
       'fmod'           : 'interp_math.fmod',
       'atan'           : 'interp_math.atan',
       'ceil'           : 'interp_math.ceil',
       'sinh'           : 'interp_math.sinh',
       'cos'            : 'interp_math.cos',
       'tanh'           : 'interp_math.tanh',
       'radians'        : 'interp_math.radians',
       'sin'            : 'interp_math.sin',
       'atan2'          : 'interp_math.atan2',
       'modf'           : 'interp_math.modf',
       'exp'            : 'interp_math.exp',
       'acos'           : 'interp_math.acos',
}

