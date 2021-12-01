OPNAMES = []
HASARG = []

def define_op(name, has_arg=False):
    globals()[name] = len(OPNAMES)
    OPNAMES.append(name)
    HASARG.append(has_arg)

define_op("CONST_INT", True)
define_op("DUP")
define_op("POP")

define_op("LT")
define_op("EQ")

define_op("ADD")
define_op("SUB")
define_op("MUL")
define_op("DIV")
define_op("MOD")

define_op("EXIT")
define_op("JUMP", True)
define_op("JUMP_IF", True)
define_op("JUMP_IF_FLS", True)

define_op("CALL", True)
define_op("CALL_JIT", True)
define_op("CALL_NORMAL", True)
define_op("RET", True)
define_op("NEWSTR", True)
