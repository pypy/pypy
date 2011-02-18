from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.interpreter.pyparser import pyparse, pygram, error
from pypy.interpreter.astcompiler.astbuilder import ast_from_node
from pypy.interpreter.astcompiler.codegen import compile_ast
from pypy.rlib.objectmodel import specialize


class STType(Wrappable):

    def __init__(self, tree, mode):
        self.tree = tree
        self.mode = mode

    @specialize.arg(3)
    def _build_app_tree(self, space, node, seq_maker, with_lineno, with_column):
        if node.children is not None:
            seq_w = [None]*(len(node.children) + 1)
            seq_w[0] = space.wrap(node.type)
            for i in range(1, len(node.children) + 1):
                seq_w[i] = self._build_app_tree(space, node.children[i - 1],
                                                seq_maker, with_lineno,
                                                with_column)
        else:
            seq_w = [None]*(2 + with_lineno + with_column)
            seq_w[0] = space.wrap(node.type)
            seq_w[1] = space.wrap(node.value)
            if with_lineno:
                seq_w[2] = space.wrap(node.lineno)
            if with_column:
                seq_w[3] = space.wrap(node.column)
        return seq_maker(seq_w)

    def descr_issuite(self, space):
        return space.wrap(self.tree.type == pygram.syms.file_input)

    def descr_isexpr(self, space):
        return space.wrap(self.tree.type == pygram.syms.eval_input)

    @unwrap_spec(line_info=bool, col_info=bool)
    def descr_totuple(self, space, line_info=False, col_info=False):
        return self._build_app_tree(space, self.tree, space.newtuple,
                                    line_info, col_info)

    @unwrap_spec(line_info=bool, col_info=bool)
    def descr_tolist(self, space, line_info=False, col_info=False):
        return self._build_app_tree(space, self.tree, space.newlist,
                                    line_info, col_info)

    @unwrap_spec(filename=str)
    def descr_compile(self, space, filename="<syntax-tree>"):
        info = pyparse.CompileInfo(filename, self.mode)
        try:
            ast = ast_from_node(space, self.tree, info)
            result = compile_ast(space, ast, info)
        except error.IndentationError, e:
            raise OperationError(space.w_IndentationError,
                                 e.wrap_info(space))
        except error.SyntaxError, e:
            raise OperationError(space.w_SyntaxError,
                                 e.wrap_info(space))
        return space.wrap(result)

STType.typedef = TypeDef("parser.st",
    issuite=interp2app(STType.descr_issuite),
    isexpr=interp2app(STType.descr_isexpr),
    totuple=interp2app(STType.descr_totuple),
    tolist=interp2app(STType.descr_tolist),
    compile=interp2app(STType.descr_compile)
)


def parse_python(space, source, mode):
    info = pyparse.CompileInfo("<string>", mode)
    parser = pyparse.PythonParser(space)
    try:
       tree = parser.parse_source(source, info)
    except error.IndentationError, e:
        raise OperationError(space.w_IndentationError,
                             e.wrap_info(space))
    except error.SyntaxError, e:
        raise OperationError(space.w_SyntaxError,
                             e.wrap_info(space))
    return space.wrap(STType(tree, mode))


@unwrap_spec(source=str)
def suite(space, source):
    return parse_python(space, source, 'exec')


@unwrap_spec(source=str)
def expr(space, source):
    return parse_python(space, source, 'eval')


@unwrap_spec(st=STType)
def isexpr(space, st):
    return space.call_method(st, "isexpr")

@unwrap_spec(st=STType)
def issuite(space, st):
    return space.call_method(st, "issuite")

@unwrap_spec(st=STType)
def st2tuple(space, st, __args__):
    return space.call_args(space.getattr(st, space.wrap("totuple")), __args__)

@unwrap_spec(st=STType)
def st2list(space, st, __args__):
    return space.call_args(space.getattr(st, space.wrap("tolist")), __args__)

@unwrap_spec(st=STType)
def compilest(space, st, __args__):
    return space.call_args(space.getattr(st, space.wrap("compile")), __args__)
