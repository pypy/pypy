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

    def visitField(self, field):
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
        self.make_var_syncer(product.fields, product, name)

    def make_var_syncer(self, fields, node, name):
        self.emit("def sync_app_attrs(self, space):", 1)
        config = (self.data.optional_masks[node],
                  self.data.required_masks[node])
        self.emit("if (self.initialization_state & ~%i) ^ %i:" % config, 2)
        names = []
        for field in fields:
            if field.opt:
                names.append("None")
            else:
                names.append(repr(field.name.value))
        sub = (", ".join(names), name.value)
        self.emit("missing_field(space, self.initialization_state, [%s], %r)"
                  % sub, 3)
        self.emit("else:", 2)
        # Fill in all the default fields.
        doing_something = False
        for field in fields:
            if field.opt:
                doing_something = True
                flag = self.data.field_masks[field]
                self.emit("if not self.initialization_state & %i:" % (flag,), 3)
                default = "0" if field.type.value == "int" else "None"
                self.emit("self.%s = %s" % (field.name, default), 4)
        if not doing_something:
            self.emit("pass", 3)
        for attr in fields:
            if attr.seq:
                self.emit("w_list = self.w_%s" % (attr.name,), 2)
                self.emit("if w_list is not None:", 2)
                self.emit("list_w = space.listview(w_list)", 3)
                self.emit("if list_w:", 3)
                unwrapper = get_unwrapper(attr.type.value, "w_obj",
                                          self.data.simple_types)
                config = (attr.name, unwrapper)
                self.emit("self.%s = [%s for w_obj in list_w]" % config,
                          4),
                self.emit("else:", 3)
                self.emit("self.%s = None" % (attr.name,), 4)
                if attr.type.value not in asdl.builtin_types and \
                        attr.type.value not in self.data.simple_types:
                    self.emit("if self.%s is not None:" % (attr.name,), 2)
                    self.emit("for node in self.%s:" % (attr.name,), 3)
                    self.emit("node.sync_app_attrs(space)", 4)
            elif attr.type.value not in asdl.builtin_types and \
                    attr.type.value not in self.data.simple_types:
                doing_something = True
                level = 2
                if attr.opt:
                    self.emit("if self.%s:" % (attr.name,), 2)
                    level += 1
                self.emit("self.%s.sync_app_attrs(space)" % (attr.name,), level)
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
        else:
            self.emit("def __init__(self):", 1)
        have_everything = self.data.required_masks[node] | \
            self.data.optional_masks[node]
        self.emit("self.initialization_state = %i" % (have_everything,), 2)
    
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
        for field in self.data.cons_attributes[cons]:
            subst = (field.name, self.data.field_masks[field])
            self.emit("_%s_mask = %i" % subst, 1)
        self.emit("")
        self.make_constructor(cons.fields, cons, extra_attributes, base)
        self.emit("")
        self.emit("def walkabout(self, visitor):", 1)
        self.emit("visitor.visit_%s(self)" % (cons.name,), 2)
        self.emit("")
        self.make_mutate_over(cons, cons.name)
        self.make_var_syncer(cons.fields + self.data.cons_attributes[cons],
                             cons, cons.name)

    def visitField(self, field):
        self.emit("self.%s = %s" % (field.name, field.name), 2)
        if field.seq:
            self.emit("self.w_%s = None" % (field.name,), 2)


class ASTVisitorVisitor(ASDLVisitor):
    """A meta visitor! :)"""

    def visitModule(self, mod):
        self.emit("class ASTVisitor(object):")
        self.emit("")
        self.emit("def visit_sequence(self, seq):", 1)
        self.emit("for node in seq:", 2)
        self.emit("node.walkabout(self)", 3)
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
            if field.seq or field.opt:
                self.emit("if node.%s:" % (field.name,), 2)
                level = 3
            else:
                level = 2
            if field.seq:
                template = "self.visit_sequence(node.%s)"
            else:
                template = "node.%s.walkabout(self)"
            self.emit(template % (field.name,), level)
            return True
        return False


