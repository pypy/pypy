#! /usr/bin/env python
# ______________________________________________________________________
"""Module pytokenize

This is a modified version of Ka-Ping Yee's tokenize module found in the
Python standard library.

The primary modification is the removal of the tokenizer's dependence on the
standard Python regular expression module, which is written in C.  The regular
expressions have been replaced with hand built DFA's using the
basil.util.automata module.

XXX This now assumes that the automata module is in the Python path.

$Id: pytokenize.py,v 1.3 2003/10/03 16:31:53 jriehl Exp $
"""
# ______________________________________________________________________

from __future__ import generators
import string
import automata

# ______________________________________________________________________
# COPIED:
from token import *

import token
__all__ = [x for x in dir(token) if x[0] != '_'] + ["COMMENT", "tokenize",
           "generate_tokens", "NL"]
del x
del token

COMMENT = N_TOKENS
tok_name[COMMENT] = 'COMMENT'
NL = N_TOKENS + 1
tok_name[NL] = 'NL'
N_TOKENS += 2

# ______________________________________________________________________
# Automatically generated DFA's (with one or two hand tweeks):

pseudoStates = [[{'\t': 0, '\n': 13, '\x0c': 0, '\r': 14, ' ': 0, '!': 10,
                  '"': 16, '#': 18, '%': 12, '&': 12,
                  "'": 15, '(': 13, ')': 13, '*': 7,
                  '+': 12, ',': 13, '-': 12, '.': 6,
                  '/': 11, '0': 4, '1': 5, '2': 5,
                  '3': 5, '4': 5, '5': 5, '6': 5,
                  '7': 5, '8': 5, '9': 5, ':': 13,
                  ';': 13, '<': 9, '=': 12, '>': 8, 'A': 1,
                  'B': 1, 'C': 1, 'D': 1, 'E': 1,
                  'F': 1, 'G': 1, 'H': 1, 'I': 1,
                  'J': 1, 'K': 1, 'L': 1, 'M': 1,
                  'N': 1, 'O': 1, 'P': 1, 'Q': 1,
                  'R': 2, 'S': 1, 'T': 1, 'U': 3,
                  'V': 1, 'W': 1, 'X': 1, 'Y': 1,
                  'Z': 1, '[': 13, '\\': 17, ']': 13,
                  '^': 12, '_': 1, '`': 13, 'a': 1,
                  'b': 1, 'c': 1, 'd': 1, 'e': 1,
                  'f': 1, 'g': 1, 'h': 1, 'i': 1,
                  'j': 1, 'k': 1, 'l': 1, 'm': 1,
                  'n': 1, 'o': 1, 'p': 1, 'q': 1,
                  'r': 2, 's': 1, 't': 1, 'u': 3,
                  'v': 1, 'w': 1, 'x': 1, 'y': 1,
                  'z': 1, '{': 13, '|': 12, '}': 13,
                  '~': 13},
                 True],
                [{'0': 1, '1': 1, '2': 1, '3': 1,
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
                 True],
                [{'"': 20, "'": 19, '0': 1, '1': 1,
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
                 True],
                [{'"': 20, "'": 19, '0': 1, '1': 1,
                  '2': 1, '3': 1, '4': 1, '5': 1,
                  '6': 1, '7': 1, '8': 1, '9': 1,
                  'A': 1, 'B': 1, 'C': 1, 'D': 1,
                  'E': 1, 'F': 1, 'G': 1, 'H': 1,
                  'I': 1, 'J': 1, 'K': 1, 'L': 1,
                  'M': 1, 'N': 1, 'O': 1, 'P': 1,
                  'Q': 1, 'R': 2, 'S': 1, 'T': 1,
                  'U': 1, 'V': 1, 'W': 1, 'X': 1,
                  'Y': 1, 'Z': 1, '_': 1, 'a': 1,
                  'b': 1, 'c': 1, 'd': 1, 'e': 1,
                  'f': 1, 'g': 1, 'h': 1, 'i': 1,
                  'j': 1, 'k': 1, 'l': 1, 'm': 1,
                  'n': 1, 'o': 1, 'p': 1, 'q': 1,
                  'r': 2, 's': 1, 't': 1, 'u': 1,
                  'v': 1, 'w': 1, 'x': 1, 'y': 1,
                  'z': 1},
                 True],
                [{'.': 24, '0': 22, '1': 22, '2': 22,
                  '3': 22, '4': 22, '5': 22, '6': 22,
                  '7': 22, '8': 23, '9': 23, 'E': 25,
                  'J': 13, 'L': 13, 'X': 21, 'e': 25,
                  'j': 13, 'l': 13, 'x': 21},
                 True],
                [{'.': 24, '0': 5, '1': 5, '2': 5,
                  '3': 5, '4': 5, '5': 5, '6': 5,
                  '7': 5, '8': 5, '9': 5, 'E': 25,
                  'J': 13, 'L': 13, 'e': 25, 'j': 13,
                  'l': 13},
                 True],
                [{'0': 26, '1': 26, '2': 26, '3': 26,
                  '4': 26, '5': 26, '6': 26, '7': 26,
                  '8': 26, '9': 26},
                 True],
                [{'*': 12, '=': 13}, True],
                [{'=': 13, '>': 12}, True],
                [{'=': 13, '<': 12, '>': 13}, True],
                [{'=': 13}, False],
                [{'=': 13, '/': 12}, True],
                [{'=': 13}, True],
                [{}, True],
                [{'\n': 13}, False],
                [{automata.DEFAULT: 19, '\n': 27, '\\': 29, "'": 28},
                 False],
                [{automata.DEFAULT: 20, '"': 30, '\n': 27, '\\': 31},
                 False],
                [{'\n': 13, '\r': 14}, False],
                [{automata.DEFAULT: 18, '\n': 27, '\r': 27}, True],
                [{automata.DEFAULT: 19, '\n': 27, '\\': 29, "'": 13},
                 False],
                [{automata.DEFAULT: 20, '"': 13, '\n': 27, '\\': 31},
                 False],
                [{'0': 21, '1': 21, '2': 21, '3': 21,
                  '4': 21, '5': 21, '6': 21, '7': 21,
                  '8': 21, '9': 21, 'A': 21, 'B': 21,
                  'C': 21, 'D': 21, 'E': 21, 'F': 21,
                  'L': 13, 'a': 21, 'b': 21, 'c': 21,
                  'd': 21, 'e': 21, 'f': 21, 'l': 13},
                 True],
                [{'.': 24, '0': 22, '1': 22, '2': 22,
                  '3': 22, '4': 22, '5': 22, '6': 22,
                  '7': 22, '8': 23, '9': 23, 'E': 25,
                  'J': 13, 'L': 13, 'e': 25, 'j': 13,
                  'l': 13},
                 True],
                [{'.': 24, '0': 23, '1': 23, '2': 23,
                  '3': 23, '4': 23, '5': 23, '6': 23,
                  '7': 23, '8': 23, '9': 23, 'E': 25,
                  'J': 13, 'e': 25, 'j': 13},
                 False],
                [{'0': 24, '1': 24, '2': 24, '3': 24,
                  '4': 24, '5': 24, '6': 24, '7': 24,
                  '8': 24, '9': 24, 'E': 32, 'J': 13,
                  'e': 32, 'j': 13},
                 True],
                [{'+': 33, '-': 33, '0': 34, '1': 34,
                  '2': 34, '3': 34, '4': 34, '5': 34,
                  '6': 34, '7': 34, '8': 34, '9': 34},
                 False],
                [{'0': 26, '1': 26, '2': 26, '3': 26,
                  '4': 26, '5': 26, '6': 26, '7': 26,
                  '8': 26, '9': 26, 'E': 32, 'J': 13,
                  'e': 32, 'j': 13},
                 True],
                [{}, False],
                [{"'": 13}, True],
                [{automata.DEFAULT: 35, '\n': 13, '\r': 14}, False],
                [{'"': 13}, True],
                [{automata.DEFAULT: 36, '\n': 13, '\r': 14}, False],
                [{'+': 37, '-': 37, '0': 38, '1': 38,
                  '2': 38, '3': 38, '4': 38, '5': 38,
                  '6': 38, '7': 38, '8': 38, '9': 38},
                 False],
                [{'0': 34, '1': 34, '2': 34, '3': 34,
                  '4': 34, '5': 34, '6': 34, '7': 34,
                  '8': 34, '9': 34},
                 False],
                [{'0': 34, '1': 34, '2': 34, '3': 34,
                  '4': 34, '5': 34, '6': 34, '7': 34,
                  '8': 34, '9': 34, 'J': 13, 'j': 13},
                 True],
                [{automata.DEFAULT: 35, '\n': 27, '\\': 29, "'": 13},
                 False],
                [{automata.DEFAULT: 36, '"': 13, '\n': 27, '\\': 31},
                 False],
                [{'0': 38, '1': 38, '2': 38, '3': 38,
                  '4': 38, '5': 38, '6': 38, '7': 38,
                  '8': 38, '9': 38},
                 False],
                [{'0': 38, '1': 38, '2': 38, '3': 38,
                  '4': 38, '5': 38, '6': 38, '7': 38,
                  '8': 38, '9': 38, 'J': 13, 'j': 13},
                 True]]
pseudoDFA = automata.DFA(pseudoStates)

double3States = [[{automata.DEFAULT: 0, '"': 1, '\\': 2}, False],
                 [{automata.DEFAULT: 4, '"': 3, '\\': 2}, False],
                 [{automata.DEFAULT: 4}, False],
                 [{automata.DEFAULT: 4, '"': 5, '\\': 2}, False],
                 [{automata.DEFAULT: 4, '"': 1, '\\': 2}, False],
                 [{automata.DEFAULT: 4, '"': 5, '\\': 2}, True]]
double3DFA = automata.NonGreedyDFA(double3States)

single3States = [[{automata.DEFAULT: 0, '\\': 2, "'": 1}, False],
                 [{automata.DEFAULT: 4, '\\': 2, "'": 3}, False],
                 [{automata.DEFAULT: 4}, False],
                 [{automata.DEFAULT: 4, '\\': 2, "'": 5}, False],
                 [{automata.DEFAULT: 4, '\\': 2, "'": 1}, False],
                 [{automata.DEFAULT: 4, '\\': 2, "'": 5}, True]]
single3DFA = automata.NonGreedyDFA(single3States)

singleStates = [[{automata.DEFAULT: 0, '\\': 2, "'": 1}, False],
                [{}, True],
                [{automata.DEFAULT: 0}, False]]
singleDFA = automata.DFA(singleStates)

doubleStates = [[{automata.DEFAULT: 0, '"': 1, '\\': 2}, False],
                [{}, True],
                [{automata.DEFAULT: 0}, False]]
doubleDFA = automata.DFA(doubleStates)

endDFAs = {"'" : singleDFA,
           '"' : doubleDFA,
           "r" : None,
           "R" : None,
           "u" : None,
           "U" : None}

for uniPrefix in ("", "u", "U"):
    for rawPrefix in ("", "r", "R"):
        prefix = uniPrefix + rawPrefix
        endDFAs[prefix + "'''"] = single3DFA
        endDFAs[prefix + '"""'] = double3DFA

whiteSpaceStates = [[{'\t': 0, ' ': 0, '\x0c': 0}, True]]
whiteSpaceDFA = automata.DFA(whiteSpaceStates)

# ______________________________________________________________________
# COPIED:

triple_quoted = {}
for t in ("'''", '"""',
          "r'''", 'r"""', "R'''", 'R"""',
          "u'''", 'u"""', "U'''", 'U"""',
          "ur'''", 'ur"""', "Ur'''", 'Ur"""',
          "uR'''", 'uR"""', "UR'''", 'UR"""'):
    triple_quoted[t] = t
single_quoted = {}
for t in ("'", '"',
          "r'", 'r"', "R'", 'R"',
          "u'", 'u"', "U'", 'U"',
          "ur'", 'ur"', "Ur'", 'Ur"',
          "uR'", 'uR"', "UR'", 'UR"' ):
    single_quoted[t] = t

tabsize = 8

class TokenError(Exception): pass

class StopTokenizing(Exception): pass

def printtoken(type, token, (srow, scol), (erow, ecol), line): # for testing
    print "%d,%d-%d,%d:\t%s\t%s" % \
        (srow, scol, erow, ecol, tok_name[type], repr(token))

def tokenize(readline, tokeneater=printtoken):
    """
    The tokenize() function accepts two parameters: one representing the
    input stream, and one providing an output mechanism for tokenize().

    The first parameter, readline, must be a callable object which provides
    the same interface as the readline() method of built-in file objects.
    Each call to the function should return one line of input as a string.

    The second parameter, tokeneater, must also be a callable object. It is
    called once for each token, with five arguments, corresponding to the
    tuples generated by generate_tokens().
    """
    try:
        tokenize_loop(readline, tokeneater)
    except StopTokenizing:
        pass

# backwards compatible interface
def tokenize_loop(readline, tokeneater):
    for token_info in generate_tokens(readline):
        tokeneater(*token_info)

def generate_tokens(readline):
    """
    The generate_tokens() generator requires one argment, readline, which
    must be a callable object which provides the same interface as the
    readline() method of built-in file objects. Each call to the function
    should return one line of input as a string.

    The generator produces 5-tuples with these members: the token type; the
    token string; a 2-tuple (srow, scol) of ints specifying the row and
    column where the token begins in the source; a 2-tuple (erow, ecol) of
    ints specifying the row and column where the token ends in the source;
    and the line on which the token was found. The line passed is the
    logical line; continuation lines are included.
    """
    lnum = parenlev = continued = 0
    namechars, numchars = string.ascii_letters + '_', '0123456789'
    contstr, needcont = '', 0
    contline = None
    indents = [0]

    while 1:                                   # loop over lines in stream
        line = readline()
        lnum = lnum + 1
        pos, max = 0, len(line)

        if contstr:                            # continued string
            if not line:
                raise TokenError, ("EOF in multi-line string", strstart)
            endmatch = endDFA.recognize(line)
            if -1 != endmatch:
                pos = end = endmatch
                yield (STRING, contstr + line[:end],
                           strstart, (lnum, end), contline + line)
                contstr, needcont = '', 0
                contline = None
            elif needcont and line[-2:] != '\\\n' and line[-3:] != '\\\r\n':
                yield (ERRORTOKEN, contstr + line,
                           strstart, (lnum, len(line)), contline)
                contstr = ''
                contline = None
                continue
            else:
                contstr = contstr + line
                contline = contline + line
                continue

        elif parenlev == 0 and not continued:  # new statement
            if not line: break
            column = 0
            while pos < max:                   # measure leading whitespace
                if line[pos] == ' ': column = column + 1
                elif line[pos] == '\t': column = (column/tabsize + 1)*tabsize
                elif line[pos] == '\f': column = 0
                else: break
                pos = pos + 1
            if pos == max: break

            if line[pos] in '#\r\n':           # skip comments or blank lines
                yield ((NL, COMMENT)[line[pos] == '#'], line[pos:],
                           (lnum, pos), (lnum, len(line)), line)
                continue

            if column > indents[-1]:           # count indents or dedents
                indents.append(column)
                yield (INDENT, line[:pos], (lnum, 0), (lnum, pos), line)
            while column < indents[-1]:
                indents = indents[:-1]
                yield (DEDENT, '', (lnum, pos), (lnum, pos), line)

        else:                                  # continued statement
            if not line:
                raise TokenError, ("EOF in multi-line statement", (lnum, 0))
            continued = 0

        while pos < max:
            pseudomatch = pseudoDFA.recognize(line, pos)
            if -1 != pseudomatch:                            # scan for tokens
                # JDR: Modified
                start = whiteSpaceDFA.recognize(line, pos)
                if -1 == start:
                    start = pos
                end = pseudomatch

                spos, epos, pos = (lnum, start), (lnum, end), end
                token, initial = line[start:end], line[start]

                if initial in numchars or \
                   (initial == '.' and token != '.'):      # ordinary number
                    yield (NUMBER, token, spos, epos, line)
                elif initial in '\r\n':
                    yield (parenlev > 0 and NL or NEWLINE,
                               token, spos, epos, line)
                elif initial == '#':
                    yield (COMMENT, token, spos, epos, line)
                elif token in triple_quoted:
                    endDFA = endDFAs[token]
                    endmatch = endDFA.recognize(line, pos)
                    if -1 != endmatch:                     # all on one line
                        pos = endmatch
                        token = line[start:pos]
                        yield (STRING, token, spos, (lnum, pos), line)
                    else:
                        strstart = (lnum, start)           # multiple lines
                        contstr = line[start:]
                        contline = line
                        break
                elif initial in single_quoted or \
                    token[:2] in single_quoted or \
                    token[:3] in single_quoted:
                    if token[-1] == '\n':                  # continued string
                        strstart = (lnum, start)
                        endDFA = (endDFAs[initial] or endDFAs[token[1]] or
                                   endDFAs[token[2]])
                        contstr, needcont = line[start:], 1
                        contline = line
                        break
                    else:                                  # ordinary string
                        yield (STRING, token, spos, epos, line)
                elif initial in namechars:                 # ordinary name
                    yield (NAME, token, spos, epos, line)
                elif initial == '\\':                      # continued stmt
                    continued = 1
                else:
                    if initial in '([{': parenlev = parenlev + 1
                    elif initial in ')]}': parenlev = parenlev - 1
                    yield (OP, token, spos, epos, line)
            else:
                yield (ERRORTOKEN, line[pos],
                           (lnum, pos), (lnum, pos+1), line)
                pos = pos + 1

    for indent in indents[1:]:                 # pop remaining indent levels
        yield (DEDENT, '', (lnum, 0), (lnum, 0), '')
    yield (ENDMARKER, '', (lnum, 0), (lnum, 0), '')

# ______________________________________________________________________)

def main ():
    import sys
    if len(sys.argv) > 1:
        tokenize(open(sys.argv[1]).readline)
    else:
        tokenize(sys.stdin.readline)

# ______________________________________________________________________

if __name__ == '__main__':
    main()

# ______________________________________________________________________
# End of pytokenize.py
