#! /usr/bin/env python
# ______________________________________________________________________
"""Module genPytokenize

Generates finite state automata for recognizing Python tokens.  These are hand
coded versions of the regular expressions originally appearing in Ping's
tokenize module in the Python standard library.

When run from the command line, this should pretty print the DFA machinery.

$Id: genPytokenize.py,v 1.1 2003/10/02 17:37:17 jriehl Exp $
"""
# ______________________________________________________________________

from automata import *

# ______________________________________________________________________

def makePyPseudoDFA ():
    import string
    states = []
    # ____________________________________________________________
    def makeLineCont ():
        return chain(states,
                     newArcPair(states, "\\"),
                     maybe(states, newArcPair(states, "\r")),
                     newArcPair(states, "\n"))
    # ____________________________________________________________
    # Ignore stuff
    def makeWhitespace ():
        return any(states, groupStr(states, " \f\t"))
    # ____________________________________________________________
    def makeComment ():
        return chain(states,
                     newArcPair(states, "#"),
                     any(states, notGroupStr(states, "\r\n")))
    # ____________________________________________________________
    #ignore = chain(states,
    #               makeWhitespace(),
    #               any(states, chain(states,
    #                                 makeLineCont(),
    #                                 makeWhitespace())),
    #               maybe(states, makeComment()))
    # ____________________________________________________________
    # Names
    name = chain(states,
                 groupStr(states, string.letters + "_"),
                 any(states, groupStr(states,
                                      string.letters + string.digits + "_")))
    # ____________________________________________________________
    # Digits
    def makeDigits ():
        return groupStr(states, "0123456789")
    # ____________________________________________________________
    # Integer numbers
    hexNumber = chain(states,
                      newArcPair(states, "0"),
                      groupStr(states, "xX"),
                      any(states, groupStr(states, "0123456789abcdefABCDEF")),
                      maybe(states, groupStr(states, "lL")))
    octNumber = chain(states,
                      newArcPair(states, "0"),
                      any(states, groupStr(states, "01234567")),
                      maybe(states, groupStr(states, "lL")))
    decNumber = chain(states,
                      groupStr(states, "123456789"),
                      any(states, makeDigits()),
                      maybe(states, groupStr(states, "lL")))
    intNumber = group(states, hexNumber, octNumber, decNumber)
    # ____________________________________________________________
    # Exponents
    def makeExp ():
        return chain(states,
                     groupStr(states, "eE"),
                     maybe(states, groupStr(states, "+-")),
                     atleastonce(states, makeDigits()))
    # ____________________________________________________________
    # Floating point numbers
    def makeFloat ():
        pointFloat = chain(states,
                           group(states,
                                 chain(states,
                                       atleastonce(states, makeDigits()),
                                       newArcPair(states, "."),
                                       any(states, makeDigits())),
                                 chain(states,
                                       newArcPair(states, "."),
                                       atleastonce(states, makeDigits()))),
                           maybe(states, makeExp()))
        expFloat = chain(states,
                         atleastonce(states, makeDigits()),
                         makeExp())
        return group(states, pointFloat, expFloat)
    # ____________________________________________________________
    # Imaginary numbers
    imagNumber = group(states,
                       chain(states,
                             atleastonce(states, makeDigits()),
                             groupStr(states, "jJ")),
                       chain(states,
                             makeFloat(),
                             groupStr(states, "jJ")))
    # ____________________________________________________________
    # Any old number.
    number = group(states, imagNumber, makeFloat(), intNumber)
    # ____________________________________________________________
    # Funny
    operator = group(states,
                     chain(states,
                           chainStr(states, "**"),
                           maybe(states, newArcPair(states, "="))),
                     chain(states,
                           chainStr(states, ">>"),
                           maybe(states, newArcPair(states, "="))),
                     chain(states,
                           chainStr(states, "<<"),
                           maybe(states, newArcPair(states, "="))),
                     chainStr(states, "<>"),
                     chainStr(states, "!="),
                     chain(states,
                           chainStr(states, "//"),
                           maybe(states, newArcPair(states, "="))),
                     chain(states,
                           groupStr(states, "+-*/%&|^=<>"),
                           maybe(states, newArcPair(states, "="))),
                     newArcPair(states, "~"))
    bracket = groupStr(states, "[](){}")
    special = group(states,
                    chain(states,
                          maybe(states, newArcPair(states, "\r")),
                          newArcPair(states, "\n")),
                    groupStr(states, ":;.,`"))
    funny = group(states, operator, bracket, special)
    # ____________________________________________________________
    def makeStrPrefix ():
        return chain(states,
                     maybe(states, groupStr(states, "uU")),
                     maybe(states, groupStr(states, "rR")))
    # ____________________________________________________________
    contStr = group(states,
                    chain(states,
                          makeStrPrefix(),
                          newArcPair(states, "'"),
                          any(states,
                              notGroupStr(states, "\n'\\")),
                          any(states,
                              chain(states,
                                    newArcPair(states, "\\"),
                                    newArcPair(states, DEFAULT),
                                    any(states,
                                        notGroupStr(states, "\n'\\")))),
                          group(states,
                                newArcPair(states, "'"),
                                makeLineCont())),
                    chain(states,
                          makeStrPrefix(),
                          newArcPair(states, '"'),
                          any(states,
                              notGroupStr(states, '\n"\\')),
                          any(states,
                              chain(states,
                                    newArcPair(states, "\\"),
                                    newArcPair(states, DEFAULT),
                                    any(states,
                                        notGroupStr(states, '\n"\\')))),
                          group(states,
                                newArcPair(states, '"'),
                                makeLineCont())))
    triple = group(states,
                   makeStrPrefix(),
                   group(states,
                         chainStr(states, "'''"),
                         chainStr(states, '"""')))
    pseudoExtras = group(states,
                         makeLineCont(),
                         makeComment(),
                         triple)
    pseudoToken = chain(states,
                        makeWhitespace(),
                        group(states,
                              pseudoExtras, number, funny, contStr, name))
    dfaStates = nfaToDfa(states, *pseudoToken)
    return DFA(dfaStates)

