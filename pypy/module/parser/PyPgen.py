#! /usr/bin/env python
# ______________________________________________________________________
"""Module PyPgen

Python implementation of the Python distribution parser generator, pgen.

XXX This now assumes that everything in the common/python directory of the
Basil project is in the Python module path.

$Id: PyPgen.py,v 1.2 2003/10/02 17:37:17 jriehl Exp $
"""
# ______________________________________________________________________
# Module imports

import PgenParser
import TokenUtils
import StdTokenizer
import token, string

EMPTY = token.ENDMARKER

__DEBUG__ = 0
__BASIL__ = 0

if __DEBUG__:
    import pprint

# ______________________________________________________________________

class PyPgen:
    """Class PyPgen
    """
    # ____________________________________________________________
    def __init__ (self):
        """PyPgen.__init__
        """
        self.nfaGrammar = self.dfaGrammar = None
        self.nfa = None
        self.crntType = token.NT_OFFSET

    # ____________________________________________________________
    def addLabel (self, labelList, tokType, tokName):
        """PyPgen.addLabel
        """
        # XXX
        #labelIndex = 0
        #for labelType, labelName in labelList:
        #    if (labelType == tokType) and (labelName == tokName):
        #        return labelIndex
        #    labelIndex += 1
        labelTup = (tokType, tokName)
        if labelTup in labelList:
            return labelList.index(labelTup)
        labelIndex = len(labelList)
        labelList.append(labelTup)
        return labelIndex

    # ____________________________________________________________
    def handleStart (self, ast):
        """PyPgen.handleStart()
        """
        self.nfaGrammar = [[],[(token.ENDMARKER, "EMPTY")]]
        self.crntType = token.NT_OFFSET
        type, children = ast
        assert type == PgenParser.MSTART
        for child in children:
            if child[0] == PgenParser.RULE:
                self.handleRule(child)
        return self.nfaGrammar

    # ____________________________________________________________
    def handleRule (self, ast):
        """PyPgen.handleRule()

        NFA := [ type : Int, name : String, [ STATE ], start : Int,
                 finish : Int ]
        STATE := [ ARC ]
        ARC := ( labelIndex : Int, stateIndex : Int )
        """
        # Build the NFA shell.
        self.nfa = [self.crntType, None, [], -1, -1]
        self.crntType += 1
        # Work on the AST node
        type, children = ast
        assert type == PgenParser.RULE
        name, colon, rhs, newline = children
        assert name[0][0] == token.NAME, "Malformed pgen parse tree"
        self.nfa[1] = name[0][1]
        if (token.NAME, name[0][1]) not in self.nfaGrammar[1]:
            self.nfaGrammar[1].append((token.NAME, name[0][1]))
        assert colon[0][0] == token.COLON, "Malformed pgen parse tree"
        start, finish = self.handleRhs(rhs)
        self.nfa[3] = start
        self.nfa[4] = finish
        assert newline[0][0] == token.NEWLINE, "Malformed pgen parse tree"
        # Append the NFA to the grammar.
        self.nfaGrammar[0].append(self.nfa)

    # ____________________________________________________________
    def handleRhs (self, ast):
        """PyPgen.handleRhs()
        """
        type, children = ast
        assert type == PgenParser.RHS
        start, finish = self.handleAlt(children[0])
        if len(children) > 1:
            cStart = start
            cFinish = finish
            start = len(self.nfa[2])
            self.nfa[2].append([(EMPTY, cStart)])
            finish = len(self.nfa[2])
            self.nfa[2].append([])
            self.nfa[2][cFinish].append((EMPTY, finish))
            for child in children[2:]:
                if child[0] == PgenParser.ALT:
                    cStart, cFinish = self.handleAlt(child)
                    self.nfa[2][start].append((EMPTY, cStart))
                    self.nfa[2][cFinish].append((EMPTY, finish))
        return start, finish

    # ____________________________________________________________
    def handleAlt (self, ast):
        """PyPgen.handleAlt()
        """
        type, children = ast
        assert type == PgenParser.ALT
        start, finish = self.handleItem(children[0])
        if len(children) > 1:
            for child in children[1:]:
                cStart, cFinish = self.handleItem(child)
                self.nfa[2][finish].append((EMPTY, cStart))
                finish = cFinish
        return start, finish

    # ____________________________________________________________
    def handleItem (self, ast):
        """PyPgen.handleItem()
        """
        nodeType, children = ast
        assert nodeType == PgenParser.ITEM
        if children[0][0] == PgenParser.ATOM:
            start, finish = self.handleAtom(children[0])
            if len(children) > 1:
                # Short out the child NFA
                self.nfa[2][finish].append((EMPTY, start))
                if children[1][0][0] == token.STAR:
                    finish = start
                else:
                    assert children[1][0][0] == token.PLUS
        else:
            assert children[0][0][0] == token.LSQB
            start = len(self.nfa[2])
            finish = start + 1
            self.nfa[2].append([(EMPTY, finish)])
            self.nfa[2].append([])
            cStart, cFinish = self.handleRhs(children[1])
            self.nfa[2][start].append((EMPTY, cStart))
            self.nfa[2][cFinish].append((EMPTY, finish))
            assert (len(children) == 3) and (children[2][0][0] == token.RSQB)
        return start, finish

    # ____________________________________________________________
    def handleAtom (self, ast):
        """PyPgen.handleAtom()
        """
        nodeType, children = ast
        assert nodeType == PgenParser.ATOM
        assert type(children[0][0]) == type(())
        tokType, tokName, lineno = children[0][0]
        if tokType == token.LPAR:
            start, finish = self.handleRhs(children[1])
            assert (len(children) == 3) and (children[2][0][0] == token.RPAR)
        elif tokType in (token.STRING, token.NAME):
            start = len(self.nfa[2])
            finish = start + 1
            labelIndex = self.addLabel(self.nfaGrammar[1], tokType, tokName)
            self.nfa[2].append([(labelIndex, finish)])
            self.nfa[2].append([])
        else:
            assert 1 == 0, "Malformed pgen parse tree."
        return start, finish

    # ____________________________________________________________
    def generateDfaGrammar (self, nfaGrammar):
        """PyPgen.makeDfaGrammar()
        See notes in basil.lang.python.DFAParser for output schema.
        """
        dfas = []
        for nfa in nfaGrammar[0]:
            dfas.append(self.nfaToDfa(nfa))
        return [dfas, self.nfaGrammar[1], dfas[0][0], 0]

    # ____________________________________________________________
    def addClosure (self, stateList, nfa, istate):
        stateList[istate] = True
        arcs = nfa[2][istate]
        for label, arrow in arcs:
            if label == EMPTY:
                self.addClosure(stateList, nfa, arrow)

    # ____________________________________________________________
    def nfaToDfa (self, nfa):
        """PyPgen.nfaToDfa()
        """
        tempStates = []
        # tempState := [ stateList : List of Boolean,
        #                arcList : List of tempArc ]
        crntTempState = [[False] * len(nfa[2]), [], False]
        self.addClosure(crntTempState[0], nfa, nfa[3])
        crntTempState[2] = crntTempState[0][nfa[4]]
        if crntTempState[2]:
            print ("PyPgen: Warning, nonterminal '%s' may produce empty." %
                   (nfa[1]))
        tempStates.append(crntTempState)
        index = 0
        while index < len(tempStates):
            crntTempState = tempStates[index]
            for componentState in range(0, len(nfa[2])):
                if not crntTempState[0][componentState]:
                    continue
                nfaArcs = nfa[2][componentState]
                for label, nfaArrow in nfaArcs:
                    if label == EMPTY:
                        continue
                    foundTempArc = False
                    for tempArc in crntTempState[1]:
                        if tempArc[0] == label:
                            foundTempArc = True
                            break
                    if not foundTempArc:
                        tempArc = [label, -1, [False] * len(nfa[2])]
                        crntTempState[1].append(tempArc)
                    self.addClosure(tempArc[2], nfa, nfaArrow)
            for arcIndex in range(0, len(crntTempState[1])):
                label, arrow, targetStateList = crntTempState[1][arcIndex]
                targetFound = False
                arrow = 0
                for destTempState in tempStates:
                    if targetStateList == destTempState[0]:
                        targetFound = True
                        break
                    arrow += 1
                if not targetFound:
                    assert arrow == len(tempStates)
                    tempState = [targetStateList[:], [],
                                 targetStateList[nfa[4]]]
                    tempStates.append(tempState)
                # Write arrow value back to the arc
                crntTempState[1][arcIndex][1] = arrow
            index += 1
        tempStates = self.simplifyTempDfa(nfa, tempStates)
        return self.tempDfaToDfa(nfa, tempStates)

    # ____________________________________________________________
    def sameState (self, s1, s2):
        """PyPgen.sameState()
        """
        if (len(s1[1]) != len(s2[1])) or (s1[2] != s2[2]):
            return False
        for arcIndex in range(0, len(s1[1])):
            arc1 = s1[1][arcIndex]
            arc2 = s2[1][arcIndex]
            if arc1[:-1] != arc2[:-1]:
                return False
        return True

    # ____________________________________________________________
    def simplifyTempDfa (self, nfa, tempStates):
        """PyPgen.simplifyDfa()
        """
        if __DEBUG__:
            print "_" * 70
            pprint.pprint(nfa)
            pprint.pprint(tempStates)
        changes = True
        deletedStates = []
        while changes:
            changes = False
            for i in range(1, len(tempStates)):
                if i in deletedStates:
                    continue
                for j in range(0, i):
                    if j in deletedStates:
                        continue
                    if self.sameState(tempStates[i], tempStates[j]):
                        deletedStates.append(i)
                        for k in range(0, len(tempStates)):
                            if k in deletedStates:
                                continue
                            for arc in tempStates[k][1]:
                                if arc[1] == i:
                                    arc[1] = j
                        changes = True
                        break
        for stateIndex in deletedStates:
            tempStates[stateIndex] = None
        if __DEBUG__:
            pprint.pprint(tempStates)
        return tempStates

    # ____________________________________________________________
    def tempDfaToDfa (self, nfa, tempStates):
        """PyPgen.tempDfaToDfa()
        """
        dfaStates = []
        dfa = [nfa[0], nfa[1], 0, dfaStates, None]
        stateMap = {}
        tempIndex = 0
        for tempState in tempStates:
            if None != tempState:
                stateMap[tempIndex] = len(dfaStates)
                dfaStates.append(([], (0,0,()), 0))
            tempIndex += 1
        for tempIndex in stateMap.keys():
            stateList, tempArcs, accepting = tempStates[tempIndex]
            dfaStateIndex = stateMap[tempIndex]
            dfaState = dfaStates[dfaStateIndex]
            for tempArc in tempArcs:
                dfaState[0].append((tempArc[0], stateMap[tempArc[1]]))
            if accepting:
                dfaState[0].append((EMPTY, dfaStateIndex))
        return dfa

    # ____________________________________________________________
    def translateLabels (self, grammar):
        """PyPgen.translateLabels()
        """
        tokenNames = token.tok_name.values()
        labelList = grammar[1]
        for labelIndex in range(0, len(labelList)):
            type, name = labelList[labelIndex]
            if type == token.NAME:
                isNonTerminal = False
                for dfa in grammar[0]:
                    if dfa[1] == name:
                        labelList[labelIndex] = (dfa[0], None)
                        isNonTerminal = True
                        break
                if not isNonTerminal:
                    if name in tokenNames:
                        labelList[labelIndex] = (getattr(token, name), None)
                    else:
                        print "Can't translate NAME label '%s'" % name
            elif type == token.STRING:
                assert name[0] == name[-1]
                sname = name[1:-1]
                if (sname[0] in string.letters) or (sname[0] == "_"):
                    labelList[labelIndex] = (token.NAME, sname)
                elif TokenUtils.operatorMap.has_key(sname):
                    labelList[labelIndex] = (TokenUtils.operatorMap[sname],
                                             None)
                else:
                    print "Can't translate STRING label %s" % name
        return grammar

    # ____________________________________________________________
    def calcFirstSet (self, grammar, dfa):
        """PyPgen.calcFirstSet()
        """
        if dfa[4] == -1L:
            print "Left-recursion for '%s'" % dfa[1]
            return
        if dfa[4] != None:
            print "Re-calculating FIRST set for '%s' ???" % dfa[1]
        dfa[4] = -1L
        symbols = []
        result = 0L # XXX Can I get this arb. size stuff to translate to C?
        state = dfa[3][dfa[2]]
        for arc in state[0]: 
            sym = arc[0]
            if sym not in symbols:
                symbols.append(sym)
                type = grammar[1][sym][0]
                if (type >= token.NT_OFFSET):
                    # Nonterminal
                    ddfa = grammar[0][type - token.NT_OFFSET]
                    if ddfa[4] == -1L:
                        print "Left recursion below '%s'" % dfa[1]
                    else:
                        if ddfa[4] == None:
                            self.calcFirstSet(grammar, ddfa)
                        result |= ddfa[4]
                else:
                    result |= (1L << sym)
        dfa[4] = result

    # ____________________________________________________________
    def generateFirstSets (self, grammar):
        """PyPgen.generateFirstSets()
        """
        dfas = grammar[0]
        index = 0
        while index < len(dfas):
            dfa = dfas[index]
            if None == dfa[4]:
                self.calcFirstSet(grammar, dfa)
            index += 1
        for dfa in dfas:
            set = dfa[4]
            resultStr = ''
            while set > 0L:
                crntBits = set & 0xff
                resultStr += chr(crntBits)
                set >>= 8
            properSize = ((len(grammar[1]) / 8) + 1)
            if len(resultStr) < properSize:
                resultStr += ('\x00' * (properSize - len(resultStr)))
            dfa[4] = resultStr
        return grammar

    # ______________________________________________________________________
    def __call__ (self, ast):
        """PyPgen.__call__()
        """
        nfaGrammar = self.handleStart(ast)
        grammar = self.generateDfaGrammar(nfaGrammar)
        self.translateLabels(grammar)
        self.generateFirstSets(grammar)
        grammar[0] = map(tuple, grammar[0])
        return tuple(grammar)

