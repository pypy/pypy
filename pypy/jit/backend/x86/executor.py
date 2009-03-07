
""" This is a simple class for executing operations directly, without
trying too hard to have execute_operation run
"""

from pypy.rlib.rarithmetic import ovfcheck
from pypy.jit.metainterp.history import BoxInt
from pypy.jit.metainterp.resoperation import rop

class Executor(object):
    @staticmethod
    def int_add_ovf(args):
        return BoxInt(ovfcheck(args[0].getint() + args[1].getint()))

    @staticmethod
    def int_sub_ovf(args):
        return BoxInt(ovfcheck(args[0].getint() - args[1].getint()))

    @staticmethod
    def int_mul_ovf(args):
        return BoxInt(ovfcheck(args[0].getint() * args[1].getint()))

execute = [None] * rop._LAST

for key in Executor.__dict__:
    if not key.startswith('_'):
        execute[getattr(rop, key.upper())] = getattr(Executor, key)
