from pypy.jit.backend.detect_cpu import autodetect_main_model
import sys


def get_module(mod):
    __import__(mod)
    return sys.modules[mod]

cpu = autodetect_main_model()
viewcode = get_module("pypy.jit.backend.%s.tool.viewcode" % cpu)
machine_code_dump = getattr(viewcode, 'machine_code_dump')
