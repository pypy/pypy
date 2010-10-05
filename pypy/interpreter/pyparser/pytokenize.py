# ______________________________________________________________________
"""Module pytokenize

THIS FILE WAS COPIED FROM pypy/module/parser/pytokenize.py AND ADAPTED
TO BE ANNOTABLE (Mainly made lists homogeneous)

This is a modified version of Ka-Ping Yee's tokenize module found in the
Python standard library.

The primary modification is the removal of the tokenizer's dependence on the
standard Python regular expression module, which is written in C.  The regular
expressions have been replaced with hand built DFA's using the
basil.util.automata module.

$Id: pytokenize.py,v 1.3 2003/10/03 16:31:53 jriehl Exp $
"""
# ______________________________________________________________________

from pypy.interpreter.pyparser import automata

__all__ = [ "tokenize" ]

# ______________________________________________________________________
# Automatically generated DFA's

accepts = [True, True, True, True, True, True, True, True,
           True, True, False, True, True, True, False, False,
           False, False, True, False, False, True, True,
           True, False, True, False, True, False, True,
           False, True, False, False, False, True, False,
           False, False, True]
states = [
    {'\t': 0, '\n': 13, '\x0c': 0,
     '\r': 14, ' ': 0, '!': 10, '"': 16,
     '#': 18, '%': 12, '&': 12, "'": 15,
     '(': 13, ')': 13, '*': 7, '+': 12,
     ',': 13, '-': 12, '.': 6, '/': 11,
     '0': 4, '1': 5, '2': 5, '3': 5,
     '4': 5, '5': 5, '6': 5, '7': 5,
     '8': 5, '9': 5, ':': 13, ';': 13,
     '<': 9, '=': 12, '>': 8, '@': 13,
     'A': 1, 'B': 2, 'C': 1, 'D': 1,
     'E': 1, 'F': 1, 'G': 1, 'H': 1,
     'I': 1, 'J': 1, 'K': 1, 'L': 1,
     'M': 1, 'N': 1, 'O': 1, 'P': 1,
     'Q': 1, 'R': 3, 'S': 1, 'T': 1,
     'U': 2, 'V': 1, 'W': 1, 'X': 1,
     'Y': 1, 'Z': 1, '[': 13, '\\': 17,
     ']': 13, '^': 12, '_': 1, '`': 13,
     'a': 1, 'b': 2, 'c': 1, 'd': 1,
     'e': 1, 'f': 1, 'g': 1, 'h': 1,
     'i': 1, 'j': 1, 'k': 1, 'l': 1,
     'm': 1, 'n': 1, 'o': 1, 'p': 1,
     'q': 1, 'r': 3, 's': 1, 't': 1,
     'u': 2, 'v': 1, 'w': 1, 'x': 1,
     'y': 1, 'z': 1, '{': 13, '|': 12,
     '}': 13, '~': 13},

    {'0': 1, '1': 1, '2': 1, '3': 1,
     '4': 1, '5': 1, '6': 1, '7': 1,
     '8': 1, '9': 1, 'A': 1, 'B': 1,
     'C': 1, 'D': 1, 'E': 1, 'F': 1,
     'G': 1, 'H': 1, 'I': 1, 'J': 1,
     'K': 1, 'L': 1, 'M': 1, 'N': 1,
     'O': 1, 'P': 1, 'Q': 1, 'R': 1,
     'S': 1, 'T': 1, 'U': 1, 'V': 1,
     'W': 1, 'X': 1, 'Y': 1, 'Z': 1,
     '_': 1, 'a': 1, 'b': 1, 'c': 1,
     'd': 1, 'e': 1, 'f': 1, 'g': 1,
     'h': 1, 'i': 1, 'j': 1, 'k': 1,
     'l': 1, 'm': 1, 'n': 1, 'o': 1,
     'p': 1, 'q': 1, 'r': 1, 's': 1,
     't': 1, 'u': 1, 'v': 1, 'w': 1,
     'x': 1, 'y': 1, 'z': 1},

    {'"': 20, "'": 19, '0': 1, '1': 1,
     '2': 1, '3': 1, '4': 1, '5': 1,
     '6': 1, '7': 1, '8': 1, '9': 1,
     'A': 1, 'B': 1, 'C': 1, 'D': 1,
     'E': 1, 'F': 1, 'G': 1, 'H': 1,
     'I': 1, 'J': 1, 'K': 1, 'L': 1,
     'M': 1, 'N': 1, 'O': 1, 'P': 1,
     'Q': 1, 'R': 3, 'S': 1, 'T': 1,
     'U': 1, 'V': 1, 'W': 1, 'X': 1,
     'Y': 1, 'Z': 1, '_': 1, 'a': 1,
     'b': 1, 'c': 1, 'd': 1, 'e': 1,
     'f': 1, 'g': 1, 'h': 1, 'i': 1,
     'j': 1, 'k': 1, 'l': 1, 'm': 1,
     'n': 1, 'o': 1, 'p': 1, 'q': 1,
     'r': 3, 's': 1, 't': 1, 'u': 1,
     'v': 1, 'w': 1, 'x': 1, 'y': 1,
     'z': 1},

    {'"': 20, "'": 19, '0': 1, '1': 1,
     '2': 1, '3': 1, '4': 1, '5': 1,
     '6': 1, '7': 1, '8': 1, '9': 1,
     'A': 1, 'B': 1, 'C': 1, 'D': 1,
     'E': 1, 'F': 1, 'G': 1, 'H': 1,
     'I': 1, 'J': 1, 'K': 1, 'L': 1,
     'M': 1, 'N': 1, 'O': 1, 'P': 1,
     'Q': 1, 'R': 1, 'S': 1, 'T': 1,
     'U': 1, 'V': 1, 'W': 1, 'X': 1,
     'Y': 1, 'Z': 1, '_': 1, 'a': 1,
     'b': 1, 'c': 1, 'd': 1, 'e': 1,
     'f': 1, 'g': 1, 'h': 1, 'i': 1,
     'j': 1, 'k': 1, 'l': 1, 'm': 1,
     'n': 1, 'o': 1, 'p': 1, 'q': 1,
     'r': 1, 's': 1, 't': 1, 'u': 1,
     'v': 1, 'w': 1, 'x': 1, 'y': 1,
     'z': 1},

    {'.': 25, '0': 23, '1': 23, '2': 23,
     '3': 23, '4': 23, '5': 23, '6': 23,
     '7': 23, '8': 24, '9': 24, 'E': 26,
     'J': 13, 'L': 13, 'O': 22, 'X': 21,
     'e': 26, 'j': 13, 'l': 13, 'o': 22,
     'x': 21},

    {'.': 25, '0': 5, '1': 5, '2': 5,
     '3': 5, '4': 5, '5': 5, '6': 5,
     '7': 5, '8': 5, '9': 5, 'E': 26,
     'J': 13, 'L': 13, 'e': 26, 'j': 13,
     'l': 13},

    {'0': 27, '1': 27, '2': 27, '3': 27,
     '4': 27, '5': 27, '6': 27, '7': 27,
     '8': 27, '9': 27},

    {'*': 12, '=': 13},

    {'=': 13, '>': 12},

    {'<': 12, '=': 13, '>': 13},

    {'=': 13},

    {'/': 12, '=': 13},

    {'=': 13},

    {},

    {'\n': 13},

    {automata.DEFAULT: 19, '\n': 28,
     "'": 29, '\\': 30},

    {automata.DEFAULT: 20, '\n': 28,
     '"': 31, '\\': 32},

    {'\n': 13, '\r': 14},

    {automata.DEFAULT: 18, '\n': 28,
     '\r': 28},

    {automata.DEFAULT: 19, '\n': 28,
     "'": 13, '\\': 30},

    {automata.DEFAULT: 20, '\n': 28,
     '"': 13, '\\': 32},

    {'0': 21, '1': 21, '2': 21, '3': 21,
     '4': 21, '5': 21, '6': 21, '7': 21,
     '8': 21, '9': 21, 'A': 21, 'B': 21,
     'C': 21, 'D': 21, 'E': 21, 'F': 21,
     'L': 13, 'a': 21, 'b': 21, 'c': 21,
     'd': 21, 'e': 21, 'f': 21,
     'l': 13},

    {'0': 22, '1': 22, '2': 22, '3': 22,
     '4': 22, '5': 22, '6': 22, '7': 22,
     'L': 13, 'l': 13},

    {'.': 25, '0': 23, '1': 23, '2': 23,
     '3': 23, '4': 23, '5': 23, '6': 23,
     '7': 23, '8': 24, '9': 24, 'E': 26,
     'J': 13, 'L': 13, 'e': 26, 'j': 13,
     'l': 13},

    {'.': 25, '0': 24, '1': 24, '2': 24,
     '3': 24, '4': 24, '5': 24, '6': 24,
     '7': 24, '8': 24, '9': 24, 'E': 26,
     'J': 13, 'e': 26, 'j': 13},

    {'0': 25, '1': 25, '2': 25, '3': 25,
     '4': 25, '5': 25, '6': 25, '7': 25,
     '8': 25, '9': 25, 'E': 33, 'J': 13,
     'e': 33, 'j': 13},

    {'+': 34, '-': 34, '0': 35, '1': 35,
     '2': 35, '3': 35, '4': 35, '5': 35,
     '6': 35, '7': 35, '8': 35,
     '9': 35},

    {'0': 27, '1': 27, '2': 27, '3': 27,
     '4': 27, '5': 27, '6': 27, '7': 27,
     '8': 27, '9': 27, 'E': 33, 'J': 13,
     'e': 33, 'j': 13},

    {},

    {"'": 13},

    {automata.DEFAULT: 36, '\n': 13,
     '\r': 14},

    {'"': 13},

    {automata.DEFAULT: 37, '\n': 13,
     '\r': 14},

    {'+': 38, '-': 38, '0': 39, '1': 39,
     '2': 39, '3': 39, '4': 39, '5': 39,
     '6': 39, '7': 39, '8': 39,
     '9': 39},

    {'0': 35, '1': 35, '2': 35, '3': 35,
     '4': 35, '5': 35, '6': 35, '7': 35,
     '8': 35, '9': 35},

    {'0': 35, '1': 35, '2': 35, '3': 35,
     '4': 35, '5': 35, '6': 35, '7': 35,
     '8': 35, '9': 35, 'J': 13,
     'j': 13},

    {automata.DEFAULT: 36, '\n': 28,
     "'": 13, '\\': 30},

    {automata.DEFAULT: 37, '\n': 28,
     '"': 13, '\\': 32},

    {'0': 39, '1': 39, '2': 39, '3': 39,
     '4': 39, '5': 39, '6': 39, '7': 39,
     '8': 39, '9': 39},

    {'0': 39, '1': 39, '2': 39, '3': 39,
     '4': 39, '5': 39, '6': 39, '7': 39,
     '8': 39, '9': 39, 'J': 13,
     'j': 13},

    ]
