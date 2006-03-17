from pypy.objspace.flow.model import Constant, Variable
from pypy.rpython.ootypesystem import ootype 

class AbstractCode:

    pass

class Message(AbstractCode):

    def __init__(self, name):
        self.name = name
        self.infix = False
        if len(name) <= 2 and not name.isalnum():
            # Binary infix selector, e.g. "+"
            self.infix = True

    def with_args(self, args):
        return MessageWithArgs(self, args)

    def send_to(self, receiver, args):
        return self.with_args(args).send_to(receiver)

class MessageWithArgs(AbstractCode):

    def __init__(self, message, args):
        self.message = message
        self.args = args

    def send_to(self, receiver):
        return SentMessage(self, receiver)

class SentMessage(AbstractCode):
    
    def __init__(self, message_wargs, receiver):
        self.message_wargs = message_wargs
        self.receiver = receiver

    def assign_to(self, result):
        return Assignment(result, self)

class Assignment(AbstractCode):

    def __init__(self, lvalue, rvalue):
        self.lvalue = lvalue
        self.rvalue = rvalue

class Self(AbstractCode):

    pass

class Field(AbstractCode):

    def __init__(self, name):
        self.name = name

class CustomVariable(AbstractCode):

    def __init__(self, name):
        self.name = name

class CodeFormatter:

    def __init__(self, gen=None): # XXX get rid of default argument
        self.gen = gen

    def format(self, code):
        if isinstance(code, Variable) or isinstance(code, Constant):
            return self.format_arg(code)
        elif isinstance(code, AbstractCode):
            type_name = code.__class__.__name__
            method = getattr(self, "format_%s" % type_name)
            return method(code)
        else:
            # Assume it's a constant value to be formatted
            return self.name_constant(code)

    def format_arg(self, arg):
        """Formats Variables and Constants."""
        if isinstance(arg, Variable):
            return self.gen.unique_var_name(arg)
        elif isinstance(arg, Constant):
            if isinstance(arg.concretetype, ootype.Instance):
                # XXX fix this
                const_id = self.gen.unique_name(
                        arg, "const_%s" % self.format_Instance(arg.value._TYPE))
                self.gen.constant_insts[arg] = const_id
                return "(PyConstants getConstant: '%s')" % const_id
            elif arg.concretetype == ootype.Char or arg.concretetype == ootype.UniChar:
                # XXX temporary
                return str(ord(arg.value))
            else:
                return self.name_constant(arg.value)
        else:
            raise TypeError, "No representation for argument %r" % (arg,)

    def name_constant(self, value):
        if isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, ootype.Instance):
            return self.format_Instance(value)
        elif value is None:
            return "nil"
        elif isinstance(value, int):
            return str(value)
        elif isinstance(value, ootype._class):
            return self.format_Instance(value._INSTANCE)
        elif isinstance(value, ootype._static_meth):
            return self.gen.unique_func_name(value.graph)
        else:
            raise TypeError, "can't format constant (%s)" % value

    def format_Instance(self, INSTANCE):
        if INSTANCE is None:
            return "Object"
        return self.gen.unique_class_name(INSTANCE)

    def format_Self(self, _):
        return "self"

    def format_Field(self, field):
        return field.name

    def format_CustomVariable(self, var):
        return var.name

    def format_MessageWithArgs(self, message):
        name = message.message.name
        arg_count = len(message.args)
        if arg_count == 0:
            return name
        elif message.message.infix:
            assert arg_count == 1
            return "%s %s" % (name, self.format(message.args[0]))
        else:
            parts = [name]
            if arg_count > 1:
                parts += ["with"] * (arg_count - 1)
            return " ".join(["%s: %s" % (p, self.format(a))
                    for (p, a) in zip(parts, message.args)])

    def format_SentMessage(self, smessage):
        return "(%s %s)" % (self.format(smessage.receiver),
                self.format_MessageWithArgs(smessage.message_wargs))

    def format_Assignment(self, ass):
        return "%s := %s" % (self.format(ass.lvalue), self.format(ass.rvalue))

