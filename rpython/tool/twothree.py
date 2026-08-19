"""Helpers for code that has to run on both Python 2 and Python 3.

Everything in here exists because there is no single spelling that works on
both versions.  Where a common spelling *does* exist - and it usually does -
use it directly instead of adding a helper: a version check at a call site is
a fork of the source in miniature, and this module exists so that there is
exactly one place where such a check lives.

Deliberately has no dependencies outside the standard library, because the
translation toolchain has to keep working during bootstrapping.
"""

import sys

if sys.version_info[0] == 2:
    # 'raise tp, value, tb' is a syntax error on Python 3 and there is no way
    # to write the three-argument form so that both parsers accept it, so it
    # has to be hidden behind exec.
    exec("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")
else:
    def reraise(tp, value, tb=None):
        if value is None:
            value = tp()
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

reraise.__doc__ = """\
Re-raise an exception with an explicit traceback.

Equivalent to the Python 2 'raise tp, value, tb' statement.  Use it only
where the traceback of the original exception has to be preserved across a
re-raise; a plain 'raise' inside an except block already does that and needs
no helper.
"""
