from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevel_name = 'pytest'
    interpleveldefs = {
        'raises': 'interp_pytest.pypyraises',
        'skip': 'interp_pytest.pypyskip',
    }
    appleveldefs = {
        'importorskip': 'app_pytest.importorskip',
    }
