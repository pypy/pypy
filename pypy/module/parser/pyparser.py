#! /usr/bin/env python
# ______________________________________________________________________
"""Module pyparser.py
This module has parser module envy, but returns syntax trees as tuple/list's
as if st2tuple() was already called on the output.  It's only claim to fame
is that is done using Pure Python(tm) with none of those icky C extensions
making it run fast.
"""
# ______________________________________________________________________
# Module imports

from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.gateway import interp2app, applevel
from pypy.interpreter.error import OperationError 
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.typedef import interp_attrproperty, GetSetProperty
from pypy.interpreter.pycode import PyCode 

import token, compiler
import PyTokenizer, PyGrammar, DFAParser

# ______________________________________________________________________
# XXX What I really want to do is parameterize this module over an
# input grammar object.  Perhaps this can be done using an external
# class and then pyparser just calls into an instance of this class.

pygrammar = DFAParser.addAccelerators(PyGrammar.grammarObj)

# ______________________________________________________________________
# InternalParserError exception

class InternalParserError (Exception):
    """Class InternalParserError
    Exception class for parser errors (I assume).
    """

# ______________________________________________________________________

class STType (Wrappable):
    """Class STType
    """
    # ____________________________________________________________
    def __init__ (self, space, tup = None):
        """STType.__init__()
        Wrapper for parse tree data returned by DFAParser.

        Note that there is an implicit structure to the input tuple, which
        is not currently checked. (XXX - should this be checked ala
        sequence2st()?)
        """
        self.space = space 
        self.tup = tup

    # ____________________________________________________________
    def totuple (self, line_info = 0):
        """STType.totuple()
        Convert the ST object into a tuple representation.
        """
        return _st2tuple(self.tup, line_info)

    def descr_totuple(self, line_info = 0): 
        return self.space.wrap(self.totuple(line_info))
       
    descr_totuple.unwrap_spec=['self', int]

    # ____________________________________________________________
    def tolist (self, line_info = 0):
        """STType.tolist()
        Convert the ST object into a list representation.
        """
        return _st2list(self.tup, line_info)

    # ____________________________________________________________
    def isexpr (self):
        """STType.isexpr()
        Returns true if the root node in the syntax tree is an expr node,
        false otherwise.
        """
        global eval_input
        return self.tup[0][0] == eval_input

    # ____________________________________________________________
    def issuite (self):
        """STType.issuite()
        Returns true if the root node in the syntax tree is a suite node,
        false otherwise.
        """
        global file_input
        return self.tup[0][0] == file_input

    # ____________________________________________________________
    def descr_compile (self, w_filename = "<syntax_tree>"): 
        """STType.compile()
        """
        space = self.space 
        tup = self.totuple(line_info=1) 
        w_tup = space.wrap(tup)   
        w_compileAST = mycompile(space, w_tup, w_filename) 
        if self.isexpr(): 
            return exprcompile(space, w_compileAST) 
        else: 
            return modcompile(space, w_compileAST) 

app = applevel(""" 
    import compiler 
    def mycompile(tup, filename): 
        transformer = compiler.transformer.Transformer()
        compileAST = transformer.compile_node(tup) 
        compiler.misc.set_filename(filename, compileAST)
        return compileAST 

    def exprcompile(compileAST): 
        gen = compiler.pycodegen.ExpressionCodeGenerator(compileAST)
        return gen.getCode()

    def modcompile(compileAST): 
        gen = compiler.pycodegen.ModuleCodeGenerator(compileAST)
        return gen.getCode() 
""") 

mycompile = app.interphook("mycompile") 
exprcompile = app.interphook("exprcompile") 
modcompile = app.interphook("modcompile") 

STType.typedef = TypeDef("parser.st", 
    compile = interp2app(STType.descr_compile), 
    totuple = interp2app(STType.descr_totuple), 
) 

# ______________________________________________________________________

ASTType = STType

# ______________________________________________________________________

def _validateChildren (dfa, children):
    """_validateChildren()
    """
    global pygrammar
    classify = lambda sym, name : DFAParser.classify(pygrammar, sym, name)
    symbol_no, symbol_name, initial, states, first = dfa
    crnt_state = states[initial]
    for child in children:
        ((child_symbol, child_text, child_line_no), grandchildren) = child
        ilabel = classify(child_symbol, child_text)
        arcs, accel, accept = crnt_state
        next_state = None
        for (arc_label, arc_state) in arcs:
            if ilabel == arc_label:
                next_state = states[arc_state]
                break
        if next_state == None:
            raise InternalParserError("symbol %d should be in %s" %
                              (ilabel, str(arcs)))
        else:
            crnt_state = next_state
    if crnt_state[2] != 1:
        raise InternalParserError("incomplete sequence of children (ended with %s)" %
                          str(child[0]))

# ______________________________________________________________________

def _seq2st (seqobj):
    """_seq2st()
    This recursively translates the more svelte sequence syntax tree to the
    much more wasteful syntax tree representation returned by the parser
    machinery.
    This returns a pair consisting of a pair where the first item is the
    translated tree and the second item is the line number for the tree (this
    is used in an attempt to recursively reconstruct line number information
    for nonterminal symbols).
    """
    symbol_no = seqobj[0]
    if symbol_no >= token.NT_OFFSET:
        assert len(seqobj) > 1
        # This is going to create a list of pairs of (node, line_no) data:
        child_data = [_seq2st(child) for child in seqobj[1:]]
        children = map(lambda (x,y) : x, child_data)
        # Validate the children against the DFA for the non-terminal.
        dfa = DFAParser.findDFA(pygrammar, symbol_no)
        _validateChildren(dfa, children)
        # Compute a line number and create the actual node object.
        line_no = min(map(lambda (x, y) : y, child_data))
        node = ((symbol_no, '', line_no), children)
    else:
        if len(seqobj) == 3:
            node = (seqobj, [])
            line_no = seqobj[2]
        elif len(seqobj) == 2:
            node = ((symbol_no, seqobj[1], 0), [])
            line_no = 0
        else:
            raise InternalParserError("terminal nodes must have 2 or 3 entries")
    return node, line_no

