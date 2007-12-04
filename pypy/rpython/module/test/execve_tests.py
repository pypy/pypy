
"""
Functions which call the llimpl execve function with various arguments.  Since
execve replaces the process with a new one in the successful case, these are
here to be run as a child process of the test process.
"""

import os, sys
sys.path.append(sys.argv[1])

from pypy.rpython.module.test.test_ll_os import EXECVE_ENV, getllimpl

execve = getllimpl(os.execve)


def execve_true():
    execve("/bin/true", ["/bin/true"], {})

def execve_false():
    execve("/bin/false", ["/bin/false"], {})

def execve_env():
    execve("/usr/bin/env", ["/usr/bin/env"], EXECVE_ENV)

if __name__ == '__main__':
    globals()[sys.argv[2]]()
