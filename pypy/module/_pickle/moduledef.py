from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._pickle.state import State

class Module(MixedModule):
    'Optimized RPython implementation for the Python pickle module.'
    appleveldefs = {
        'PickleError': 'app_pickle.PickleError',
        'PicklingError': 'app_pickle.PicklingError',
        'UnpicklingError': 'app_pickle.UnpicklingError',
        'load': 'app_pickle.load',
        'loads': 'app_pickle.loads',
        'dump': 'app_pickle.dump',
        'dumps': 'app_pickle.dumps',
    }

    interpleveldefs = {
        '__name__' : '(space.newtext("_pickle"))',
        'Pickler' : 'interp_pickle.W_Pickler',
        'Unpickler' : 'interp_pickle.W_Unpickler',
    }

    def startup(self, space):
        space.fromcache(State).startup(space)
