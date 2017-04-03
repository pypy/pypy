import sys
import lib_pypy.pyrepl
sys.modules['pyrepl'] = sys.modules['lib_pypy.pyrepl']

if sys.platform.startswith('freebsd'):
    raise Exception('XXX seems to hangs on FreeBSD9')
