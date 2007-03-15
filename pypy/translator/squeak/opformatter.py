from pypy.rlib.rarithmetic import r_int, r_uint, r_longlong, r_ulonglong
from pypy.translator.squeak.codeformatter import CodeFormatter
from pypy.translator.squeak.codeformatter import Message, Self, Assignment, Field

def _setup_int_masks():
    """Generates code for helpers to mask the various integer types."""
    masks = {}
    # NB: behaviour of signed long longs is undefined on overflow
    for name, r_type in ("int", r_int), ("uint", r_uint), ("ullong", r_ulonglong):
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
        'bool_not':    'not',

        'cast_int_to_float': 'asFloat',
        # XXX this potentially incorrect (may return LargeIntegers)
        'cast_float_to_int': 'truncated',
    }

    number_ops = {
        'abs':       'abs',
        'is_true':   'isZero not',
        'neg':       'negated',
        'invert':    'bitInvert',

        'add':       '+',
        'sub':       '-',
        'eq':        '=',
        'mul':       '*',
        'floordiv':  'quo',
        'truediv':   '/ asFloat',
        'mod':       r'\\',
        'eq':        '=',
        'ne':        '~=',
        'lt':        '<',
        'le':        '<=',
        'gt':        '>',
        'ge':        '>=',
        'and':       'bitAnd',
        'or':        'bitOr',
        'lshift':    '<<',
        'rshift':    '>>',
        'xor':       'bitXor',
        # XXX need to support x_ovf ops
    }

    number_opprefixes = "int", "uint", "llong", "ullong",\
            "float", "char", "unichar"

    wrapping_ops = "neg", "invert", "add", "sub", "mul", "lshift"

    noops = "same_as", "ooupcast", "oodowncast", "cast_char_to_int", \
            "cast_unichar_to_int", "cast_int_to_unichar", \
            "cast_int_to_char", "cast_int_to_longlong", \
            "truncate_longlong_to_int"

    int_masks = _setup_int_masks()

    def __init__(self, gen, node):
        self.gen = gen
        self.node = node
        self.codef = CodeFormatter(gen)

    def format(self, op):
        if self.ops.has_key(op.opname):
            name = self.ops[op.opname]
            sent = Message(name).send_to(op.args[0], op.args[1:])
            return self.codef.format(sent.assign_to(op.result))
        opname_parts = op.opname.split("_")
        if opname_parts[0] in self.number_opprefixes:
            return self.format_number_op(
                    op, opname_parts[0], "_".join(opname_parts[1:]))
        op_method = getattr(self, "op_%s" % op.opname, None)
        if op_method is not None:
            return self.codef.format(op_method(op))
        else:
            raise NotImplementedError(
                        "operation not supported: %s" % op.opname)

    def format_number_op(self, op, ptype, opname):
        messages = self.number_ops[opname].split()
        msg = Message(messages[0])
        sent_message = msg.send_to(op.args[0], op.args[1:])
        for add_message in messages[1:]:
            sent_message = Message(add_message).send_to(sent_message, [])
        if opname in self.wrapping_ops \
                and self.int_masks.has_key(ptype):
            sent_message = self.apply_mask_helper(sent_message, ptype)
        return self.codef.format(sent_message.assign_to(op.result))

    def apply_mask_helper(self, receiver, mask_type_name):
        # XXX how do i get rid of this import?
        from pypy.translator.squeak.node import HelperNode
        mask_name, mask_code = self.int_masks[mask_type_name]
        helper = HelperNode(self.gen, Message(mask_name), mask_code)
        result = helper.apply([receiver])
        self.gen.schedule_node(helper)
        return result

    def op_oosend(self, op):
        message_name = op.args[0].value
        message_name = self.gen.unique_method_name(
                op.args[1].concretetype, message_name)
        if op.args[1] == self.node.self:
            receiver = Self()
        else:
            receiver = op.args[1]
        sent_message = Message(message_name).send_to(receiver, op.args[2:])
        return sent_message.assign_to(op.result)

    def op_oogetfield(self, op):
        INST = op.args[0].concretetype
        field_name = self.gen.unique_field_name(INST, op.args[1].value)
        if op.args[0] == self.node.self:
            # Private field access
            # Could also directly substitute op.result with name
            # everywhere for optimization.
            rvalue = Field(field_name)
        else:
            # Public field access
            rvalue = Message(field_name).send_to(op.args[0], [])
        return Assignment(op.result, rvalue)

    def op_oosetfield(self, op):
        # Note that the result variable is never used
        INST = op.args[0].concretetype
        field_name = self.gen.unique_field_name(INST, op.args[1].value)
        field_value = op.args[2]
        if op.args[0] == self.node.self:
            # Private field access
            return Assignment(Field(field_name), field_value)
        else:
            # Public field access
            return Message(field_name).send_to(op.args[0], [field_value])

    def op_direct_call(self, op):
        # XXX how do i get rid of this import?
        from pypy.translator.squeak.node import FunctionNode
        function_name = self.gen.unique_func_name(op.args[0].value.graph)
        msg = Message(function_name).send_to(FunctionNode.FUNCTIONS, op.args[1:])
        return msg.assign_to(op.result)

    def cast_bool(self, op, true_repr, false_repr):
        msg = Message("ifTrue: [%s] ifFalse: [%s]" % (true_repr, false_repr))
        return msg.send_to(op.args[0], []).assign_to(op.result)

    def op_cast_bool_to_int(self, op):
        return self.cast_bool(op, "1", "0")

    op_cast_bool_to_uint = op_cast_bool_to_int

    def op_cast_bool_to_float(self, op):
        return self.cast_bool(op, "1.0", "0.0")

    def masking_cast(self, op, mask):
        cast = self.apply_mask_helper(op.args[0], mask)
        return Assignment(op.result, cast)

    def op_cast_int_to_uint(self, op):
        return self.masking_cast(op, "uint")

    def op_cast_uint_to_int(self, op):
        return self.masking_cast(op, "int")

    def op_cast_float_to_uint(self, op):
        truncated = Message("truncated").send_to(op.args[0], [])
        return Assignment(op.result, self.apply_mask_helper(truncated, "uint"))

    def noop(self, op):
        return Assignment(op.result, op.args[0])

for opname in OpFormatter.noops:
    setattr(OpFormatter, "op_%s" % opname, OpFormatter.noop)
