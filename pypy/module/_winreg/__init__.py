from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._winreg import interp_winreg
from pypy.rlib.rwinreg import constants

class Module(MixedModule):
    appleveldefs = {
    }
    interpleveldefs = {
        'SetValue': 'interp_winreg.SetValue',
        'QueryValue': 'interp_winreg.QueryValue',
        'HKEYType': 'interp_winreg.W_HKEY',
    }

    for name, value in constants.iteritems():
        interpleveldefs[name] = "space.wrap(%s)" % (value,)
