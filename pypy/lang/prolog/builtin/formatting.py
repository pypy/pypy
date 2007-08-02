import os
import string

from pypy.lang.prolog.interpreter.term import Term, Float, Number, Var, Atom
from pypy.lang.prolog.interpreter import error, helper, parsing
from pypy.lang.prolog.builtin.register import expose_builtin

class TermFormatter(object):
    def __init__(self, engine, quoted=False, max_depth=0,
                 ignore_ops=False):
        self.engine = engine
        self.quoted = quoted
        self.max_depth = max_depth
        self.ignore_ops = ignore_ops
        self.curr_depth = 0
        self._make_reverse_op_mapping()
        self.var_to_number = {}
    
    def from_option_list(engine, options):
        # XXX add numbervars support
        quoted = False
        max_depth = 0
        ignore_ops = False
        number_vars = False
        for option in options:
            if (not isinstance(option, Term) or len(option.args) != 1):
                error.throw_domain_error('write_option', option)
            arg = option.args[0]
            if option.name == "max_depth":
                try:
                    max_depth = helper.unwrap_int(arg)
                except error.CatchableError:
                    error.throw_domain_error('write_option', option)
            elif (not isinstance(arg, Atom) or
                (arg.name != "true" and arg.name != "false")):
                error.throw_domain_error('write_option', option)
                assert 0, "unreachable"
            elif option.name == "quoted":
                quoted = arg.name == "true"
            elif option.name == "ignore_ops":
                ignore_ops = arg.name == "true"
        return TermFormatter(engine, quoted, max_depth, ignore_ops)
    from_option_list = staticmethod(from_option_list)

    def format(self, term):
        self.curr_depth += 1
        if self.max_depth > 0 and self.curr_depth > self.max_depth:
            return "..."
        if isinstance(term, Atom):
            return self.format_atom(term.name)
        elif isinstance(term, Number):
            return self.format_number(term)
        elif isinstance(term, Float):
            return self.format_float(term)
        elif isinstance(term, Term):
            return self.format_term(term)
        elif isinstance(term, Var):
            return self.format_var(term)
        else:
            return '?'

    def format_atom(self, s):
        from pypy.rlib.parsing.deterministic import LexerError
        if self.quoted:
            try:
                tokens = parsing.lexer.tokenize(s)
                if (len(tokens) == 1 and tokens[0].name == 'ATOM' and
                    tokens[0].source == s):
                    return s
            except LexerError:
                pass
            return "'%s'" % (s, )
        return s

    def format_number(self, num):
        return str(num.num)

    def format_float(self, num):
        return str(num.floatval)

    def format_var(self, var):
        try:
            num = self.var_to_number[var]
        except KeyError:
            num = self.var_to_number[var] = len(self.var_to_number)
        return "_G%s" % (num, )

    def format_term_normally(self, term):
        return "%s(%s)" % (self.format_atom(term.name),
                           ", ".join([self.format(a) for a in term.args]))

    def format_term(self, term):
        if self.ignore_ops:
            return self.format_term_normally(term)
        else:
            return self.format_with_ops(term)[1]

    def format_with_ops(self, term):
        if not isinstance(term, Term):
            return (0, self.format(term))
        if term.signature == "./2":
            result = ["["]
            while isinstance(term, Term) and term.signature == "./2":
                first = term.args[0]
                second = term.args[1]
                result.append(self.format(first))
                result.append(", ")
                term = second
            if isinstance(term, Atom) and term.name == "[]":
                result[-1] = "]"
            else:
                result[-1] = "|"
                result.append(self.format(term))
                result.append("]")
            return (0, "".join(result))
        if (len(term.args), term.name) not in self.op_mapping:
            return (0, self.format_term_normally(term))
        form, prec = self.op_mapping[(len(term.args), term.name)]
        result = []
        assert 0 <= len(term.args) <= 2
        curr_index = 0
        for c in form:
            if c == "f":
                result.append(self.format_atom(term.name))
            else:
                childprec, child = self.format_with_ops(term.args[curr_index])
                parentheses = (c == "x" and childprec >= prec or
                               c == "y" and childprec > prec)
                if parentheses:
                    result.append("(")
                    result.append(child)
                    result.append(")")
                else:
                    result.append(child)
                curr_index += 1
        assert curr_index == len(term.args)
        return (prec, "".join(result))

    def _make_reverse_op_mapping(self):
        m = {}
        for prec, allops in self.engine.getoperations():
            for form, ops in allops:
                for op in ops:
                    m[len(form) - 1, op] = (form, prec)
        self.op_mapping = m

def impl_write_term(engine, term, options):
    f = TermFormatter.from_option_list(engine, options)
    os.write(1, f.format(term)) # XXX use streams
expose_builtin(impl_write_term, "write_term", unwrap_spec=["concrete", "list"])

def impl_nl(engine):
    os.write(1, "\n") # XXX use streams
expose_builtin(impl_nl, "nl", unwrap_spec=[])

def impl_write(engine, term):
    impl_write_term(engine, term, [])
expose_builtin(impl_write, "write", unwrap_spec=["raw"])