pseudoDFA = automata.DFA(states, accepts)

accepts = [False, False, False, False, False, True]
states = [
    {automata.DEFAULT: 0, '"': 1,
     '\\': 2},

    {automata.DEFAULT: 4, '"': 3,
     '\\': 2},

    {automata.DEFAULT: 4},

    {automata.DEFAULT: 4, '"': 5,
     '\\': 2},

    {automata.DEFAULT: 4, '"': 1,
     '\\': 2},

    {automata.DEFAULT: 4, '"': 5,
     '\\': 2},

    ]
double3DFA = automata.NonGreedyDFA(states, accepts)

accepts = [False, False, False, False, False, True]
states = [
    {automata.DEFAULT: 0, "'": 1,
     '\\': 2},

    {automata.DEFAULT: 4, "'": 3,
     '\\': 2},

    {automata.DEFAULT: 4},

    {automata.DEFAULT: 4, "'": 5,
     '\\': 2},

    {automata.DEFAULT: 4, "'": 1,
     '\\': 2},

    {automata.DEFAULT: 4, "'": 5,
     '\\': 2},

    ]
single3DFA = automata.NonGreedyDFA(states, accepts)

accepts = [False, True, False, False]
states = [
    {automata.DEFAULT: 0, '"': 1,
     '\\': 2},

    {},

    {automata.DEFAULT: 3},

    {automata.DEFAULT: 3, '"': 1,
     '\\': 2},

    ]