asdl_type_map = {
    "int" : "int_w",
    "identifier" : "str_w",
    "bool" : "bool_w"
}

def get_unwrapper(tp, name, simple_types):
    if tp in asdl.builtin_types:
        return "space.%s(%s)" % (asdl_type_map[tp], name)
    elif tp in simple_types:
        return "space.interp_w(%s, %s).to_simple_int(space)" % (tp, name)
    else:
        return "space.interp_w(%s, %s)" % (tp, name)


# CPython lets blank AST nodes (no constructor arguments) be created
# and the attributes added later.  In CPython, it is implemented by
# implementing applevel and c level AST as different structures and
# copying between them.  This is hideous, so we use a slightly less
# ugly hack in PyPy.  Each field has a bitmask which is set on the
# initialization_state attribute when the field type is set.  When
# sync_app_attrs() is called, it's a simple matter of removing the
# optional field flags from initialization_state, and using XOR to
# test if all the required fields have been set.
class AppExposeVisitor(ASDLVisitor):

    def visitType(self, tp):
        super(AppExposeVisitor, self).visitType(tp, tp.name)

    def visitSum(self, sum, name):
        for field in sum.attributes:
            self.make_property(field, name, True)
        self.make_typedef(name, "AST", sum.attributes,
                          fields_name="_attributes")
        if not is_simple_sum(sum):
            super(AppExposeVisitor, self).visitSum(sum, name)
        else:
            for cons in sum.types:
                self.make_typedef("_" + cons.name.value, name, (), cons.name,
                                  concrete=True)

    def make_typedef(self, name, base, fields, display_name=None,
                     fields_name="_fields", concrete=False, needs_init=False):
        if display_name is None:
            display_name = name
        self.emit("%s.typedef = typedef.TypeDef(\"%s\"," % (name, display_name))
        self.emit("%s.typedef," % (base,), 1)
        self.emit("__module__='_ast',", 1)
        comma_fields = ", ".join(repr(field.name.value) for field in fields)
        self.emit("%s=_FieldsWrapper([%s])," % (fields_name, comma_fields), 1)
        for field in fields:
            getter = "%s_get_%s" % (name, field.name)
            setter = "%s_set_%s" % (name, field.name)
            config = (field.name, getter, setter, name)
            self.emit("%s=typedef.GetSetProperty(%s, %s, cls=%s)," % config, 1)
        self.emit("__new__=interp2app(get_AST_new(%s))," % (name,), 1)
        if needs_init:
            self.emit("__init__=interp2app(%s_init)," % (name,), 1)
        self.emit(")")
        self.emit("")

    def make_init(self, name, fields):
        comma_fields = ", ".join(repr(field.name.value) for field in fields)
        if fields:
            config = (name, comma_fields)
            self.emit("_%s_field_unroller = unrolling_iterable([%s])" % config)
        self.emit("def %s_init(space, w_self, __args__):" % (name,))
        self.emit("w_self = space.descr_self_interp_w(%s, w_self)" % (name,), 1)
        for field in fields:
            if field.seq:
                self.emit("w_self.w_%s = None" % (field.name,), 1)
        self.emit("args_w, kwargs_w = __args__.unpack()", 1)
        self.emit("if args_w:", 1)
        arity = len(fields)
        if arity:
            self.emit("if len(args_w) != %i:" % (arity,), 2)
            plural = arity > 1 and "s" or ""
            self.emit("w_err = space.wrap(\"%s constructor takes either 0 or %i " \
                          "positional argument%s\")" % (name, arity, plural), 3)
            self.emit("raise OperationError(space.w_TypeError, w_err)", 3)
            self.emit("i = 0", 2)
            self.emit("for field in _%s_field_unroller:" % (name,), 2)
            self.emit("space.setattr(w_self, space.wrap(field), args_w[i])", 3)
            self.emit("i += 1", 3)
        else:
            self.emit("w_err = space.wrap(\"%s constructor takes no " \
                          "arguments\")" % (name,), 2)
            self.emit("raise OperationError(space.w_TypeError, w_err)", 2)
        self.emit("for field, w_value in kwargs_w.iteritems():", 1)
        self.emit("space.setattr(w_self, space.wrap(field), w_value)", 2)
        self.emit("")

    def visitConstructor(self, cons, base):
        super(AppExposeVisitor, self).visitConstructor(cons, cons.name)
        self.make_init(cons.name, cons.fields)
        self.make_typedef(cons.name, base, cons.fields, concrete=True,
                          needs_init=True)

    def visitProduct(self, product, name):
        super(AppExposeVisitor, self).visitProduct(product, name)
        self.make_init(name, product.fields)
        self.make_typedef(name, "AST", product.fields, concrete=True,
                          needs_init=True)

    def visitField(self, field, name):
        self.make_property(field, name)

    def make_property(self, field, name, different_masks=False):
        func = "def %s_get_%s(space, w_self):" % (name, field.name)
        self.emit(func)
        if different_masks:
            flag = "w_self._%s_mask" % (field.name,)
        else:
            flag = self.data.field_masks[field]
        if not field.seq:
            self.emit("if w_self.w_dict is not None:", 1)
            self.emit("    w_obj = w_self.getdictvalue(space, '%s')" % (field.name,), 1)
            self.emit("    if w_obj is not None:", 1)
            self.emit("        return w_obj", 1)
        self.emit("if not w_self.initialization_state & %s:" % (flag,), 1)
        self.emit("typename = space.type(w_self).getname(space)", 2)
        self.emit("w_err = space.wrap(\"'%%s' object has no attribute '%s'\" %% typename)" %
                  (field.name,), 2)
        self.emit("raise OperationError(space.w_AttributeError, w_err)", 2)
        if field.seq:
            self.emit("if w_self.w_%s is None:" % (field.name,), 1)
            self.emit("if w_self.%s is None:" % (field.name,), 2)
            self.emit("w_list = space.newlist([])", 3)
            self.emit("else:", 2)
            if field.type.value in self.data.simple_types:
                wrapper = "%s_to_class[node - 1]()" % (field.type,)
            else:
                wrapper = "space.wrap(node)"
            self.emit("list_w = [%s for node in w_self.%s]" %
                      (wrapper, field.name), 3)
            self.emit("w_list = space.newlist(list_w)", 3)
            self.emit("w_self.w_%s = w_list" % (field.name,), 2)
            self.emit("return w_self.w_%s" % (field.name,), 1)
        elif field.type.value in self.data.simple_types:
            config = (field.type, field.name)
            self.emit("return %s_to_class[w_self.%s - 1]()" % config, 1)
        elif field.type.value in ("object", "string"):
            self.emit("return w_self.%s" % (field.name,), 1)
        else:
            self.emit("return space.wrap(w_self.%s)" % (field.name,), 1)
        self.emit("")

        func = "def %s_set_%s(space, w_self, w_new_value):" % (name, field.name)
        self.emit(func)
        if field.seq:
            self.emit("w_self.w_%s = w_new_value" % (field.name,), 1)
        else:
            save_original_object = False
            self.emit("try:", 1)
            if field.type.value not in asdl.builtin_types:
                # These are always other AST nodes.
                if field.type.value in self.data.simple_types:
                    self.emit("obj = space.interp_w(%s, w_new_value)" % \
                                  (field.type,), 2)
                    self.emit("w_self.%s = obj.to_simple_int(space)" %
                              (field.name,), 2)
                    save_original_object = True
                else:
                    config = (field.name, field.type, repr(field.opt))
                    self.emit("w_self.%s = space.interp_w(%s, w_new_value, %s)" %
                              config, 2)
            else:
                level = 2
                if field.opt and field.type.value != "int":
                    self.emit("if space.is_w(w_new_value, space.w_None):", 2)
                    self.emit("w_self.%s = None" % (field.name,), 3)
                    level += 1
                    self.emit("else:", 2)
                if field.type.value in ("object", "string"):
                    self.emit("w_self.%s = w_new_value" % (field.name,), level)
                else:
                    space_method = asdl_type_map[field.type.value]
                    config = (field.name, space_method)
                    self.emit("w_self.%s = space.%s(w_new_value)" % config, level)
            self.emit("except OperationError, e:", 1)
            self.emit("    if not e.match(space, space.w_TypeError):", 1)
            self.emit("        raise", 1)
            self.emit("    w_self.setdictvalue(space, '%s', w_new_value)"
                      % (field.name,), 1)
            self.emit("    return", 1)
            if save_original_object:
                self.emit("# need to save the original object too", 1)
                self.emit("w_self.setdictvalue(space, '%s', w_new_value)"
                          % (field.name,), 1)
            else:
                self.emit("w_self.deldictvalue(space, '%s')" %(field.name,), 1)
        self.emit("w_self.initialization_state |= %s" % (flag,), 1)
        self.emit("")


