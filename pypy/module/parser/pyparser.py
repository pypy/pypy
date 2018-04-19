from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.interpreter.pyparser import pyparse, pygram, error
from pypy.interpreter.astcompiler.astbuilder import ast_from_node
from pypy.interpreter.astcompiler.codegen import compile_ast
from rpython.rlib.objectmodel import specialize


class Cache:
    def __init__(self, space):
        self.error = space.new_exception_class("parser.ParserError")

def get_error(space):
    return space.fromcache(Cache).error


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

    @unwrap_spec(filename='fsencode')
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


@unwrap_spec(source='text')
def suite(space, source):
    return parse_python(space, source, 'exec')


@unwrap_spec(source='text')
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


def parser_error(space, w_tuple, message):
    raise OperationError(get_error(space), space.newtuple(
        [w_tuple, space.newtext(message)]))

def parse_error(space, message):
    return OperationError(get_error(space),
                         space.newtext(message))


def get_node_type(space, w_tuple):
    try:
        w_type = space.getitem(w_tuple, space.newint(0))
        return space.int_w(w_type)
    except OperationError:
        raise parser_error(space, w_tuple, "Illegal component tuple.")

class NodeState:
    def __init__(self):
        self.lineno = 0

def build_node_tree(space, w_tuple):
    type = get_node_type(space, w_tuple)
    node_state = NodeState()
    if 0 <= type < 256:
        # The tuple is simple, but it doesn't start with a start symbol.
        # Raise an exception now and be done with it.
        raise parser_error(space, w_tuple,
                           "Illegal syntax-tree; cannot start with terminal symbol.")
    node = pyparse.parser.Nonterminal(type)
    build_node_children(space, w_tuple, node, node_state)
    return node

def build_node_children(space, w_tuple, node, node_state):
    for w_elem in space.unpackiterable(w_tuple)[1:]:
        type = get_node_type(space, w_elem)
        if type < 256:  # Terminal node
            length = space.len_w(w_elem)
            if length == 2:
                _, w_obj = space.unpackiterable(w_elem, 2)
            elif length == 3:
                _, w_obj, w_lineno = space.unpackiterable(w_elem, 3)
            else:
                raise parse_error(
                    space, "terminal nodes must have 2 or 3 entries")
            strn = space.text_w(w_obj)
            child = pyparse.parser.Terminal(type, strn, node_state.lineno, 0)
        else:
            child = pyparse.parser.Nonterminal(type)
        node.append_child(child)
        if type >= 256:  # Nonterminal node
            build_node_children(space, w_elem, child, node_state)
        elif type == pyparse.pygram.tokens.NEWLINE:
            node_state.lineno += 1


def validate_node(space, tree):
    assert tree.type >= 256
    type = tree.type - 256
    parser = pyparse.PythonParser(space)
    if type >= len(parser.grammar.dfas):
        raise parse_error(space, "Unrecognized node type %d." % type)
    dfa = parser.grammar.dfas[type]
    # Run the DFA for this nonterminal
    arcs, is_accepting = dfa.states[0]
    for pos in range(tree.num_children()):
        ch = tree.get_child(pos)
        for i, next_state in arcs:
            label = parser.grammar.labels[i]
            if label == ch.type:
                # The child is acceptable; validate it recursively
                if ch.type >= 256:
                    validate_node(space, ch)
                # Update the state, and move on to the next child.
                arcs, is_accepting = dfa.states[next_state]
                break
        else:
            raise parse_error(space, "Illegal node")
    if not is_accepting:
        raise parse_error(space, "Illegal number of children for %d node" %
                          tree.type)


def tuple2st(space, w_sequence):
    # Convert the tree to the internal form before checking it
    tree = build_node_tree(space, w_sequence)
    validate_node(space, tree)
    return W_STType(tree, 'eval')
