import py

class Node(object):
    def view(self):
        from pypy.translator.tool.pygame import graphclient
        content = ["digraph G{"]
        content.extend(self.dot())
        content.append("}")
        p = py.test.ensuretemp("automaton").join("temp.dot")
        p.write("\n".join(content))
        graphclient.display_dot_file(str(p))

class Symbol(Node):

    def __init__(self, symbol, additional_info, token):
        self.symbol = symbol
        self.additional_info = additional_info
        self.token = token
    
    def __repr__(self):
        return "Symbol(%r, %r)" % (self.symbol, self.additional_info)

    def dot(self):
        addinfo = str(self.additional_info).replace('"', "'") or "_"
        yield ('"%s" [label="%r%r"];' % (
            id(self), self.symbol, addinfo)).replace("\\", "\\\\")

    def visit(self, visitor):
        if isinstance(visitor, RPythonVisitor):
            visitor.dispatch(self)
        method = getattr(visitor, "visit_" + self.symbol, None)
        if method is None:
            return self
        return method(self)

class Nonterminal(Node):
    def __init__(self, symbol, children):
        self.children = children
        self.symbol = symbol

    def __str__(self):
        return "%s(%s)" % (self.symbol, ", ".join([str(c) for c in self.children]))

    def __repr__(self):
        return "Nonterminal(%r, %r)" % (self.children, self.symbol)

    def dot(self):
        yield '"%s" [label="%s"];' % (id(self), self.symbol)
        for child in self.children:
            yield '"%s" -> "%s";' % (id(self), id(child))
            for line in child.dot():
                yield line

    def visit(self, visitor):
        if isinstance(visitor, RPythonVisitor):
            visitor.dispatch(self)
        general = getattr(visitor, "visit", None)
        if general is None:
            return getattr(visitor, "visit_" + self.symbol)(self)
        else:
            specific = getattr(visitor, "visit_" + self.symbol, None)
            if specific is None:
                return general(self)
            else:
                return specific(self)

class Epsilon(Node):
    pass

class VisitError(Exception):
    def __init__(self, node):
        self.node = node
        self.args = (node, )

    def __str__(self):
        return "could not visit %s" % (self.node, )

def make_dispatch_function(dispatch_table):
    code = ["def dispatch(self, node):"]
    code.append("    if isinstance(node, Nonterminal):")
    code.append("        if node.symbol not in self.dispatch_table:")
    if "__general_nonterminal_visit" in dispatch_table:
        code.append(
                "            return self.dispatch_table['__general_nonterminal_visit'](self, node)")
    elif "__general_visit" in dispatch_table:
        code.append(
                "            return self.dispatch_table['__general_visit'](self, node)")
    else:
        code.append("            raise VisitError(node)")
    code.append("        else:")
    code.append("            return self.dispatch_table[node.symbol](self, node)")
    code.append("    if isinstance(node, Symbol):")
    code.append("        if node.symbol not in self.dispatch_table:")
    if "__general_symbol_visit" in dispatch_table:
        code.append(
                "            return self.dispatch_table['__general_symbol_visit'](self, node)")
    elif "__general_visit" in dispatch_table:
        code.append(
                "            return self.dispatch_table['__general_visit'](self, node)")
    else:
        code.append("              raise VisitError(node)")
    code.append("        else:")
    code.append("            return self.dispatch_table[node.symbol](self, node)")
    code.append("    raise VisitError(node)")
    exec py.code.Source("\n".join(code)).compile()
    return dispatch

class CreateDispatchDictionaryMetaclass(type):
    def __new__(cls, name_, bases, dct):
        dispatch_table = {}
        for name, value in dct.iteritems():
            if name.startswith("visit_"):
                dispatch_table[name[len("visit_"):]] = value
        for special in ["general_symbol_visit",
                        "general_nonterminal_visit",
                        "general_visit"]:
            if special in dct:
                dispatch_table["__" + special] = dct[special]
        dct["dispatch_table"] = dispatch_table
        dct["dispatch"] = make_dispatch_function(dispatch_table)
        return type.__new__(cls, name_, bases, dct)

class RPythonVisitor(object):
    __metaclass__ = CreateDispatchDictionaryMetaclass

    def dispatch(self, node):
        if isinstance(node, Nonterminal):
            if node.symbol not in self.dispatch_table:
                raise VisitError(node)
            else:
                return self.dispatch_table[node.symbol](self, node)
        elif isinstance(node, Symbol):
            if node.symbol not in self.dispatch_table:
                if "__general_symbol" in self.dispatch_table:
                    return self.dispatch_table["__general_symbol"](self, node)
                raise VisitError(node)
            else:
                return self.dispatch_table[node.symbol](self, node)

        else:
            raise VisitError(node)