def copy_field(field):
    return asdl.Field(field.type, field.name, field.seq, field.opt)


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
                field_masks[field] = flag
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
                    for cons in sum.types:
                        attrs = [copy_field(field) for field in sum.attributes]
                        add_masks(cons.fields + attrs, cons)
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
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import typedef
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError
from pypy.rlib.unroll import unrolling_iterable
from pypy.tool.pairtype import extendabletype
from pypy.tool.sourcetools import func_with_new_name


class AST(Wrappable):

    w_dict = None

    __metaclass__ = extendabletype

    def walkabout(self, visitor):
        raise AssertionError("walkabout() implementation not provided")

    def mutate_over(self, visitor):
        raise AssertionError("mutate_over() implementation not provided")

    def sync_app_attrs(self, space):
        raise NotImplementedError

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


class NodeVisitorNotImplemented(Exception):
    pass


class _FieldsWrapper(Wrappable):
    "Hack around the fact we can\'t store tuples on a TypeDef."

    def __init__(self, fields):
        self.fields = fields

    def __spacebind__(self, space):
        return space.newtuple([space.wrap(field) for field in self.fields])


def get_AST_new(node_class):
    def generic_AST_new(space, w_type, __args__):
        node = space.allocate_instance(node_class, w_type)
        node.initialization_state = 0
        return space.wrap(node)
    return func_with_new_name(generic_AST_new, "new_%s" % node_class.__name__)

