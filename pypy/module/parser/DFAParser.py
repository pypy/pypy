#! /usr/bin/env python
# ______________________________________________________________________
"""DFAParser.py - Implements the Python parsing algorithm.

I am going to try to keep this simple, and see if I can't get a Python to C
translator to optimize the heck out of it after this is all done.

Grammar := ( [ DFA ], [ Label ], Start : Int , Accel : Int )
DFA := ( Type : Int, Name : String, Initial : Int, [ State ], First : String )
State := ( [ Arc ], Accel, Accept : Int )
Arc := ( Label : Int, StateIndex )
Accel := ( Upper : Int, Lower : Int, [ Int ] )
Label := ( Type : Int, Name : String )

______________________________________________________________________
Function isomorphism notes:

acceler.c:
PyGrammar_AddAccelerators       ~ addAccelerators

bitset.c:
testbit                         ~ testbit

grammar1.c:
PyGrammar_FindDFA               ~ findDFA

parser.c:
classify                        ~ classify
PyParser_AddToken               ~ addToken

parsetok.c:
parsetok                        ~ parsetok

______________________________________________________________________
Developer notes:

* I'm not sure I like all this tuple/functional BS.  Maybe I should use
lists so data can be modified in place?  Ultimately, this will change to
whatever best suits the Python to C translator.
______________________________________________________________________
$Id: DFAParser.py,v 1.1 2003/10/02 17:37:17 jriehl Exp $
"""
# ______________________________________________________________________

# XXX The token module dependency may need to be hacked if/when support for
# other tokenizers is added.

import token

# ______________________________________________________________________

E_OK = 0
E_DONE = 1
E_SYNTAX = 2

__DEBUG__ = 0

if __DEBUG__:
    import string

# ______________________________________________________________________

def testbit (bitstr, ibit):
    """testbit()
    Mirrors the operation of the C testbit() function in the bitset.c module
    of the Python distribution.

    Note that I have made the possibly incorrect assumption that
    sizeof(char) = 1 for the CPython platform.
    """
    return 0 != (ord(bitstr[ibit >> 3]) & (1 << (ibit & 0x7)))

# ______________________________________________________________________

def classify (grammar, type, name):
    """classify()
    Mirrors the operation of the C classify() in the parser.c module of the
    Python distribution.
    """
    labels = grammar[1]
    if type == token.NAME:
        i = 0
        for label in labels:
            if (type, name) == label:
                return i
            i += 1
    i = 0
    for label in labels:
        if (type == label[0]) and (None == label[1]):
            return i
        i += 1
    return -1

# ______________________________________________________________________

def findDFA (g, nt):
    """findDFA()
    Mirrors the operation of the PyGrammar_FindDFA() function in the Python
    distribution.
    """
    dfa = g[0][nt - token.NT_OFFSET]
    assert dfa[0] == nt
    return dfa

# ______________________________________________________________________

def addToken (grammar, stack, type, name, lineno):
    """addToken()
    Mirrors the operation of the C PyParser_AddToken() in the parser.c module
    of the Python distribution.
    """
    ilabel = classify(grammar, type, name)
    if __DEBUG__:
        if len(name) > 50:
            print "Token: (%d, %d, '%s...')" % (type, ilabel, name[:50])
        else:
            print "Token: (%d, %d, '%s')" % (type, ilabel, name)
    while 1:
        state, dfa, parent = stack[-1]
        if __DEBUG__:
            print "DFA '%s', State %d:" % (dfa[1], dfa[3].index(state)),
        # __________________________________________________
        # Perform accelerator
        arcs, (accelUpper, accelLower, accelTable), accept = state
        if (accelLower <= ilabel) and (ilabel < accelUpper):
            accelResult = accelTable[ilabel - accelLower]
            if -1 != accelResult:
                # ______________________________
                # Handle accelerator result
                if (accelResult & (1<<7)):
                    # "Push non-terminal"
                    nt = (accelResult >> 8) + token.NT_OFFSET
                    arrow = accelResult & ((1<<7)-1)
                    nextDFA = findDFA(grammar, nt)
                    # ____________________
                    # INLINE PUSH
                    newAstNode = ((nt, None, lineno), [])
                    parent[1].append(newAstNode)
                    stack[-1] = (dfa[3][arrow], dfa, parent)
                    stack.append((nextDFA[3][nextDFA[2]], nextDFA, newAstNode))
                    # ____________________
                    if __DEBUG__:
                        print "Push..."
                    continue
                # ______________________________
                # INLINE SHIFT
                parent[1].append(((type, name, lineno), []))
                nextState = dfa[3][accelResult]
                stack[-1] = (nextState, dfa, parent)
                state = nextState
                if __DEBUG__:
                    print "Shift."
                # ______________________________
                while state[2] and len(state[0]) == 1:
                    # ____________________
                    # INLINE POP
                    stack = stack[:-1]
                    if __DEBUG__:
                        print ("DFA '%s', State %d: Direct pop" %
                               (dfa[1], dfa[3].index(state)))
                    if 0 == len(stack):
                        if __DEBUG__:
                            print "Accept."
                        return (E_DONE, stack, None)
                    else:
                        state, dfa, parent = stack[-1]
                    # ____________________
                return (E_OK, stack, None)
        # __________________________________________________
        if accept:
            if __DEBUG__:
                print "Pop..."
            stack = stack[:-1]
            if 0 == len(stack):
                return (E_SYNTAX, stack, ", (XXX) empty stack!!!")
            continue
        # XXX Add (more/better) syntax error support.
        if __DEBUG__:
            print ("Syntax error: upper %d, lower %d, ilabel %d" %
                   (accelUpper, accelLower, ilabel))
        if ((accelUpper - 1 <= accelLower) and
            (None != grammar[1][accelLower][1])):
            errMsg = ", %s expected (not %s)" % (grammar[1][accelLower][1],
                                                 `name`)
        else:
            errMsg = ", unexpected %s" % `name`
        return (E_SYNTAX, stack, errMsg)

