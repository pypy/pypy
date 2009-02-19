from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._winreg import interp_winreg
from pypy.rlib.rwinreg import constants

class Module(MixedModule):
    appleveldefs = {
    }
    interpleveldefs = {
        'HKEYType': 'interp_winreg.W_HKEY',
        'SetValue': 'interp_winreg.SetValue',
        'SetValueEx': 'interp_winreg.SetValueEx',
        'QueryValue': 'interp_winreg.QueryValue',
        'QueryValueEx' : 'interp_winreg.QueryValueEx',
        'CreateKey': 'interp_winreg.CreateKey',
        'DeleteKey'   : 'interp_winreg.DeleteKey',
        'DeleteValue' : 'interp_winreg.DeleteValue',
        'OpenKey'     : 'interp_winreg.OpenKey',
        'OpenKeyEx'   : 'interp_winreg.OpenKey',
        'EnumValue'   : 'interp_winreg.EnumValue',
        'EnumKey'     : 'interp_winreg.EnumKey',
        'CloseKey': 'interp_winreg.CloseKey',
        'QueryInfoKey': 'interp_winreg.QueryInfoKey',
        'ConnectRegistry': 'interp_winreg.ConnectRegistry',
    }

    for name, value in constants.iteritems():
        interpleveldefs[name] = "space.wrap(%s)" % (value,)
