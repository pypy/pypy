from pypy.rpython.rarithmetic import r_int, r_uint, r_longlong, r_ulonglong
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
        'same_as':     'yourself', 
        'bool_not':    'not',
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
        'div':       '//',
        'floordiv':  '//',
        #'truediv':   '/', # XXX fix this when we have float support
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
    
    number_opprefixes = "int", "uint", "llong", "ullong", "float"

    wrapping_ops = "neg", "invert", "add", "sub", "mul", "lshift"

    int_masks = _setup_int_masks()

    def __init__(self, gen, node):
        self.gen = gen
        self.node = node
        self.codef = CodeFormatter(gen)

    def format(self, op):
        opname_parts = op.opname.split("_")
        if opname_parts[0] in self.number_opprefixes:
            return self.format_number_op(
                    op, opname_parts[0], "_".join(opname_parts[1:]))
        op_method = getattr(self, "op_%s" % op.opname, None)
        if op_method is not None:
            return op_method(op)
        else:
            if not self.ops.has_key(op.opname):
                raise NotImplementedError(
                        "operation not supported: %s" % op.opname)
            name = self.ops[op.opname]
            sent = Message(name).send_to(op.args[0], op.args[1:])
            return self.codef.format(sent.assign_to(op.result))

    def format_number_op(self, op, ptype, opname):
        message = Message(self.number_ops[opname])
        sent_message = message.send_to(op.args[0], op.args[1:])
        if opname in self.wrapping_ops \
                and self.int_masks.has_key(ptype):
            # XXX how do i get rid of this import?
            from pypy.translator.squeak.node import HelperNode
            mask_name, mask_code = self.int_masks[ptype]
            helper = HelperNode(self.gen, Message(mask_name), mask_code)
            sent_message = helper.apply([sent_message])
            self.gen.schedule_node(helper)
        return self.codef.format(sent_message.assign_to(op.result))

    def op_oosend(self, op):
        message_name = op.args[0].value
        message_name = self.gen.unique_method_name(
                op.args[1].concretetype, message_name)
        if op.args[1] == self.node.self:
            receiver = Self()
        else:
            receiver = op.args[1]
        sent_message = Message(message_name).send_to(receiver, op.args[2:])
        return  self.codef.format(sent_message.assign_to(op.result))

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
        return self.codef.format(Assignment(op.result, rvalue))

    def op_oosetfield(self, op):
        # Note that the result variable is never used
        INST = op.args[0].concretetype
        field_name = self.gen.unique_field_name(INST, op.args[1].value)
        field_value = op.args[2]
        if op.args[0] == self.node.self:
            # Private field access
            return self.codef.format(Assignment(Field(field_name), field_value))
        else:
            # Public field access
            setter = Message(field_name).send_to(op.args[0], [field_value])
            return self.codef.format(setter)

    def op_oodowncast(self, op):
        return self.codef.format(Assignment(op.result, op.args[0]))

    def op_direct_call(self, op):
        # XXX how do i get rid of this import?
        from pypy.translator.squeak.node import FunctionNode
        function_name = self.gen.unique_func_name(op.args[0].value.graph)
        msg = Message(function_name).send_to(FunctionNode.FUNCTIONS, op.args[1:])
        return self.codef.format(msg.assign_to(op.result))

