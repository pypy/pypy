import autopath
from pypy.lang.prolog.interpreter.parsing import OrderTransformer, make_default_operations, unescape
from pypy.rlib.parsing.tree import Nonterminal, Symbol, RPythonVisitor

class ASTTermBuilder(RPythonVisitor):

    def __init__(self):
        self.varname_to_var = {}

    def build(self, s):
        "NOT_RPYTHON"
        if isinstance(s, list):
            return self.build_many(s)
        return self.build_query(s)

    def build_many(self, trees):
        ot = OrderTransformer()
        facts = []
        for tree in trees:
            s = ot.transform(tree)
            facts.append(self.build_fact(s))
        return facts

    def build_query(self, s):
        ot = OrderTransformer()
        s = ot.transform(s)
        return self.visit(s.children[0])

    def build_fact(self, node):
        self.varname_to_var = {}
        return self.visit(node.children[0])

    def visit(self, node):
        node = self.find_first_interesting(node)
        return self.dispatch(node)

    def general_nonterminal_visit(self, node):
        children = []
        name = ""
        token = None
        for child in node.children:
            if isinstance(child, Symbol):
                name = self.general_symbol_visit(child).name
                token = self.make_token(child)
            else:
                children.append(child)
        children = [self.visit(child) for child in children]
        if len(children) == 1 and (name == "-" or name == "+"):
            if name == "-":
                factor = -1
            else:
                factor = 1
            child = children[0]
            if isinstance(child, Number):
                child.value *= factor
                return child
            if isinstance(child, Float):
                child.value *= factor
                return child
        result = Term()
        result.setup(token, children, name)
        return result

    def build_list(self, node):
        result = []
        while node is not None:
            node = self._build_list(node, result)
        return result

    def _build_list(self, node, result):
        node = self.find_first_interesting(node)
        if isinstance(node, Nonterminal):
            child = node.children[1]
            if (isinstance(child, Symbol) and
                node.children[1].additional_info == ","):
                element = self.visit(node.children[0])
                result.append(element)
                return node.children[2]
        result.append(self.visit(node))

    def find_first_interesting(self, node):
        if isinstance(node, Nonterminal) and len(node.children) == 1:
            return self.find_first_interesting(node.children[0])
        return node

    def general_symbol_visit(self, node):
        if node.additional_info.startswith("'"):
            end = len(node.additional_info) - 1
            assert end >= 0
            name = unescape(node.additional_info[1:end])
        else:
            name = node.additional_info
        result = Atom()
        result.setup(self.make_token(node), name)
        return result

    def visit_VAR(self, node):
        varname = node.additional_info
        result = Var()
        result.setup(self.make_token(node), varname)
        return result

    def visit_NUMBER(self, node):
        s = node.additional_info
        try:
            result = Number()
            result.setup(self.make_token(node), int(s))
            return result
        except ValueError:
            result = Float()
            result.setup(self.make_token(node), float(s))
            return result

    def visit_complexterm(self, node):
        name = self.general_symbol_visit(node.children[0]).name
        children = self.build_list(node.children[2])
        result = Term()
        result.setup(self.make_token(node.children[1]), children, name)
        return result

    def visit_expr(self, node):
        if node.children[0].additional_info == '-':
            result = self.visit(node.children[1])
            if isinstance(result, Number):
                result.value = -result.value
            elif isinstance(result, Float):
                result.value = -result.value
        return self.visit(node.children[1])

    def visit_listexpr(self, node):
        node = node.children[1]
        if len(node.children) == 1:
            l = self.build_list(node)
            start = Atom()
            start.setup(None, "[]")
        else:
            l = self.build_list(node.children[0])
            start = self.visit(node.children[2])
        l.reverse()
        curr = start
        for elt in l:
            curr = Term()
            curr.setup(None, [elt, curr], ".")
        return curr

    def make_token(self, node):
        token = Token()
        source_pos = node.token.source_pos
        token.setup(node.token.source, source_pos.i, source_pos.lineno,
                    source_pos.columnno)
        return token
                    

class Token(object):
    def __init__(self):
        pass

    def setup(self, text, startpos, line, column):
        self.text = text
        self.startpos = startpos
        self.line = line
        self.column = column

class Node(object):
    def __init__(self):
        self.children = [None] # trick the annotator

    def setup(self, token, children=None):
        self.token = token
        if children is not None:
            self.children = children
        else:
            self.children = []

    def num_children(self):
        return len(self.children)

    def get_child(self, i):
        return self.children[i]

class Atom(Node):
    def __init__(self):
        pass
    def setup(self, token, name):
        Node.setup(self, token)
        self.name = name

class Number(Node):
    def __init__(self):
        pass
    def setup(self, token, value):
        Node.setup(self, token)
        self.value = value

class Float(Node):
    def __init__(self):
        pass
    def setup(self, token, value):
        Node.setup(self, token)
        self.value = value

class Var(Node):
    def __init__(self):
        pass
    def setup(self, token, varname):
        Node.setup(self, token)
        self.varname = varname

class Term(Node):
    def __init__(self):
        pass
    def setup(self, token, children, name):
        Node.setup(self, token, children)
        self.name = name


class Lines(object):
    def __init__(self):
        self.parser = None
        self.operations = make_default_operations()
        self.terms = []

    def num_terms(self):
        return len(self.terms)

    def get_term(self, i):
        return self.terms[i]

class ParseError(Exception):
    def __init__(self, pos, reason):
        self.pos = pos
        self.reason = reason
        self.args = (pos, reason)


def _build_and_run(lines, tree):
    from pypy.lang.prolog.interpreter.parsing import TermBuilder
    builder = ASTTermBuilder()
    term = builder.build_query(tree)
    if (isinstance(term, Term) and term.name == ":-" and
            len(term.children) == 1):
        child = term.get_child(0)
        if isinstance(child, Term) and child.name == "op":
            if len(child.children) != 3:
                raise ParseError(child.token.startpos, "expecting three arguments")
            precedence = child.children[0]
            form = child.children[1]
            name = child.children[2]
            if not isinstance(precedence, Number):
                raise ParseError(precedence.token.startpos, "first argument to op should be number")
            if not isinstance(form, Atom):
                raise ParseError(precedence.token.startpos, "second argument to op should be atom")
            if not isinstance(name, Atom):
                raise ParseError(precedence.token.startpos, "third argument to op should be atom")
            parser = impl_op(lines.operations, precedence.value, form.name, name.name)
            lines.parser = parser

    lines.terms.append(term)
    return lines.parser

def parse(s):
    from pypy.lang.prolog.interpreter.parsing import parse_file
    lines = Lines()
    trees = parse_file(s, lines.parser, _build_and_run, lines)
    return lines


def impl_op(operations, precedence, typ, name):
    from pypy.lang.prolog.interpreter import parsing
    precedence_to_ops = {}
    for prec, allops in operations:
        precedence_to_ops[prec] = allops
        for form, ops in allops:
            try:
                index = ops.index(name)
                del ops[index]
            except ValueError:
                pass
    if precedence != 0:
        if precedence in precedence_to_ops:
            allops = precedence_to_ops[precedence]
            for form, ops in allops:
                if form == typ:
                    ops.append(name)
                    break
            else:
                allops.append((typ, [name]))
        else:
            for i in range(len(operations)):
                (prec, allops) = operations[i]
                if precedence > prec:
                    operations.insert(i, (precedence, [(typ, [name])]))
                    break
            else:
                operations.append((precedence, [(typ, [name])]))
    return parsing.make_parser_at_runtime(operations)


if __name__ == '__main__':
    x = parse(":- op(900, xfx, hello). a hello b.")