def AST_init(space, w_self, __args__):
    args_w, kwargs_w = __args__.unpack()
    if args_w and len(args_w) != 0:
        w_err = space.wrap("_ast.AST constructor takes 0 positional arguments")
        raise OperationError(space.w_TypeError, w_err)
    for field, w_value in kwargs_w.iteritems():
        space.setattr(w_self, space.wrap(field), w_value)

AST.typedef = typedef.TypeDef("AST",
    _fields=_FieldsWrapper([]),
    _attributes=_FieldsWrapper([]),
    __module__='_ast',
    __reduce__=interp2app(AST.reduce_w),
    __setstate__=interp2app(AST.setstate_w),
    __dict__ = typedef.GetSetProperty(typedef.descr_get_dict,
                                      typedef.descr_set_dict, cls=AST),
    __new__=interp2app(get_AST_new(AST)),
    __init__=interp2app(AST_init),
)


def missing_field(space, state, required, host):
    "Find which required field is missing."
    for i in range(len(required)):
        if not (state >> i) & 1:
            missing = required[i]
            if missing is not None:
                 err = "required field \\"%s\\" missing from %s"
                 err = err % (missing, host)
                 w_err = space.wrap(err)
                 raise OperationError(space.w_TypeError, w_err)
    raise AssertionError("should not reach here")


"""

visitors = [ASTNodeVisitor, ASTVisitorVisitor, GenericASTVisitorVisitor,
            AppExposeVisitor]


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
