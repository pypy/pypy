import py

_defaultopt = dict(wd = False, source = False, nostop = False, stdout = False)

def getoption(name):
    return getattr(py.test.config.option, name, _defaultopt.get(name))
