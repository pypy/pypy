from pypy.translator.jvm.conftest import option

def getoption(name):
    return getattr(option, name)
