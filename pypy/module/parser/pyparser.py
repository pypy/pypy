from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.interpreter.pyparser import pyparse, pygram, error
from pypy.interpreter.astcompiler.astbuilder import ast_from_node
from pypy.interpreter.astcompiler.codegen import compile_ast
from rpython.rlib.objectmodel import specialize


class W_STType(W_Root):
    def __init__(self, tree, mode, recursive_parser=None):
        self.tree = tree
        self.mode = mode
        self.recursive_parser = recursive_parser

    @specialize.arg(3)
    def _build_app_tree(self, space, node, seq_maker, with_lineno, with_column):
        if node.num_children():
            seq_w = [None]*(node.num_children() + 1)
            seq_w[0] = space.newint(node.type)
            for i in range(1, node.num_children() + 1):
                seq_w[i] = self._build_app_tree(space, node.get_child(i - 1),
                                                seq_maker, with_lineno,
                                                with_column)
        else:
            seq_w = [None]*(2 + with_lineno + with_column)
            seq_w[0] = space.newint(node.type)
            seq_w[1] = space.newtext(node.get_value())
            if with_lineno:
                seq_w[2] = space.newint(node.get_lineno())
            if with_column:
                seq_w[3] = space.newint(node.get_column())
        return seq_maker(seq_w)

    def descr_issuite(self, space):
        return space.newbool(self.tree.type == pygram.syms.file_input)

    def descr_isexpr(self, space):
        return space.newbool(self.tree.type == pygram.syms.eval_input)

    @unwrap_spec(line_info=bool, col_info=bool)
    def descr_totuple(self, space, line_info=False, col_info=False):
        return self._build_app_tree(space, self.tree, space.newtuple,
                                    line_info, col_info)

    @unwrap_spec(line_info=bool, col_info=bool)
    def descr_tolist(self, space, line_info=False, col_info=False):
        return self._build_app_tree(space, self.tree, space.newlist,
                                    line_info, col_info)

    @unwrap_spec(filename='str0')
    def descr_compile(self, space, filename="<syntax-tree>"):
        info = pyparse.CompileInfo(filename, self.mode)
        try:
            ast = ast_from_node(space, self.tree, info, self.recursive_parser)
            result = compile_ast(space, ast, info)
        except error.IndentationError as e:
            raise OperationError(space.w_IndentationError,
                                 e.wrap_info(space))
        except error.SyntaxError as e:
            raise OperationError(space.w_SyntaxError,
                                 e.wrap_info(space))
        return result

W_STType.typedef = TypeDef("parser.st",
    issuite=interp2app(W_STType.descr_issuite),
    isexpr=interp2app(W_STType.descr_isexpr),
    totuple=interp2app(W_STType.descr_totuple),
    tolist=interp2app(W_STType.descr_tolist),
    compile=interp2app(W_STType.descr_compile)
)


def parse_python(space, source, mode):
    info = pyparse.CompileInfo("<string>", mode)
    parser = pyparse.PythonParser(space)
    try:
        tree = parser.parse_source(source, info)
    except error.IndentationError as e:
        raise OperationError(space.w_IndentationError,
                             e.wrap_info(space))
    except error.SyntaxError as e:
        raise OperationError(space.w_SyntaxError,
                             e.wrap_info(space))
    return W_STType(tree, mode, recursive_parser=parser)


@unwrap_spec(source=str)
def suite(space, source):
    return parse_python(space, source, 'exec')


@unwrap_spec(source=str)
def expr(space, source):
    return parse_python(space, source, 'eval')


@unwrap_spec(w_st=W_STType)
def isexpr(space, w_st):
    return w_st.descr_isexpr(space)

@unwrap_spec(w_st=W_STType)
def issuite(space, w_st):
    return w_st.descr_issuite(space)

@unwrap_spec(w_st=W_STType)
def st2tuple(space, w_st, __args__):
    return space.call_args(space.getattr(w_st, space.newtext("totuple")), __args__)

@unwrap_spec(w_st=W_STType)
def st2list(space, w_st, __args__):
    return space.call_args(space.getattr(w_st, space.newtext("tolist")), __args__)

@unwrap_spec(w_st=W_STType)
def compilest(space, w_st, __args__):
    return space.call_args(space.getattr(w_st, space.newtext("compile")), __args__)
