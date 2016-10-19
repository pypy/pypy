
from pypy.interperter.pyopcode import opcodedesc as bc


OPT_RULES = {}

def binary_rule(opcode, types, enhanced_code):
    global OPT_RULES
    OPT_RULES[opcode] = (types, enhanced_code)

binary_rule(bc.BINARY_ADD, [Types.FLOAT, Types.FLOAT], bc.BINARY_ADD_FLOAT_FLOAT)

