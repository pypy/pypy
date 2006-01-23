from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem import lltype, llmemory

very_low_level_ops = [
    'nop',

    #control flow operations (only at the end of blocks)
    'jump', 'jump_cond',
    'void_return', 'int_return', 'float_return', 'adr_return',

    #operations with adresses:
    'adr_add', 'adr_delta', 'adr_eq', 'adr_ge', 'adr_gt', 'adr_le',
    'adr_lt', 'adr_ne', 'adr_sub',

    #operations with bools:
    'bool_not',

    #casts:
    'cast_bool_to_float', 'cast_bool_to_int', 'cast_char_to_int',
    'cast_float_to_int', 'cast_int_to_char', 'cast_int_to_float',
    'cast_int_to_uint', 'cast_int_to_unichar', 'cast_pointer',
    'cast_ptr_to_int', 'cast_uint_to_int', 'cast_unichar_to_int',

    #operations with chars:
    'char_eq', 'char_ge', 'char_gt', 'char_le', 'char_lt', 'char_ne',

    #calls:
    'direct_call',

    #flavored memory operations:
    'flavored_free', 'flavored_malloc',

    #float operations:
    'float_abs', 'float_add', 'float_div', 'float_eq', 'float_floor',
    'float_floordiv', 'float_fmod', 'float_ge', 'float_gt', 'float_invert',
    'float_is_true', 'float_le', 'float_lt', 'float_mod', 'float_mul',
    'float_ne', 'float_neg', 'float_sub', 'float_truediv',

    #array operations:
    'getarrayitem', 'getarraysize', 'getarraysubstruct', 'setarrayitem',

    #struct operations:
    'getfield_int', 'getfield_char', 'getfield_dbl', 'getfield_ptr', 
    'getsubstruct',
    'setfield_int', 'setfield_char', 'setfield_dbl', 'setfield_ptr',

    #integer operations:
    'int_abs', 'int_abs_ovf', 'int_add', 'int_add_ovf', 'int_and',
    'int_and_ovf', 'int_div', 'int_div_ovf', 'int_eq', 'int_eq_ovf',
    'int_floordiv', 'int_floordiv_ovf', 'int_floordiv_ovf_zer', 'int_ge',
    'int_ge_ovf', 'int_gt', 'int_gt_ovf', 'int_invert', 'int_invert_ovf',
    'int_is_true', 'int_is_true_ovf', 'int_le', 'int_le_ovf', 'int_lshift',
    'int_lshift_ovf', 'int_lt', 'int_lt_ovf', 'int_mod', 'int_mod_ovf',
    'int_mod_ovf_zer', 'int_mul', 'int_mul_ovf', 'int_ne', 'int_ne_ovf',
    'int_neg', 'int_neg_ovf', 'int_or', 'int_or_ovf', 'int_rshift',
    'int_rshift_ovf', 'int_sub', 'int_sub_ovf', 'int_truediv',
    'int_truediv_ovf', 'int_xor', 'int_xor_ovf',

    #regular object memory operations:
    'keepalive', 'malloc', 'malloc_varsize',

    #pointer operations:
    'ptr_eq', 'ptr_iszero', 'ptr_ne', 'ptr_nonzero',

    #raw memory operations
    'raw_free', 'raw_load', 'raw_malloc', 'raw_memcopy', 'raw_store',

    #same_as:
    'same_as',

    #operations with unsigned integers: 
    'uint_abs', 'uint_add', 'uint_and', 'uint_div', 'uint_eq',
    'uint_floordiv', 'uint_ge', 'uint_gt', 'uint_invert', 'uint_is_true',
    'uint_le', 'uint_lshift', 'uint_lt', 'uint_mod', 'uint_mul', 'uint_ne',
    'uint_neg', 'uint_or', 'uint_rshift', 'uint_sub', 'uint_truediv',
    'uint_xor',

    #operations with unicode characters
    'unichar_eq', 'unichar_ne'
    ]

#assert len(very_low_level_ops) <= 256
very_low_level_opcode = {}
for i, op in enumerate(very_low_level_ops):
    very_low_level_opcode[op] = i
del i, op


primitives = [lltype.Signed, lltype.Unsigned, lltype.Float, lltype.Char,
              lltype.UniChar, llmemory.Address, lltype.Void]

primitive_to_number = {}
for i, p in enumerate(primitives):
    primitive_to_number[p] = -i - 1
del i, p

class Op: "Attribute-based interface to very_low_level_opcode"
Op = Op()
Op.__dict__ = very_low_level_opcode


class Block(object):
    def __init__(self, insns, exit0=None,
                              exit1=None,
                              constants_int=None,
                              constants_dbl=None,
                              constants_ptr=None,
                              constants_offset=None,
                              called_graphs=None):
        self.insns = insns
        self.exit0 = exit0
        self.exit1 = exit1
        self.constants_int = constants_int
        self.constants_dbl = constants_dbl
        self.constants_ptr = constants_ptr
        
        self.constants_offset = constants_offset
        self.called_graphs = called_graphs

class Link(object):
    def __init__(self, target, targetregs_int=None,
                               targetregs_dbl=None,
                               targetregs_ptr=None):
        self.target = target
        self.targetregs_int = targetregs_int
        self.targetregs_dbl = targetregs_dbl
        self.targetregs_ptr = targetregs_ptr

class Graph(object):
    def __init__(self, name, startblock, nargs_int, nargs_dbl, nargs_ptr):
        self.name = name
        self.startblock = startblock
        self.nargs_int = nargs_int
        self.nargs_dbl = nargs_dbl
        self.nargs_ptr = nargs_ptr
