"""
Generate AST node definitions from an ASDL description.
"""

import sys
import os
import asdl


class ASDLVisitor(asdl.VisitorBase):

    def __init__(self, stream, data):
        super(ASDLVisitor, self).__init__()
        self.stream = stream
        self.data = data

    def visitModule(self, mod, *args):
        for df in mod.dfns:
            self.visit(df, *args)

    def visitSum(self, sum, *args):
        for tp in sum.types:
            self.visit(tp, *args)

    def visitType(self, tp, *args):
        self.visit(tp.value, *args)

    def visitProduct(self, prod, *args):
        for field in prod.fields:
            self.visit(field, *args)

    def visitConstructor(self, cons, *args):
        for field in cons.fields:
            self.visit(field, *args)

    def visitField(self, field, *args):
        pass

    def emit(self, line, level=0):
        indent = "    "*level
        self.stream.write(indent + line + "\n")


def is_simple_sum(sum):
    assert isinstance(sum, asdl.Sum)
    for constructor in sum.types:
        if constructor.fields:
            return False
    return True


class ASTNodeVisitor(ASDLVisitor):

    def visitType(self, tp):
        self.visit(tp.value, tp.name)

    def visitSum(self, sum, base):
        if is_simple_sum(sum):
            self.emit("class %s(AST):" % (base,))
            self.emit("")
            self.emit("def to_simple_int(self, space):", 1)
            self.emit("w_msg = space.wrap(\"not a valid %s\")" % (base,), 2)
            self.emit("raise OperationError(space.w_TypeError, w_msg)", 2)
            self.emit("")
            for i, cons in enumerate(sum.types):
                self.emit("class _%s(%s):" % (cons.name, base))
                self.emit("")
                self.emit("def to_simple_int(self, space):", 1)
                self.emit("return %i" % (i + 1,), 2)
                self.emit("")
            for i, cons in enumerate(sum.types):
                self.emit("%s = %i" % (cons.name, i + 1))
            self.emit("")
            self.emit("%s_to_class = [" % (base,))
            for cons in sum.types:
                self.emit("_%s," % (cons.name,), 1)
            self.emit("]")
            self.emit("")
        else:
            self.emit("class %s(AST):" % (base,))
            if sum.attributes:
                self.emit("")
                args = ", ".join(attr.name.value for attr in sum.attributes)
                self.emit("def __init__(self, %s):" % (args,), 1)
                for attr in sum.attributes:
                    self.visit(attr)
                self.emit("")
            else:
                self.emit("pass", 1)
                self.emit("")
            for cons in sum.types:
                self.visit(cons, base, sum.attributes)
                self.emit("")

    def visitProduct(self, product, name):
        self.emit("class %s(AST):" % (name,))
        self.emit("")
        self.make_constructor(product.fields, product)
        self.emit("")
        self.make_mutate_over(product, name)
        self.emit("def walkabout(self, visitor):", 1)
        self.emit("visitor.visit_%s(self)" % (name,), 2)
        self.emit("")

    def make_constructor(self, fields, node, extras=None, base=None):
        if fields or extras:
            arg_fields = fields + extras if extras else fields
            args = ", ".join(str(field.name) for field in arg_fields)
            self.emit("def __init__(self, %s):" % args, 1)
            for field in fields:
                self.visit(field)
            if extras:
                base_args = ", ".join(str(field.name) for field in extras)
                self.emit("%s.__init__(self, %s)" % (base, base_args), 2)
    
    def make_mutate_over(self, cons, name):
        self.emit("def mutate_over(self, visitor):", 1)
        for field in cons.fields:
            if (field.type.value not in asdl.builtin_types and
                field.type.value not in self.data.simple_types):
                if field.opt or field.seq:
                    level = 3
                    self.emit("if self.%s:" % (field.name,), 2)
                else:
                    level = 2
                if field.seq:
                    sub = (field.name,)
                    self.emit("visitor._mutate_sequence(self.%s)" % sub, level)
                else:
                    sub = (field.name, field.name)
                    self.emit("self.%s = self.%s.mutate_over(visitor)" % sub,
                              level)
        self.emit("return visitor.visit_%s(self)" % (name,), 2)
        self.emit("")

    def visitConstructor(self, cons, base, extra_attributes):
        self.emit("class %s(%s):" % (cons.name, base))
        self.emit("")
        self.make_constructor(cons.fields, cons, extra_attributes, base)
        self.emit("")
        self.emit("def walkabout(self, visitor):", 1)
        self.emit("visitor.visit_%s(self)" % (cons.name,), 2)
        self.emit("")
        self.make_mutate_over(cons, cons.name)

    def visitField(self, field):
        self.emit("self.%s = %s" % (field.name, field.name), 2)