# ______________________________________________________________________

def sequence2st (space, w_seqObj):
    """sequence2st()
    Do some basic checking on the input sequence and wrap in a STType.
    """
    try: 
        seqObj = space.unwrap(w_seqObj) 
        tup = _seq2st(seqObj)[0]
        if tup[0][0] not in (file_input, eval_input):
            raise InternalParserError("parse tree does not use a valid start symbol")
        return STType(space, tup)
    except InternalParserError, e: 
        reraise(space, e) 

sequence2ast = sequence2st
tuple2ast = sequence2st
tuple2st = sequence2st

# ______________________________________________________________________
# Okay, assume that the nonterminal numbers do not change.

def _findDFA (dfaName):
    """_findDFA
    Perform a string based search for a DFA index.
    """
    global pygrammar
    for dfa in pygrammar[0]:
        if dfa[1] == dfaName:
            return dfa[0]
    # XXX - Am I the right exception to be thrown?
    raise ValueError, ("Symbol %s has no corresponding DFA in the Python "
                       "grammar object!" % dfaName)

eval_input = _findDFA("eval_input")
file_input = _findDFA("file_input")

# ______________________________________________________________________

def _st2tuple (node, line_info = False):
    """return a tuple representation (ourself!)
    """
    ((symbolno, text, lineno), children) = node
    if symbolno >= token.NT_OFFSET:
        nextchildren = [symbolno]
        nextchildren += [_st2tuple(child, line_info) for child in children]
        return tuple(nextchildren)
    elif text == "\n":
        # XXX This is kinda a hack; can it be fixed somehow?
        return line_info and (symbolno, '', lineno) or (symbolno, '')
    #elif symbolno == token.ENDMARKER and line_info:
    #    # XXX Another hack to align line number of the end token.
    #    return (symbolno, '', lineno - 1)
    else:
        return line_info and (symbolno, text, lineno) or (symbolno, text)

# ______________________________________________________________________

def st2tuple (node, line_info = 0):
    """st2tuple()
    Do what parser.st2tuple() normally does.
    """
    return node.totuple(line_info)

ast2tuple = st2tuple

# ______________________________________________________________________

def _st2list (node, line_info = False):
    """return a list representation (ourself!)
    """
    ((symbolno, text, lineno), children) = node
    if symbolno >= token.NT_OFFSET:
        nextchildren = [symbolno]
        nextchildren += [_st2list(child, line_info) for child in children]
        return nextchildren
    elif text == "\n":
        # XXX This is kinda a hack; can it be fixed somehow?
        return line_info and (symbolno, '', lineno) or (symbolno, '')
    #elif symbolno == token.ENDMARKER and line_info:
    #    # XXX Another hack to align line number of the end token.
    #    return (symbolno, '', lineno - 1)
    else:
        return line_info and (symbolno, text, lineno) or (symbolno, text)

# ______________________________________________________________________

def st2list (node, line_info = 0):
    """st2list()
    Do what parser.st2list() normally does.
    """
    return node.tolist(line_info)

ast2list = st2list

# ______________________________________________________________________

def compileast (st, file_name):
    """compileast()
    Do what parser.compileast() normally does.
    """
    return st.compile(file_name)

# ______________________________________________________________________
def expr (space, source):
    """expr
    Tries to mock the expr() function in the Python parser module, but returns
    one of those silly tuple/list encoded trees.
    """
    st = _doParse(space, source, eval_input)
    return space.wrap(st) 
expr.unwrap_spec = [ObjSpace, str]

# ______________________________________________________________________

def suite (space, source):
    """suite
    Tries to mock the suite() function in the Python parser module, but returns
    one of those silly tuple/list encoded trees.
    """
    st = _doParse(space, source, file_input)
    return space.wrap(st) 
suite.unwrap_spec = [ObjSpace, str]

# ______________________________________________________________________

def _doParse (space, source, start):
    """_doParse()
    Ignore the function behind the curtain!  Even if it is kinda like the
    CPython PyParser_SimpleParseString() (I think.)
    """
    global pygrammar
    try: 
        tokenizer = PyTokenizer.PyTokenizer()
        tokenizer.tokenizeString(source)
        return STType(space, DFAParser.parsetok(tokenizer, pygrammar, start))
    except SyntaxError: 
        raise OperationError(space.w_SyntaxError) 
    except InternalParserError, e: 
        reraise(space, e) 

def reraise(space, e): 
    w_ParserError = space.sys.getmodule('parser').get('ParserError') 
    if e.args: 
        w_msg = space.wrap(e.args[0])
    else: 
        w_msg = space.wrap("unknown") 
    raise OperationError(w_ParserError, w_msg) 

# ______________________________________________________________________

def _check_for_accepting_states (igrammar):
    """_check_for_accepting_states()
    Ignore me, I am just a sanity checking function for tree validation.

    This illustrates the raw grammar generated by PyPgen doesn't ship
    accepting state data; this is left to addAccelerators().
    """
    for dfa in igrammar[0]:
        symbol_no, symbol_name, initial, states, first = dfa
        acceptingStates = []
        for state in states:
            arcs, accel, accept = state
            if accept:
                acceptingStates.append(state)
        if len(acceptingStates) == 0:
            print "!" * 70
        print symbol_name, acceptingStates
        if len(acceptingStates) == 0:
            print "!" * 70
        else:
            print

# ______________________________________________________________________
# End of pyparser.py