# ______________________________________________________________________

def addAccelerators (g):
    """addAccelerators()
    Adds accelerator data to a grammar tuple if the grammar does not already
    contain accelerator information.  Returns a new grammar tuple.
    """
    # ____________________________________________________________
    def handleState (state):
        """handleState()
        Warning: this is nested so it can get at the grammar passed to
        addAccelerators() - rather than accepting it as an argument.  I only
        do this b/c this function is map()'d.
        """
        arcs, accel, accept = state
        accept = 0
        labelCount = len(labels)
        accelArray = [-1] * labelCount
        for arc in arcs:
            labelIndex, arrow = arc
            type = labels[labelIndex][0]
            if (arrow >= (1 << 7)):
                print "XXX too many states!"
                continue
            if type > token.NT_OFFSET:
                targetFirstSet = findDFA(g, type)[4]
                if (type - token.NT_OFFSET >= (1 << 7)):
                    print "XXX too high nonterminal number!"
                    continue
                for ibit in range(0, labelCount):
                    if testbit(targetFirstSet, ibit):
                        if accelArray[ibit] != -1:
                            print "XXX ambiguity!"
                        accelArray[ibit] = (arrow | (1 << 7) |
                                            ((type - token.NT_OFFSET) << 8))
            elif 0 == labelIndex:
                accept = 1
            elif (labelIndex >= 0) and (labelIndex < labelCount):
                accelArray[labelIndex] = arrow
        # Now compute the upper and lower bounds.
        accelUpper = labelCount
        while (accelUpper > 0) and (-1 == accelArray[accelUpper - 1]):
            accelUpper -= 1
        accelLower = 0
        while (accelLower < accelUpper) and (-1 == accelArray[accelLower]):
            accelLower += 1
        accelArray = accelArray[accelLower:accelUpper]
        return (arcs, (accelUpper, accelLower, accelArray), accept)
    # ____________________________________________________________
    def handleDFA (dfa):
        type, name, initial, states, first = dfa
        return (type, name, initial, map(handleState, states), first)
    # ____________________________________________________________
    dfas, labels, start, accel = g
    if 0 == accel:
        g = (map(handleDFA, dfas), labels, start, 1)
    return g

# ______________________________________________________________________

def parsetok (tokenizer, grammar, start):
    """parsetok()
    Mirrors the operation of the C parsetok() in the parsetok.c module of the
    Python distribution.  However, one big difference is its use of a tokenizer
    function.  The function should return a type, a string and a line number.

    NOTE: I think I am not going to accept the lexical hack where final
    NEWLINE and DEDENTS are inserted in the lexical stream if needed - this
    should be implemented in the tokenizer.
    """
    # Initialize the parsing stack.
    grammar = addAccelerators(grammar)
    rootNode = ((start, None, 0), [])
    dfa = findDFA(grammar, start)
    parseStack = [(dfa[3][dfa[2]], dfa, rootNode)]
    # Parse all of it.
    result = E_OK
    while result == E_OK:
        type, tokStr, lineno = tokenizer()
        result, parseStack, errMsg = addToken(grammar, parseStack, type,
                                              tokStr, lineno)
    if result == E_DONE:
        return rootNode
    else:
        raise SyntaxError("Error in line %d%s" % (lineno, errMsg))

# ______________________________________________________________________
# MAIN ROUTINE - For unit testing.

def main (inputGrammar, inputFile = None):
    """main() - Silly little test routine"""
    # ____________________________________________________________
    # Build tokenizer
    import sys
    try:
        from basil.lang.python import StdTokenizer
    except ImportError:
        import StdTokenizer
    if inputFile == None:
        inputFile = "<stdin>"
        fileObj = sys.stdin
    else:
        fileObj = open(inputFile)
    tokenizer = StdTokenizer.StdTokenizer(inputFile, fileObj.readline)
    # ____________________________________________________________
    # Build parser
    import pprint
    from basil.parsing import pgen
    gramAst = pgen.metaParser.parseFile(inputGrammar)
    myParser = pgen.buildParser(gramAst)
    grammar = myParser.toTuple()
    if __DEBUG__:
        pprint.pprint(grammar)
    symbols = myParser.stringToSymbolMap()
    # ____________________________________________________________
    # Run parser
    import time
    t0 = time.time()
    parseTree = parsetok(tokenizer, grammar, symbols['file_input'])
    t1 = time.time()
    print "DFAParser took %g seconds" % (t1 - t0)
    fileObj.close()
    # ____________________________________________________________
    # Display AST
    from basil.visuals.TreeBox import showTree
    showTree(parseTree).mainloop()

# ______________________________________________________________________

if __name__ == "__main__":
    import sys
    # XXX - Maybe this file location should not be hard coded??
    inputGrammar = "../../parsing/tests/test.pgen"
    if len(sys.argv) == 1:
        main(inputGrammar)
    else:
        main(inputGrammar, sys.argv[1])

# ______________________________________________________________________
# End of DFAParser.py
