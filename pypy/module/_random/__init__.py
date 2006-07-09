from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {}
  
    interpleveldefs = {
        'Random'          : 'interp_random.W_Random',  
        'seed'            : 'interp_random.get_random_method(space, "seed")',
        'getstate'        : 'interp_random.get_random_method(space, "getstate")',
        'setstate'        : 'interp_random.get_random_method(space, "setstate")',
        'jumpahead'       : 'interp_random.get_random_method(space, "jumpahead")',
        'randrange'       : 'interp_random.get_random_method(space, "randrange")',
        'randint'         : 'interp_random.get_random_method(space, "randint")',
        'choice'          : 'interp_random.get_random_method(space, "choice")',
        'shuffle'         : 'interp_random.get_random_method(space, "shuffle")',
        'sample'          : 'interp_random.get_random_method(space, "sample")',
        'random'          : 'interp_random.get_random_method(space, "random")',
        'uniform'         : 'interp_random.get_random_method(space, "uniform")',
        'betavariate'     : 'interp_random.get_random_method(space, "betavariate")',
        'expovariate'     : 'interp_random.get_random_method(space, "expovariate")',
        'gammavariate'    : 'interp_random.get_random_method(space, "gammavariate")',
        'jumpahead'       : 'interp_random.get_random_method(space, "jumpahead")',
        'gauss'           : 'interp_random.get_random_method(space, "gauss")',
        'lognormvariate'  : 'interp_random.get_random_method(space, "lognormvariate")',
        'normalvariate'   : 'interp_random.get_random_method(space, "normalvariate")',
        'vonmisesvariate' : 'interp_random.get_random_method(space, "vonmisesvariate")',
        'paretovariate'   : 'interp_random.get_random_method(space, "paretovariate")',
        'cunifvariate'    :  'interp_random.get_random_method(space, "cunifvariate")',
        'weibullvariate'  : 'interp_random.get_random_method(space, "weibullvariate")',
        'whseed'          : 'interp_random.get_random_method(space, "whseed")', # officially obsolete
        }
    