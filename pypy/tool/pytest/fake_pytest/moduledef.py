from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevel_name = 'pytest'
    interpleveldefs = {
        'raises': 'interp_pytest.pypyraises',
        'skip': 'interp_pytest.pypyskip',
        'fixture': 'interp_pytest.fake_fixture',
    }
    appleveldefs = {
        'importorskip': 'app_pytest.importorskip',
        'mark': 'app_pytest.mark',
    }
