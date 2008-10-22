#
# Common entry point to access a temporary directory (for testing, etc.)
# This uses the py lib's logic to create numbered directories.  The last
# three temporary directories are kept.
#
# The udir is created with the following name:
#
#    $PYPY_USESSION_DIR/usession-$PYPY_USESSION_BASENAME-N
#
# where N is a small number.  If supported, a symlink is created for
# convenience too, pointing to (the most recent) udir:
#
#    $PYPY_USESSION_DIR/usession-$PYPY_USESSION_BASENAME-$USER
#
# The default value for $PYPY_USESSION_DIR is the system tmp.
# The default value for $PYPY_USESSION_BASENAME is the name
# of the current subversion branch.
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

def make_udir(dir=None, basename=None):
    if dir is not None:
        dir = local(dir)
    if basename is None:
        try:
            p = py.magic.autopath().dirpath()
            basename = svn_info(py.path.svnwc(p).info().url)
        except:
            basename = ''
    if not basename.startswith('-'):
        basename = '-' + basename
    if not basename.endswith('-'):
        basename = basename + '-'
    return local.make_numbered_dir(rootdir = dir,
                                   prefix = 'usession' + basename,
                                   keep = 3)

udir = make_udir(dir      = os.environ.get('PYPY_USESSION_DIR'),
                 basename = os.environ.get('PYPY_USESSION_BASENAME'))
