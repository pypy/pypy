import os

# This module should be kept compatible with Python 1.5.2.

__revision__ = "$Id: debug.py,v 1.2 2002/11/19 13:12:27 akuchling Exp $"

# If DISTUTILS_DEBUG is anything other than the empty string, we run in
# debug mode.
DEBUG = os.environ.get('DISTUTILS_DEBUG')

