#
# Common entry point to access a temporary directory (for testing, etc.)
# This uses the py lib's logic to create numbered directories.  The last
# three temporary directories are kept.
#

import autopath

from py.path import local 

udir = local.make_numbered_dir(prefix='usession-', keep=3)

