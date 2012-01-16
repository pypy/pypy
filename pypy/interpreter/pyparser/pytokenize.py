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
           False, False, True, False, False, False, False,
           True, False, True, False, True, False, False,
           True, False, False, True, True, True, False,
           False, True, False, False, False, True]
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
     'U': 1, 'V': 1, 'W': 1, 'X': 1,
     'Y': 1, 'Z': 1, '[': 13, '\\': 17,
     ']': 13, '^': 12, '_': 1, '`': 13,
     'a': 1, 'b': 2, 'c': 1, 'd': 1,
     'e': 1, 'f': 1, 'g': 1, 'h': 1,
     'i': 1, 'j': 1, 'k': 1, 'l': 1,
     'm': 1, 'n': 1, 'o': 1, 'p': 1,
     'q': 1, 'r': 3, 's': 1, 't': 1,
     'u': 1, 'v': 1, 'w': 1, 'x': 1,
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
    {'.': 23, '0': 22, '1': 22, '2': 22,
     '3': 22, '4': 22, '5': 22, '6': 22,
     '7': 22, '8': 22, '9': 22, 'B': 21,
     'E': 24, 'J': 13, 'O': 20, 'X': 19,
     'b': 21, 'e': 24, 'j': 13, 'o': 20,
     'x': 19},
    # 5
    {'.': 23, '0': 5, '1': 5, '2': 5,
     '3': 5, '4': 5, '5': 5, '6': 5,
     '7': 5, '8': 5, '9': 5, 'E': 24,
     'J': 13, 'e': 24, 'j': 13},
    # 6
    {'0': 25, '1': 25, '2': 25, '3': 25,
     '4': 25, '5': 25, '6': 25, '7': 25,
     '8': 25, '9': 25},
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
    {automata.DEFAULT: 29, '\n': 26,
     '\r': 26, "'": 27, '\\': 28},
    # 16
    {automata.DEFAULT: 32, '\n': 26,
     '\r': 26, '"': 30, '\\': 31},
    # 17
    {'\n': 13, '\r': 14},
    # 18
    {automata.DEFAULT: 18, '\n': 26, '\r': 26},
    # 19
    {'0': 33, '1': 33, '2': 33, '3': 33,
     '4': 33, '5': 33, '6': 33, '7': 33,
     '8': 33, '9': 33, 'A': 33, 'B': 33,
     'C': 33, 'D': 33, 'E': 33, 'F': 33,
     'a': 33, 'b': 33, 'c': 33, 'd': 33,
     'e': 33, 'f': 33},
    # 20
    {'0': 34, '1': 34, '2': 34, '3': 34,
     '4': 34, '5': 34, '6': 34, '7': 34},
    # 21
    {'0': 35, '1': 35},
    # 22
    {'.': 23, '0': 22, '1': 22, '2': 22,
     '3': 22, '4': 22, '5': 22, '6': 22,
     '7': 22, '8': 22, '9': 22, 'E': 24,
     'J': 13, 'e': 24, 'j': 13},
    # 23
    {'0': 23, '1': 23, '2': 23, '3': 23,
     '4': 23, '5': 23, '6': 23, '7': 23,
     '8': 23, '9': 23, 'E': 36, 'J': 13,
     'e': 36, 'j': 13},
    # 24
    {'+': 37, '-': 37, '0': 38, '1': 38,
     '2': 38, '3': 38, '4': 38, '5': 38,
     '6': 38, '7': 38, '8': 38, '9': 38},
    # 25
    {'0': 25, '1': 25, '2': 25, '3': 25,
     '4': 25, '5': 25, '6': 25, '7': 25,
     '8': 25, '9': 25, 'E': 36, 'J': 13,
     'e': 36, 'j': 13},
    # 26
    {},
    # 27
    {"'": 13},
    # 28
    {automata.DEFAULT: 39, '\n': 13, '\r': 14},
    # 29
    {automata.DEFAULT: 29, '\n': 26,
     '\r': 26, "'": 13, '\\': 28},
    # 30
    {'"': 13},
    # 31
    {automata.DEFAULT: 40, '\n': 13, '\r': 14},
    # 32
    {automata.DEFAULT: 32, '\n': 26,
     '\r': 26, '"': 13, '\\': 31},
    # 33
    {'0': 33, '1': 33, '2': 33, '3': 33,
     '4': 33, '5': 33, '6': 33, '7': 33,
     '8': 33, '9': 33, 'A': 33, 'B': 33,
     'C': 33, 'D': 33, 'E': 33, 'F': 33,
     'a': 33, 'b': 33, 'c': 33, 'd': 33,
     'e': 33, 'f': 33},
    # 34
    {'0': 34, '1': 34, '2': 34, '3': 34,
     '4': 34, '5': 34, '6': 34, '7': 34},
    # 35
    {'0': 35, '1': 35},
    # 36
    {'+': 41, '-': 41, '0': 42, '1': 42,
     '2': 42, '3': 42, '4': 42, '5': 42,
     '6': 42, '7': 42, '8': 42, '9': 42},
    # 37
    {'0': 38, '1': 38, '2': 38, '3': 38,
     '4': 38, '5': 38, '6': 38, '7': 38,
     '8': 38, '9': 38},
    # 38
    {'0': 38, '1': 38, '2': 38, '3': 38,
     '4': 38, '5': 38, '6': 38, '7': 38,
     '8': 38, '9': 38, 'J': 13, 'j': 13},
    # 39
    {automata.DEFAULT: 39, '\n': 26,
     '\r': 26, "'": 13, '\\': 28},
    # 40
    {automata.DEFAULT: 40, '\n': 26,
     '\r': 26, '"': 13, '\\': 31},
    # 41
    {'0': 42, '1': 42, '2': 42, '3': 42,
     '4': 42, '5': 42, '6': 42, '7': 42,
     '8': 42, '9': 42},
    # 42
    {'0': 42, '1': 42, '2': 42, '3': 42,
     '4': 42, '5': 42, '6': 42, '7': 42,
     '8': 42, '9': 42, 'J': 13, 'j': 13},
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
           'b' : None,
           'B' : None}

for uniPrefix in ("", "b", "B"):
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
          "b'''", 'b"""', "B'''", 'B"""',
          "br'''", 'br"""', "Br'''", 'Br"""',
          "bR'''", 'bR"""', "BR'''", 'BR"""'):
    triple_quoted[t] = t
single_quoted = {}
for t in ("'", '"',
          "r'", 'r"', "R'", 'R"',
          "b'", 'b"', "B'", 'B"',
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

