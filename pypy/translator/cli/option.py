from pypy.translator.cli.conftest import option

_defaultopt = dict(wd = False, source = False, nostop = False, stdout = False)

def getoption(name):
    return getattr(option, name, _defaultopt.get(name))
