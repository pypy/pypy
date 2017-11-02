import sys
import lib_pypy.pyrepl
sys.modules['pyrepl'] = sys.modules['lib_pypy.pyrepl']
