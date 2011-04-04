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
           True, True, False, True, True, True, True, False,
           False, False, True, False, False, True, False,
           False, True, False, True, False, True, False,
           False, True, False, False, True, True, True,
           False, False, True, False, False, False, True]
states = [
    # 0
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
    # 1
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
    # 2
    {'"': 16, "'": 15, '0': 1, '1': 1,
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
    # 3
    {'"': 16, "'": 15, '0': 1, '1': 1,
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
    # 4
    {'.': 24, '0': 21, '1': 21, '2': 21,
     '3': 21, '4': 21, '5': 21, '6': 21,
     '7': 21, '8': 23, '9': 23, 'B': 22,
     'E': 25, 'J': 13, 'L': 13, 'O': 20,
     'X': 19, 'b': 22, 'e': 25, 'j': 13,
     'l': 13, 'o': 20, 'x': 19},
    # 5
    {'.': 24, '0': 5, '1': 5, '2': 5,
     '3': 5, '4': 5, '5': 5, '6': 5,
     '7': 5, '8': 5, '9': 5, 'E': 25,
     'J': 13, 'L': 13, 'e': 25, 'j': 13,
     'l': 13},
    # 6
    {'0': 26, '1': 26, '2': 26, '3': 26,
     '4': 26, '5': 26, '6': 26, '7': 26,
     '8': 26, '9': 26},
    # 7
    {'*': 12, '=': 13},
    # 8
    {'=': 13, '>': 12},
    # 9
    {'<': 12, '=': 13, '>': 13},
    # 10
    {'=': 13},
    # 11
    {'/': 12, '=': 13},
    # 12
    {'=': 13},
    # 13
    {},
    # 14
    {'\n': 13},
    # 15
    {automata.DEFAULT: 30, '\n': 27,
     '\r': 27, "'": 28, '\\': 29},
    # 16
    {automata.DEFAULT: 33, '\n': 27,
     '\r': 27, '"': 31, '\\': 32},
    # 17
    {'\n': 13, '\r': 14},
    # 18
    {automata.DEFAULT: 18, '\n': 27, '\r': 27},
    # 19
    {'0': 34, '1': 34, '2': 34, '3': 34,
     '4': 34, '5': 34, '6': 34, '7': 34,
     '8': 34, '9': 34, 'A': 34, 'B': 34,
     'C': 34, 'D': 34, 'E': 34, 'F': 34,
     'a': 34, 'b': 34, 'c': 34, 'd': 34,
     'e': 34, 'f': 34},
    # 20
    {'0': 35, '1': 35, '2': 35, '3': 35,
     '4': 35, '5': 35, '6': 35, '7': 35},
    # 21
    {'.': 24, '0': 21, '1': 21, '2': 21,
     '3': 21, '4': 21, '5': 21, '6': 21,
     '7': 21, '8': 23, '9': 23, 'E': 25,
     'J': 13, 'L': 13, 'e': 25, 'j': 13,
     'l': 13},
    # 22
    {'0': 36, '1': 36},
    # 23
    {'.': 24, '0': 23, '1': 23, '2': 23,
     '3': 23, '4': 23, '5': 23, '6': 23,
     '7': 23, '8': 23, '9': 23, 'E': 25,
     'J': 13, 'e': 25, 'j': 13},
    # 24
    {'0': 24, '1': 24, '2': 24, '3': 24,
     '4': 24, '5': 24, '6': 24, '7': 24,
     '8': 24, '9': 24, 'E': 37, 'J': 13,
     'e': 37, 'j': 13},
    # 25
    {'+': 38, '-': 38, '0': 39, '1': 39,
     '2': 39, '3': 39, '4': 39, '5': 39,
     '6': 39, '7': 39, '8': 39, '9': 39},
    # 26
    {'0': 26, '1': 26, '2': 26, '3': 26,
     '4': 26, '5': 26, '6': 26, '7': 26,
     '8': 26, '9': 26, 'E': 37, 'J': 13,
     'e': 37, 'j': 13},
    # 27
    {},
    # 28
    {"'": 13},
    # 29
    {automata.DEFAULT: 40, '\n': 13, '\r': 14},
    # 30
    {automata.DEFAULT: 30, '\n': 27,
     '\r': 27, "'": 13, '\\': 29},
    # 31
    {'"': 13},
    # 32
    {automata.DEFAULT: 41, '\n': 13, '\r': 14},
    # 33
    {automata.DEFAULT: 33, '\n': 27,
     '\r': 27, '"': 13, '\\': 32},
    # 34
    {'0': 34, '1': 34, '2': 34, '3': 34,
     '4': 34, '5': 34, '6': 34, '7': 34,
     '8': 34, '9': 34, 'A': 34, 'B': 34,
     'C': 34, 'D': 34, 'E': 34, 'F': 34,
     'L': 13, 'a': 34, 'b': 34, 'c': 34,
     'd': 34, 'e': 34, 'f': 34, 'l': 13},
    # 35
    {'0': 35, '1': 35, '2': 35, '3': 35,
     '4': 35, '5': 35, '6': 35, '7': 35,
     'L': 13, 'l': 13},
    # 36
    {'0': 36, '1': 36, 'L': 13, 'l': 13},
    # 37
    {'+': 42, '-': 42, '0': 43, '1': 43,
     '2': 43, '3': 43, '4': 43, '5': 43,
     '6': 43, '7': 43, '8': 43, '9': 43},
    # 38
    {'0': 39, '1': 39, '2': 39, '3': 39,
     '4': 39, '5': 39, '6': 39, '7': 39,
     '8': 39, '9': 39},
    # 39
    {'0': 39, '1': 39, '2': 39, '3': 39,
     '4': 39, '5': 39, '6': 39, '7': 39,
     '8': 39, '9': 39, 'J': 13, 'j': 13},
    # 40
    {automata.DEFAULT: 40, '\n': 27,
     '\r': 27, "'": 13, '\\': 29},
    # 41
    {automata.DEFAULT: 41, '\n': 27,
     '\r': 27, '"': 13, '\\': 32},
    # 42
    {'0': 43, '1': 43, '2': 43, '3': 43,
     '4': 43, '5': 43, '6': 43, '7': 43,
     '8': 43, '9': 43},
    # 43
    {'0': 43, '1': 43, '2': 43, '3': 43,
     '4': 43, '5': 43, '6': 43, '7': 43,
     '8': 43, '9': 43, 'J': 13, 'j': 13},
    ]
pseudoDFA = automata.DFA(states, accepts)

accepts = [False, False, False, False, False, True]
states = [
    # 0
    {automata.DEFAULT: 0, '"': 1, '\\': 2},
    # 1
    {automata.DEFAULT: 4, '"': 3, '\\': 2},
    # 2
    {automata.DEFAULT: 4},
    # 3
    {automata.DEFAULT: 4, '"': 5, '\\': 2},
    # 4
    {automata.DEFAULT: 4, '"': 1, '\\': 2},
    # 5
    {automata.DEFAULT: 4, '"': 5, '\\': 2},
    ]
double3DFA = automata.NonGreedyDFA(states, accepts)

accepts = [False, False, False, False, False, True]
states = [
    # 0
    {automata.DEFAULT: 0, "'": 1, '\\': 2},
    # 1
    {automata.DEFAULT: 4, "'": 3, '\\': 2},
    # 2
    {automata.DEFAULT: 4},
    # 3
    {automata.DEFAULT: 4, "'": 5, '\\': 2},
    # 4
    {automata.DEFAULT: 4, "'": 1, '\\': 2},
    # 5
    {automata.DEFAULT: 4, "'": 5, '\\': 2},
    ]
single3DFA = automata.NonGreedyDFA(states, accepts)

accepts = [False, True, False, False]
states = [
    # 0
    {automata.DEFAULT: 0, "'": 1, '\\': 2},
    # 1
    {},
    # 2
    {automata.DEFAULT: 3},
    # 3
    {automata.DEFAULT: 3, "'": 1, '\\': 2},
    ]
singleDFA = automata.DFA(states, accepts)

accepts = [False, True, False, False]
states = [
    # 0
    {automata.DEFAULT: 0, '"': 1, '\\': 2},
    # 1
    {},
    # 2
    {automata.DEFAULT: 3},
    # 3
    {automata.DEFAULT: 3, '"': 1, '\\': 2},
    ]
doubleDFA = automata.DFA(states, accepts)

#_______________________________________________________________________
# End of automatically generated DFA's

endDFAs = {"'" : singleDFA,
           '"' : doubleDFA,
           'r' : None,
           'R' : None,
           'u' : None,
           'U' : None,
           'b' : None,
           'B' : None}

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