doubleDFA = automata.DFA(states, accepts)

accepts = [False, True, False, False]
states = [
    {automata.DEFAULT: 0, "'": 1,
     '\\': 2},

    {},

    {automata.DEFAULT: 3},

    {automata.DEFAULT: 3, "'": 1,
     '\\': 2},

    ]
singleDFA = automata.DFA(states, accepts)

endDFAs = {"'" : singleDFA,
           '"' : doubleDFA,
           'r' : None,
           'R' : None,
           'u' : None,
           'U' : None,
           'b' : None,
           'B' : None}

#_______________________________________________________________________
# End of automatically generated DFA's

for uniPrefix in ("", "u", "U", "b", "B"):
    for rawPrefix in ("", "r", "R"):
        prefix = uniPrefix + rawPrefix
        endDFAs[prefix + "'''"] = single3DFA
        endDFAs[prefix + '"""'] = double3DFA

whiteSpaceStatesAccepts = [True]
whiteSpaceStates = [{'\t': 0, ' ': 0, '\x0c': 0}]
whiteSpaceDFA = automata.DFA(whiteSpaceStates, whiteSpaceStatesAccepts)

# ______________________________________________________________________
# COPIED:

triple_quoted = {}
for t in ("'''", '"""',
          "r'''", 'r"""', "R'''", 'R"""',
          "u'''", 'u"""', "U'''", 'U"""',
          "b'''", 'b"""', "B'''", 'B"""',
          "ur'''", 'ur"""', "Ur'''", 'Ur"""',
          "uR'''", 'uR"""', "UR'''", 'UR"""',
          "br'''", 'br"""', "Br'''", 'Br"""',
          "bR'''", 'bR"""', "BR'''", 'BR"""'):
    triple_quoted[t] = t
single_quoted = {}
for t in ("'", '"',
          "r'", 'r"', "R'", 'R"',
          "u'", 'u"', "U'", 'U"',
          "b'", 'b"', "B'", 'B"',
          "ur'", 'ur"', "Ur'", 'Ur"',
          "uR'", 'uR"', "UR'", 'UR"',
          "br'", 'br"', "Br'", 'Br"',
          "bR'", 'bR"', "BR'", 'BR"'):
    single_quoted[t] = t

tabsize = 8

# PYPY MODIFICATION: removed TokenError class as it's not needed here

# PYPY MODIFICATION: removed StopTokenizing class as it's not needed here

# PYPY MODIFICATION: removed printtoken() as it's not needed here

# PYPY MODIFICATION: removed tokenize() as it's not needed here

# PYPY MODIFICATION: removed tokenize_loop() as it's not needed here

# PYPY MODIFICATION: removed generate_tokens() as it was copied / modified
#                    in pythonlexer.py

# PYPY MODIFICATION: removed main() as it's not needed here

# ______________________________________________________________________
# End of pytokenize.py

