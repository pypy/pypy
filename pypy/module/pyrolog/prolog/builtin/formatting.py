import os
import string

from prolog.interpreter.term import Float, Number, Var, Atom, Callable, AttVar
from prolog.interpreter import error, helper, parsing
from prolog.builtin.register import expose_builtin
from prolog.interpreter.signature import Signature
from prolog.interpreter.stream import PrologStream

conssig = Signature.getsignature(".", 2)
nilsig = Signature.getsignature("[]", 0)
tuplesig = Signature.getsignature(",", 2)


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
            if (not helper.is_term(option) or (isinstance(option, Callable) and option.argument_count() != 1)):
                error.throw_domain_error('write_option', option)
            assert isinstance(option, Callable)
            arg = option.argument_at(0)
            if option.name()== "max_depth":
                try:
                    max_depth = helper.unwrap_int(arg)
                except error.CatchableError:
                    error.throw_domain_error('write_option', option)
            elif (not isinstance(arg, Atom) or
                (arg.name()!= "true" and arg.name()!= "false")):
                error.throw_domain_error('write_option', option)
                assert 0, "unreachable"
            elif option.name()== "quoted":
                quoted = arg.name()== "true"
            elif option.name()== "ignore_ops":
                ignore_ops = arg.name()== "true"
        return TermFormatter(engine, quoted, max_depth, ignore_ops)
    from_option_list = staticmethod(from_option_list)

    def format(self, term):
        self.curr_depth += 1
        term = term.dereference(None)
        if self.max_depth > 0 and self.curr_depth > self.max_depth:
            return "..."
        if isinstance(term, Atom):
            return self.format_atom(term.name())
        elif isinstance(term, Number):
            return self.format_number(term)
        elif isinstance(term, Float):
            return self.format_float(term)
        elif helper.is_term(term):
            assert isinstance(term, Callable)
            return self.format_term(term)
        elif isinstance(term, AttVar):
            return self.format_attvar(term)
        elif isinstance(term, Var):
            return self.format_var(term)
        elif isinstance(term, PrologStream):
            return self.format_stream(term)
        else:
            return '?'

    def format_atom(self, s):
        from rpython.rlib.parsing.deterministic import LexerError
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

    def format_attvar(self, attvar):
        l = []
        if attvar.value_list is not None:
            for name, index in attvar.attmap.indexes.iteritems():
                value = attvar.value_list[index]
                if value is not None:
                    l.append("put_attr(%s, %s, %s)" % (self.format_var(attvar),
                            name, self.format(value)))
        return "\n".join(l)

    def format_var(self, var):
        try:
            num = self.var_to_number[var]
        except KeyError:
            num = self.var_to_number[var] = len(self.var_to_number)
        return "_G%s" % (num, )

    def format_term_normally(self, term):
        return "%s(%s)" % (self.format_atom(term.name()),
                           ", ".join([self.format(a) for a in term.arguments()]))

    def format_term(self, term):
        if self.ignore_ops:
            return self.format_term_normally(term)
        else:
            return self.format_with_ops(term)[1]

    def format_stream(self, stream):
        return "'$stream'(%d)" % stream.fd()

    def format_with_ops(self, term):
        if not helper.is_term(term):
            return (0, self.format(term))
        assert isinstance(term, Callable)
        if term.signature().eq(conssig):
            result = ["["]
            while helper.is_term(term) and isinstance(term, Callable) and term.signature().eq(conssig):
                first = term.argument_at(0)
                second = term.argument_at(1)
                result.append(self.format(first))
                result.append(", ")
                term = second
            if isinstance(term, Atom) and term.signature().eq(nilsig):
                result[-1] = "]"
            else:
                result[-1] = "|"
                result.append(self.format(term))
                result.append("]")
            return (0, "".join(result))
        if term.signature().eq(tuplesig):
            result = ["("]
            while helper.is_term(term) and isinstance(term, Callable) and term.signature().eq(tuplesig):
                first = term.argument_at(0)
                second = term.argument_at(1)
                result.append(self.format(first))
                result.append(", ")
                term = second
            result.append(self.format(term))
            result.append(")")
            return (0, "".join(result))
        if (term.argument_count(), term.name()) not in self.op_mapping:
            return (0, self.format_term_normally(term))
        form, prec = self.op_mapping[(term.argument_count(), term.name())]
        result = []
        assert 0 <= term.argument_count() <= 2
        curr_index = 0
        for c in form:
            if c == "f":
                result.append(self.format_atom(term.name()))
            else:
                childprec, child = self.format_with_ops(term.argument_at(curr_index))
                parentheses = (c == "x" and childprec >= prec or
                               c == "y" and childprec > prec)
                if parentheses:
                    result.append("(")
                    result.append(child)
                    result.append(")")
                else:
                    result.append(child)
                curr_index += 1
        assert curr_index == term.argument_count()
        return (prec, "".join(result))

    def _make_reverse_op_mapping(self):
        m = {}
        for prec, allops in self.engine.getoperations():
            for form, ops in allops:
                for op in ops:
                    m[len(form) - 1, op] = (form, prec)
        self.op_mapping = m
