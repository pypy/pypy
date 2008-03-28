#
# Common entry point to access a temporary directory (for testing, etc.)
# This uses the py lib's logic to create numbered directories.  The last
# three temporary directories are kept.
#

import autopath
import os

from py.path import local 

def svn_info(url):
    basename = url[:-len('pypy/tool')]
    if basename.endswith('dist/'):
        return 'dist'
    else:
        return basename.split('/')[-2]

try:
    basename = '-' + svn_info(py.path.svnwc.info().url) + '-'
except:
    basename = '-'

udir = local.make_numbered_dir(prefix='usession' + basename, keep=3)
