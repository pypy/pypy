from pypy.translator.jvm.typesystem import \
     IFLT, IFLE, IFEQ, IFNE, IFGT, IFGE, \
     IFNONNULL, IF_ACMPEQ, GOTO, ICONST, \
     DCONST_0, DCMPG, LCONST_0, LCMP, \
     IF_ICMPLT, IF_ICMPLE, IF_ICMPEQ, IF_ICMPNE, IF_ICMPGT, IF_ICMPGE, \
     PYPYUINTCMP, PYPYULONGCMP

from pypy.translator.jvm.generator import \
     Label

##### Branch directly as the result of a comparison

# A table mapping the kind of numeric type to the opcode or method
# needed to compare two values of that type.  The result of this
# opcode of method is that a -1, 0, or 1 is pushed on the stack,
# like the cmp() method in Python.  Used to prepare the cmp_opname
# table below.
cmp_numeric_prep = {
    'uint': PYPYUINTCMP,
    'float': DCMPG,
    'llong': LCMP,
    'ullong': PYPYULONGCMP,
    }

# A table mapping the kind of comparison to the opcode which
# performs that comparison and then branches.  Used to prepare the
# cmp_opname table below.
cmp_numeric_branch = {
    'lt': IFLT,
    'le': IFLE,
    'eq': IFEQ,
    'ne': IFNE,
    'gt': IFGT,
    'ge': IFGE,
    }

# A table that maps an opname to a set of instructions for
# performing a comparison.  Some entries are inserted
# automatically, either because they do not fit the numeric
# pattern or are exceptions, and others are created from the
# cmp_numeric_{prep,branch} tables above.  In all cases, the
# instructions are a list of opcode/functions which will be
# emitted.  The last one must be a branching instruction.
cmp_opname = {
    # Single operand entries:
    'bool_not': [IFEQ],
    'int_is_true': [IFNE],
    'uint_is_true': [IFNE],
    'float_is_true': [DCONST_0, DCMPG, IFNE],
    'llong_is_true': [LCONST_0, LCMP, IFNE],
    'ullong_is_true': [LCONST_0, LCMP, IFNE],

    # Double operand entries:
    'oononnull': [IFNONNULL],
    'oois': [IF_ACMPEQ],

    'unichar_eq': [IF_ICMPEQ],
    'unichar_ne': [IF_ICMPNE],

    'char_eq': [IF_ICMPEQ],
    'char_ne': [IF_ICMPNE],
    'char_lt': [IF_ICMPLT],
    'char_le': [IF_ICMPLE],
    'char_gt': [IF_ICMPGT],
    'char_ge': [IF_ICMPGE],
    
    'int_eq': [IF_ICMPEQ],
    'int_ne': [IF_ICMPNE],
    'int_lt': [IF_ICMPLT],
    'int_le': [IF_ICMPLE],
    'int_gt': [IF_ICMPGT],
    'int_ge': [IF_ICMPGE],

    'int_eq_ovf': [IF_ICMPEQ],
    'int_ne_ovf': [IF_ICMPNE],
    'int_lt_ovf': [IF_ICMPLT],
    'int_le_ovf': [IF_ICMPLE],
    'int_gt_ovf': [IF_ICMPGT],
    'int_ge_ovf': [IF_ICMPGE],

    'uint_eq': [IF_ICMPEQ],
    'uint_ne': [IF_ICMPNE],    
    }

# fill in the default entries like uint_lt, llong_eq:
for (prepnm, prepfn) in cmp_numeric_prep.items():
    for (brnm, brfn) in cmp_numeric_branch.items():
        opname = "%s_%s" % (prepnm, brnm)
        if opname not in cmp_opname:
            cmp_opname[opname] = [prepfn, brfn]

def can_branch_directly(opname):
    """
    Returns true if opname is the kind of instruction where we can
    branch directly based on its result without storing it into a
    variable anywhere.  For example, int_lt is such an instruction.
    This is used to optimize away intermediate boolean values, which
    otherwise force us to generate very inefficient and hard-to-read
    code.
    """
    return opname in cmp_opname

def branch_if(gen, opname, truelabel):
    """
    Branches to 'truelabel' if 'opname' would return true.
    'opname' must be something like int_lt, float_ne, etc,
    as determined by can_branch_directly().  
    """
    assert can_branch_directly(opname)
    assert isinstance(truelabel, Label)
    instrs = cmp_opname[opname]
    for i in instrs[:-1]: gen.emit(i)
    gen.emit(instrs[-1], truelabel)