# ______________________________________________________________________

def main ():
    import sys, PgenParser, pprint, DFAParser
    # ____________________________________________________________
    # Generate a test parser
    grammarST = PgenParser.parseFile("Grammar")
    pgenObj = PyPgen()
    grammarObj = pgenObj(grammarST)
    if "-py" in sys.argv:
        print "# %s" % ("_" * 70)
        print "# This was automatically generated by PyPgen."
        print "# Hack at your own risk."
        print
        print "grammarObj =",
    pprint.pprint(grammarObj)
    if "-i" in sys.argv:
        # __________________________________________________
        # Parse some input
        if len(sys.argv) > 1:
            inputFile = sys.argv[1]
            fileObj = open(inputFile)
        else:
            inputFile = "<stdin>"
            fileObj = sys.stdin
        tokenizer = StdTokenizer.StdTokenizer(inputFile, fileObj.readline)
        parseTree = DFAParser.parsetok(tokenizer, grammarObj, 257)
        fileObj.close()
        # __________________________________________________
        # Show the result
        if __BASIL__:
            from basil.visuals.TreeBox import showTree
            showTree(parseTree).mainloop()
        else:
            pprint.pprint(parseTree)

# ______________________________________________________________________

if __name__ == "__main__":
    main()

# ______________________________________________________________________
# End of PyPgen.py
