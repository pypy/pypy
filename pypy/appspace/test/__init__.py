#
#  Confusion.  When doing 'import test' at app-level, we actually
#  find this package...  This hack "merges" the package with
#  CPython's own 'test' package.
#

import os
__path__.append(os.path.join(os.path.dirname(os.__file__), 'test'))
