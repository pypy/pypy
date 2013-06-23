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
            self.emit("State.ast_type('%s', 'AST')" % (base,))
            self.emit("")
            for i, cons in enumerate(sum.types):
                self.emit("class _%s(%s):" % (cons.name, base))
                self.emit("")
                self.emit("def to_simple_int(self, space):", 1)
                self.emit("return %i" % (i + 1,), 2)
                self.emit("State.ast_type('%s', '%s')" % (cons.name, base))
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
            else:
                self.emit("pass", 1)
            self.emit("State.ast_type('%r', 'AST')" % (base,))
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
        self.make_converters(product.fields, name)
        self.emit("State.ast_type('%r', 'AST')" % (name,))
        self.emit("")

    def get_field_converter(self, field):
        if field.seq:
            lines = []
            lines.append("if self.%s is None:" % field.name)
            lines.append("    %s_w = []" % field.name)
            lines.append("else:")
            if field.type.value in self.data.simple_types:
                wrapper = "%s_to_class[node - 1]()" % (field.type,)
            elif field.type.value in ("object", "string"):
                wrapper = "node"
            else:
                wrapper = "node.to_object(space)"
            lines.append("    %s_w = [%s for node in self.%s] # %s" %
                         (field.name, wrapper, field.name, field.type))
            lines.append("w_%s = space.newlist(%s_w)" % (field.name, field.name))
            return lines
        elif field.type.value in self.data.simple_types:
            return ["w_%s = %s_to_class[self.%s - 1]()" % 
                    (field.name, field.type, field.name)]
        elif field.type.value in ("object", "string"):
            return ["w_%s = self.%s" % (field.name, field.name)]
        elif field.type.value in ("identifier",):
            return ["w_%s = space.wrap(self.%s)" % (field.name, field.name)]
        else:
            return ["w_%s = self.%s.to_object(space)  # %s" %
                    (field.name, field.name, field.type)]

    def make_converters(self, fields, name):
        self.emit("def to_object(self, space):", 1)
        self.emit("w_node = space.call_function(get(space).w_%s)" % name, 2)
        for field in fields:
            wrapping_code = self.get_field_converter(field)
            for line in wrapping_code:
                self.emit(line, 2)
            self.emit("space.setattr(w_node, space.wrap(%r), w_%s)" % (
                    str(field.name), field.name), 2)
        self.emit("return w_node", 2)

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
        self.make_converters(cons.fields, cons.name)
        self.emit("State.ast_type('%r', '%s')" % (cons.name, base))
        self.emit("")

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
        if (field.type.value not in asdl.builtin_types and 
            field.type.value not in self.data.simple_types):
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
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter import typedef
from pypy.interpreter.gateway import interp2app
from rpython.tool.sourcetools import func_with_new_name


class AST(object):
    __metaclass__ = extendabletype

    def walkabout(self, visitor):
        raise AssertionError("walkabout() implementation not provided")

    def mutate_over(self, visitor):
        raise AssertionError("mutate_over() implementation not provided")


class NodeVisitorNotImplemented(Exception):
    pass


class _FieldsWrapper(W_Root):
    "Hack around the fact we can't store tuples on a TypeDef."

    def __init__(self, fields):
        self.fields = fields

    def __spacebind__(self, space):
        return space.newtuple([space.wrap(field) for field in self.fields])


class W_AST(W_Root):
    w_dict = None

    def getdict(self, space):
        if self.w_dict is None:
            self.w_dict = space.newdict(instance=True)
        return self.w_dict

    def reduce_w(self, space):
        w_dict = self.w_dict
        if w_dict is None:
            w_dict = space.newdict()
        w_type = space.type(self)
        w_fields = w_type.getdictvalue(space, "_fields")
        for w_name in space.fixedview(w_fields):
            space.setitem(w_dict, w_name,
                          space.getattr(self, w_name))
        w_attrs = space.findattr(w_type, space.wrap("_attributes"))
        if w_attrs:
            for w_name in space.fixedview(w_attrs):
                space.setitem(w_dict, w_name,
                              space.getattr(self, w_name))
        return space.newtuple([space.type(self),
                               space.newtuple([]),
                               w_dict])

    def setstate_w(self, space, w_state):
        for w_name in space.unpackiterable(w_state):
            space.setattr(self, w_name,
                          space.getitem(w_state, w_name))

def get_W_AST_new(node_class):
    def generic_W_AST_new(space, w_type, __args__):
        node = space.allocate_instance(node_class, w_type)
        return space.wrap(node)
    return func_with_new_name(generic_W_AST_new, "new_%s" % node_class.__name__)


def W_AST_init(space, w_self, __args__):
    args_w, kwargs_w = __args__.unpack()
    if args_w and len(args_w) != 0:
        w_err = space.wrap("_ast.AST constructor takes 0 positional arguments")
        raise OperationError(space.w_TypeError, w_err)
    for field, w_value in kwargs_w.iteritems():
        space.setattr(w_self, space.wrap(field), w_value)


W_AST.typedef = typedef.TypeDef("AST",
    _fields=_FieldsWrapper([]),
    _attributes=_FieldsWrapper([]),
    __module__='_ast',
    __reduce__=interp2app(W_AST.reduce_w),
    __setstate__=interp2app(W_AST.setstate_w),
    __dict__ = typedef.GetSetProperty(typedef.descr_get_dict,
                                      typedef.descr_set_dict, cls=W_AST),
    __new__=interp2app(get_W_AST_new(W_AST)),
    __init__=interp2app(W_AST_init),
)

class State:
    AST_TYPES = []

    @classmethod
    def ast_type(cls, name, base):
        cls.AST_TYPES.append((name, base))

    def __init__(self, space):
        self.w_AST = space.gettypeobject(W_AST.typedef)
        for (name, base) in self.AST_TYPES:
            self.make_new_type(space, name, base)
        
    def make_new_type(self, space, name, base):
        w_base = getattr(self, 'w_%s' % base)
        w_type = space.call_function(
            space.w_type, 
            space.wrap(name), space.newtuple([w_base]), space.newdict())
        setattr(self, 'w_%s' % name, w_type)

def get(space):
    return space.fromcache(State)

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
