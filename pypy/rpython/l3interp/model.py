from pypy.rpython.memory import lladdress
from pypy.objspace.flow import model as flowmodel
from pypy.rpython import lltype

very_low_level_ops = [
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
    'getfield', 'getsubstruct', 'setfield', 

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




primitives = [lltype.Signed, lltype.Unsigned, lltype.Float, lltype.Char,
              lltype.UniChar, lladdress.Address, lltype.Void]

primitive_to_number = {}
for i, p in enumerate(primitives):
    primitive_to_number[p] = -i - 1
del p


# possible values for exitswitch:
ONE_EXIT = -1
LAST_EXCEPTION = -2

class Operation(object):
    def __init__(self, opimpl, result, args):
        self.opimpl = opimpl # unbound method of LLFrame
        self.args = args     # list of ints: how to represent constants?
        self.result = result # resulting variable

class Link(object):
    def __init__(self, target, exitcase=None):
        self.target = target # target is a Block
        self.exitcase = exitcase  # NULL for non-exceptional case
                                  # address of exception class else
        self.move_int_registers = None

class ReturnLink(Link):
    def __init__(self, return_val=0, exitcase=None):
        Link.__init__(self, None, exitcase)
        if return_val != 0:
            self.move_int_registers = [return_val, 0]
    pass

class StartLink(Link):
    pass

class Block(object):
    def __init__(self, exitswitch, exits):
        self.operations = []         # list of Operations
        self.exitswitch = exitswitch # positives are variables
                                     # negatives see above
        self.exits = exits           # list of Links

class Graph(object):
    def __init__(self, name, startlink):
        self.name = name             # string
        self.startlink = startlink # Block
        self.constants_int = []
        self.max_num_ints = 17 #XXX calculate this

    def set_constants_int(self, constants):
        self.constants_int = constants

    def blocklist(self):
        result = []
        pending = [self.startblock]
        seen = {}
        while len(pending):
            block = pending.pop()
            if block in seen:
                continue
            result.append(block)
            for i in range(len(block.exits)):
                pending.append(block.exits[i].target)
        return result

class Globals(object):
    def __init__(self):
        self.graphs = []    # list of Graphs

