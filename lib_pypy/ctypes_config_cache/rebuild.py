#! /usr/bin/env python
# Run this script to rebuild all caches from the *.ctc.py files.

# hack: we cannot directly import autopath, as we are outside the pypy
# package.  However, we pretend to be inside pypy/tool and manually run it, to
# get the correct path
import os.path
this_dir = os.path.dirname(__file__)
autopath_py = os.path.join(this_dir, '../../pypy/tool/autopath.py')
autopath_py = os.path.abspath(autopath_py)
execfile(autopath_py, dict(__name__='autopath', __file__=autopath_py))

from pypy.tool.lib_pypy import try_rebuild

if __name__ == '__main__':
    try_rebuild()