# ______________________________________________________________________

def makePyEndDFAMap ():
    states = []
    single = chain(states,
                   any(states, notGroupStr(states, "'\\")),
                   any(states,
                       chain(states,
                             newArcPair(states, "\\"),
                             newArcPair(states, DEFAULT),
                             any(states, notGroupStr(states, "'\\")))),
                   newArcPair(states, "'"))
    singleDFA = DFA(nfaToDfa(states, *single))
    states = []
    double = chain(states,
                   any(states, notGroupStr(states, '"\\')),
                   any(states,
                       chain(states,
                             newArcPair(states, "\\"),
                             newArcPair(states, DEFAULT),
                             any(states, notGroupStr(states, '"\\')))),
                   newArcPair(states, '"'))
    doubleDFA = DFA(nfaToDfa(states, *double))
    states = []
    single3 = chain(states,
                    any(states, notGroupStr(states, "'\\")),
                    any(states,
                        chain(states,
                              group(states,
                                    chain(states,
                                          newArcPair(states, "\\"),
                                          newArcPair(states, DEFAULT)),
                                    chain(states,
                                          newArcPair(states, "'"),
                                          notChainStr(states, "''"))),
                              any(states, notGroupStr(states, "'\\")))),
                    chainStr(states, "'''"))
    single3DFA = NonGreedyDFA(nfaToDfa(states, *single3))
    states = []
    double3 = chain(states,
                    any(states, notGroupStr(states, '"\\')),
                    any(states,
                        chain(states,
                              group(states,
                                    chain(states,
                                          newArcPair(states, "\\"),
                                          newArcPair(states, DEFAULT)),
                                    chain(states,
                                          newArcPair(states, '"'),
                                          notChainStr(states, '""'))),
                              any(states, notGroupStr(states, '"\\')))),
                    chainStr(states, '"""'))
    double3DFA = NonGreedyDFA(nfaToDfa(states, *double3))
    map = {"'" : singleDFA,
           '"' : doubleDFA,
           "r" : None,
           "R" : None,
           "u" : None,
           "U" : None}
    for uniPrefix in ("", "u", "U"):
        for rawPrefix in ("", "r", "R"):
            prefix = uniPrefix + rawPrefix
            map[prefix + "'''"] = single3DFA
            map[prefix + '"""'] = double3DFA
    return map

# ______________________________________________________________________

def main ():
    import pprint
    pseudoDFA = makePyPseudoDFA()
    print "psuedoDFA =",
    pprint.pprint(pseudoDFA.states)
    endDFAMap = makePyEndDFAMap()
    print "singleEndDFA =",
    pprint.pprint(endDFAMap["'"].states)
    print "doubleEndDFA =",
    pprint.pprint(endDFAMap['"'].states)
    print "endDFAMap = {\"'\" : singleEndDFA,"
    print "             '\"' : doubleEndDFA,"
    print "             'r' : None,"
    print "             'R' : None,"
    print "             'u' : None,"
    print "             'U' : None}"

# ______________________________________________________________________

if __name__ == "__main__":
    main()

# ______________________________________________________________________
# End of genPytokenize.py
