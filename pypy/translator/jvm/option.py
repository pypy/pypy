from pypy.conftest import option

# Not sure why this is needed.  Sure that it shouldn't be, even.
_default_values = {
    'javac':'javac',
    'java':'java',
    'jasmin':'jasmin',
    'noasm':False,
    'package':'pypy',
    'wd':False,
    'norun':False,
    'trace':False,
    'byte-arrays':False
    }

def getoption(name):
    if hasattr(option, name):
        return getattr(option, name)
    return _default_values[name]
