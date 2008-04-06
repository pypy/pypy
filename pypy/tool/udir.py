#
# Common entry point to access a temporary directory (for testing, etc.)
# This uses the py lib's logic to create numbered directories.  The last
# three temporary directories are kept.
#

import autopath
import os
import py

from py.path import local 

def svn_info(url):
    basename = url[:-len('pypy/tool')]
    if basename.endswith('dist/'):
        return 'dist'
    else:
        return basename.split('/')[-2]

basename = os.environ.get('PYPY_USESSION_BASENAME')
if not basename:
    try:
        basename = '-' + svn_info(py.path.svnwc(py.magic.autopath().dirpath()).info().url) + '-'
    except:
        basename = '-'

udir = local.make_numbered_dir(prefix='usession' + basename, keep=3)
