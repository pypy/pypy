import sys, os
from optparse import OptionParser

parser = OptionParser()
parser.add_option(
    '--size-factor-list', dest='sizefactorlist',
    default='1,2,5,20,1,2,5,20,1,2,5,20',
    )
options, args = parser.parse_args(sys.argv[1:])
args = args or [sys.executable]
executables = [os.path.abspath(executable) for executable in args]
sizefactors = [int(s) for s in options.sizefactorlist.split(',')]

os.chdir(os.path.dirname(sys.argv[0]) or '.')

for sizefactor in sizefactors:
    for executable in executables:
        sys.argv[1:] = [executable, '--pickle=jitbench.benchmark_result',
                        '-v', '--no-cpython',
                        '--size-factor=%d' % sizefactor]
        execfile('bench-custom.py')
