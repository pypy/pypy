from pypy.objspace.flow.model import Constant, Variable
from pypy.rpython.ootypesystem import ootype 

def camel_case(identifier):
    identifier = identifier.replace(".", "_")
    words = identifier.split('_')
    return ''.join([words[0]] + [w.capitalize() for w in words[1:]])

class Message:

    def __init__(self, name):
        self.name = camel_case(name) # XXX Should not use camel_case here
        self.infix = False
        if len(name) <= 2 and not name.isalnum():
            # Binary infix selector, e.g. "+"
            self.infix = True

    def with_args(self, args):
        return MessageWithArgs(self, args)

    def send_to(self, receiver, args):
        return self.with_args(args).send_to(receiver)

class MessageWithArgs:

    def __init__(self, message, args):
        self.message = message
        self.args = args

    def send_to(self, receiver):
        return SentMessage(self, receiver)

class SentMessage:
    
    def __init__(self, message_wargs, receiver):
        self.message_wargs = message_wargs
        self.receiver = receiver

    def assign_to(self, result):
        return Assignment(result, self)

class Assignment:

    def __init__(self, lvalue, rvalue):
        self.lvalue = lvalue
        self.rvalue = rvalue

class Self:

    pass

class Field:

    def __init__(self, name):
        self.name = name

class CodeFormatter:

    def __init__(self, gen=None): # XXX get rid of default argument
        self.gen = gen

    def format(self, code):
        if isinstance(code, Variable) or isinstance(code, Constant):
            return self.format_arg(code)
        type_name = code.__class__.__name__
        method = getattr(self, "format_%s" % type_name)
        return method(code)

    def format_arg(self, arg):
        """Formats Variables and Constants."""
        if isinstance(arg, Variable):
            return camel_case(arg.name)
        elif isinstance(arg, Constant):
            if isinstance(arg.concretetype, ootype.Instance):
                # XXX fix this
                #const_id = self.gen.unique_name(
                #        v, "const_%s" % self.gen.nameof(v.value._TYPE))
                #self.gen.constant_insts[v] = const_id
                #return "(PyConstants getConstant: '%s')" % const_id
                return None
            elif arg.concretetype == ootype.Bool:
                return str(arg.value).lower()
            elif arg.concretetype == ootype.Void:
                if isinstance(arg.value, ootype.Instance):
                    return self.format_Instance(arg.value)
                else:
                    assert arg.value is None
                    return "nil"
            else:
                # Integers etc.
                return str(arg.value)
        else:
            raise TypeError, "No representation for argument %r" % (v,)

    def format_Instance(self, INSTANCE):
        return self.gen.nameof_Instance(INSTANCE)

    def format_Self(self, _):
        return "self"

    def format_Field(self, field):
        return field.name

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