class ASTVisitorVisitor(ASDLVisitor):
    """A meta visitor! :)"""

    def visitModule(self, mod):
        self.emit("class ASTVisitor(object):")
        self.emit("")
        self.emit("def visit_sequence(self, seq):", 1)
        self.emit("if seq is not None:", 2)
        self.emit("for node in seq:", 3)
        self.emit("node.walkabout(self)", 4)
        self.emit("")
        self.emit("def default_visitor(self, node):", 1)
        self.emit("raise NodeVisitorNotImplemented", 2)
        self.emit("")
        self.emit("def _mutate_sequence(self, seq):", 1)
        self.emit("for i in range(len(seq)):", 2)
        self.emit("seq[i] = seq[i].mutate_over(self)", 3)
        self.emit("")
        super(ASTVisitorVisitor, self).visitModule(mod)
        self.emit("")

    def visitType(self, tp):
        if not (isinstance(tp.value, asdl.Sum) and
                is_simple_sum(tp.value)):
            super(ASTVisitorVisitor, self).visitType(tp, tp.name)

    def visitProduct(self, prod, name):
        self.emit("def visit_%s(self, node):" % (name,), 1)
        self.emit("return self.default_visitor(node)", 2)

    def visitConstructor(self, cons, _):
        self.emit("def visit_%s(self, node):" % (cons.name,), 1)
        self.emit("return self.default_visitor(node)", 2)


class GenericASTVisitorVisitor(ASDLVisitor):

    def visitModule(self, mod):
        self.emit("class GenericASTVisitor(ASTVisitor):")
        self.emit("")
        super(GenericASTVisitorVisitor, self).visitModule(mod)
        self.emit("")

    def visitType(self, tp):
        if not (isinstance(tp.value, asdl.Sum) and
                is_simple_sum(tp.value)):
            super(GenericASTVisitorVisitor, self).visitType(tp, tp.name)

    def visitProduct(self, prod, name):
        self.make_visitor(name, prod.fields)

    def visitConstructor(self, cons, _):
        self.make_visitor(cons.name, cons.fields)

    def make_visitor(self, name, fields):
        self.emit("def visit_%s(self, node):" % (name,), 1)
        have_body = False
        for field in fields:
            if self.visitField(field):
                have_body = True
        if not have_body:
            self.emit("pass", 2)
        self.emit("")

    def visitField(self, field):
        if field.type.value not in asdl.builtin_types and \
                field.type.value not in self.data.simple_types:
            level = 2
            template = "node.%s.walkabout(self)"
            if field.seq:
                template = "self.visit_sequence(node.%s)"
            elif field.opt:
                self.emit("if node.%s:" % (field.name,), 2)
                level = 3
            self.emit(template % (field.name,), level)
            return True
        return False


class ASDLData(object):

    def __init__(self, tree):
        simple_types = set()
        prod_simple = set()
        field_masks = {}
        required_masks = {}
        optional_masks = {}
        cons_attributes = {}
        def add_masks(fields, node):
            required_mask = 0
            optional_mask = 0
            for i, field in enumerate(fields):
                flag = 1 << i
                if field not in field_masks:
                    field_masks[field] = flag
                else:
                    assert field_masks[field] == flag
                if field.opt:
                    optional_mask |= flag
                else:
                    required_mask |= flag
            required_masks[node] = required_mask
            optional_masks[node] = optional_mask
        for tp in tree.dfns:
            if isinstance(tp.value, asdl.Sum):
                sum = tp.value
                if is_simple_sum(sum):
                    simple_types.add(tp.name.value)
                else:
                    attrs = [field for field in sum.attributes]
                    for cons in sum.types:
                        add_masks(attrs + cons.fields, cons)
                        cons_attributes[cons] = attrs
            else:
                prod = tp.value
                prod_simple.add(tp.name.value)
                add_masks(prod.fields, prod)
        prod_simple.update(simple_types)
        self.cons_attributes = cons_attributes
        self.simple_types = simple_types
        self.prod_simple = prod_simple
        self.field_masks = field_masks
        self.required_masks = required_masks
        self.optional_masks = optional_masks


HEAD = """# Generated by tools/asdl_py.py
from pypy.interpreter.error import OperationError
from rpython.tool.pairtype import extendabletype


class AST(object):
    __metaclass__ = extendabletype

    def walkabout(self, visitor):
        raise AssertionError("walkabout() implementation not provided")

    def mutate_over(self, visitor):
        raise AssertionError("mutate_over() implementation not provided")


class NodeVisitorNotImplemented(Exception):
    pass

"""

visitors = [ASTNodeVisitor, ASTVisitorVisitor, GenericASTVisitorVisitor]


def main(argv):
    if len(argv) == 3:
        def_file, out_file = argv[1:]
    elif len(argv) == 1:
        print "Assuming default values of Python.asdl and ast.py"
        here = os.path.dirname(__file__)
        def_file = os.path.join(here, "Python.asdl")
        out_file = os.path.join(here, "..", "ast.py")
    else:
        print >> sys.stderr, "invalid arguments"
        return 2
    mod = asdl.parse(def_file)
    data = ASDLData(mod)
    fp = open(out_file, "w")
    try:
        fp.write(HEAD)
        for visitor in visitors:
            visitor(fp, data).visit(mod)
    finally:
        fp.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
