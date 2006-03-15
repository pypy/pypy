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

    def _selector_parts(self, arg_count):
        parts = [self.name]
        if arg_count > 1:
            parts += ["with"] * (arg_count - 1)
        return parts

    def symbol(self, arg_count):
        if arg_count == 0 or self.infix:
            return self.name
        else:
            parts = self._selector_parts(arg_count)
            return "%s:%s" % (parts[0], "".join([p + ":" for p in parts[1:]]))

    def signature(self, arg_strings):
        if len(arg_strings) == 0:
            return self.name
        elif self.infix:
            assert len(arg_strings) == 1
            return "%s %s" % (self.name, arg_strings[0])
        else:
            parts = self._selector_parts(len(arg_strings))
            return " ".join(["%s: %s" % (p, a)
                    for (p, a) in zip(parts, arg_strings)])

