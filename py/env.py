#!/usr/bin/python 

import sys, os

progpath = sys.argv[0] 
packagedir = os.path.abspath(os.path.dirname(progpath))
packagename = os.path.basename(packagedir)
bindir = os.path.join(packagedir, 'bin')
rootdir = os.path.dirname(packagedir)
tooldir = os.path.join(rootdir, 'tool')

def prepend_unixpath(VAR, strpath):
    value = "%r:$%s" % (strpath, VAR)
    shell = os.getenv('SHELL')
    if shell and shell.endswith('csh'):
        return "setenv %s %s" % (VAR, value)
    else:
        return "%s=%s; export %s" % (VAR, value, VAR)

if sys.platform != 'win32':
    print prepend_unixpath('PATH', bindir)
    print prepend_unixpath('PATH', tooldir)
    print prepend_unixpath('PYTHONPATH', rootdir) 
