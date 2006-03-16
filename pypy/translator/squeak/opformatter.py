import sys
from pypy.objspace.flow.model import Constant, Variable
from pypy.rpython.rarithmetic import r_int, r_uint, r_longlong, r_ulonglong
from pypy.rpython.ootypesystem.ootype import Instance
from pypy.translator.squeak.message import Message, camel_case

def _setup_int_masks():
    """Generates code for helpers to mask the various integer types."""
    masks = {}
    for name, r_type in ("int", r_int), ("uint", r_uint), \
            ("llong", r_longlong), ("ullong", r_ulonglong):
        helper_name = "mask%s" % name.capitalize()
        if name[0] == "u":
            # Unsigned integer type
            code = """%s: i 
                ^ i bitAnd: %s""" % (helper_name, r_type.MASK)
        else:
            # Signed integer type
            code = """%s: i
                (i <= %s) & (i >= %s) ifTrue: [^i].
                (i < 0) ifTrue: [^i bitAnd: %s]
                        ifFalse: [^(((i negated) - 1) bitAnd: %s) negated - 1]
                """ % (helper_name, r_type.MASK>>1, -(r_type.MASK>>1)-1,
                        r_type.MASK>>1, r_type.MASK>>1)
        masks[name] = helper_name, code
    return masks

class OpFormatter:

    ops = {
        'new':         'new',
        'runtimenew':  'new',
        'classof':     'class',
        'same_as':     'yourself', 
    }

    number_ops = {
        'abs':       'abs',
        'is_true':   'isZero not',
        'neg':       'negated',
        'invert':    'bitInvert', # maybe bitInvert32?

        'add':       '+',
        'sub':       '-',
        'eq':        '=',
        'mul':       '*',
        'div':       '//',
        'floordiv':  '//',
    }
    
    number_opprefixes = "int", "uint", "llong", "ullong", "float"

    wrapping_ops = "neg", "invert", "add", "sub", "mul"

    int_masks = _setup_int_masks()

    def __init__(self, gen, node):
        self.gen = gen
        self.node = node

    def expr(self, v):
        # XXX this code duplicated in gensqueak.py
        if isinstance(v, Variable):
            return camel_case(v.name)
        elif isinstance(v, Constant):
            if isinstance(v.concretetype, Instance):
                const_id = self.gen.unique_name(
                        v, "const_%s" % self.gen.nameof(v.value._TYPE))
                self.gen.constant_insts[v] = const_id
                return "(PyConstants getConstant: '%s')" % const_id
            return self.gen.nameof(v.value)
        else:
            raise TypeError, "expr(%r)" % (v,)

    def format(self, op):
        opname_parts = op.opname.split("_")
        if opname_parts[0] in self.number_opprefixes:
            return self.format_number_op(
                    op, opname_parts[0], "_".join(opname_parts[1:]))
        op_method = getattr(self, "op_%s" % op.opname, None)
        if op_method is not None:
            return op_method(op)
        else:
            name = op.opname
            name = self.ops.get(name, name)
            receiver = self.expr(op.args[0])
            args = [self.expr(arg) for arg in op.args[1:]]
            return self.assignment(op, receiver, name, args)

    def format_number_op(self, op, ptype, opname):
        receiver = self.expr(op.args[0])
        args = [self.expr(arg) for arg in op.args[1:]]
        sel = Message(self.number_ops[opname])
        message = "%s %s" % (receiver, sel.signature(args))
        if opname in self.wrapping_ops \
                and self.int_masks.has_key(ptype):
            from pypy.translator.squeak.gensqueak import HelperNode
            mask_name, mask_code = self.int_masks[ptype]
            helper = HelperNode(self.gen, Message(mask_name), mask_code)
            message = helper.apply(["(%s)" % message])
            self.gen.schedule_node(helper)
        return "%s := %s." % (self.expr(op.result), message)

    def assignment(self, op, receiver_name, sel_name, arg_names):
        sel = Message(sel_name)
        return "%s := %s %s." % (self.expr(op.result),
                receiver_name, sel.signature(arg_names))

    def op_oosend(self, op):
        message = op.args[0].value
        if op.args[1] == self.node.self:
            receiver = "self"
        else:
            receiver = self.expr(op.args[1])
        args = [self.expr(a) for a in op.args[2:]]
        from pypy.translator.squeak.gensqueak import MethodNode
        self.gen.schedule_node(
                MethodNode(self.gen, op.args[1].concretetype, message))
        return self.assignment(op, receiver, message, args)

    def op_oogetfield(self, op):
        INST = op.args[0].concretetype
        receiver = self.expr(op.args[0])
        field_name = self.node.unique_field(INST, op.args[1].value)
        if op.args[0] == self.node.self:
            # Private field access
            # Could also directly substitute op.result with name
            # everywhere for optimization.
            return "%s := %s." % (self.expr(op.result), field_name)
        else:
            # Public field access
            from pypy.translator.squeak.gensqueak import GetterNode
            self.gen.schedule_node(GetterNode(self.gen, INST, field_name))
            return self.assignment(op, receiver, field_name, [])

    def op_oosetfield(self, op):
        # Note that the result variable is never used
        INST = op.args[0].concretetype
        field_name = self.node.unique_field(INST, op.args[1].value)
        field_value = self.expr(op.args[2])
        if op.args[0] == self.node.self:
            # Private field access
            return "%s := %s." % (field_name, field_value)
        else:
            # Public field access
            from pypy.translator.squeak.gensqueak import SetterNode
            self.gen.schedule_node(SetterNode(self.gen, INST, field_name))
            receiver = self.expr(op.args[0])
            return "%s %s: %s." % (receiver, field_name, field_value)

    def op_oodowncast(self, op):
        return "%s := %s." % (self.expr(op.result), self.expr(op.args[0]))

    def op_direct_call(self, op):
        # XXX not sure if static methods of a specific class should
        # be treated differently.
        from pypy.translator.squeak.gensqueak import FunctionNode
        receiver = "PyFunctions"
        callable_name = self.expr(op.args[0])
        args = [self.expr(a) for a in op.args[1:]]
        self.gen.schedule_node(
            FunctionNode(self.gen, op.args[0].value.graph))
        return self.assignment(op, receiver, callable_name, args)

