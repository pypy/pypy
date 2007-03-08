
""" Using narcisus to generate code
"""

# TODO Should be replaced by a real parser

import os
import os.path as path
import re
from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
from pypy.rlib.parsing.ebnfparse import Symbol
from pypy.rlib.streamio import open_file_as_stream, fdopen_as_stream

DEBUG = False

class JsSyntaxError(Exception):
    pass

SLASH = "\\"
jsdir = path.join(path.dirname(__file__),"js")
jsdefspath = path.join(jsdir, "jsdefs.js")
jsparsepath = path.join(jsdir, "jsparse.js")
fname = path.join(path.dirname(__file__) ,"tobeparsed.js")
command = 'js -f %s -f %s -f %s'%(jsdefspath, jsparsepath, fname)

def read_js_output(code_string):
    tmp = []
    last = ""
    for c in code_string:
        if c == "'" and last != SLASH:
            tmp.append("\\'")
        else:
            if c == SLASH:
                tmp.append(SLASH*2)
            elif c == "\n":
                tmp.append("\\n")
            else:
                tmp.append(c)
    stripped_code = "".join(tmp)
    if DEBUG:
        print "------ got:"
        print code_string
        print "------ put:"
        print stripped_code
    f = open_file_as_stream(fname, 'w')
    f.write("print(parse('%s'));\n" % stripped_code)
    f.close()
    c2pread, c2pwrite = os.pipe()
    if os.fork() == 0:
        #child
        os.dup2(c2pwrite, 1)
        for i in range(3, 256):
            try:
                os.close(i)
            except OSError:
                pass
        cmd = ['/bin/sh', '-c', command]
        os.execv(cmd[0], cmd)
    os.close(c2pwrite)
    f = fdopen_as_stream(c2pread, 'r', 0)
    retval = f.readall()
    f.close()
    if not retval.startswith("{"):
        raise JsSyntaxError(retval)
    if DEBUG:
        print "received back:"
        print retval
    return retval

def unquote(t):
    if isinstance(t, Symbol):
        if t.symbol == "QUOTED_STRING":
            stop = len(t.additional_info)-1
            if stop < 0:
                stop = 0
            t.additional_info = t.additional_info[1:stop]
            temp = []
            last = ""
            for char in t.additional_info:
                if last == SLASH:
                    if char == SLASH:
                        temp.append(SLASH)
                if char != SLASH:        
                    temp.append(char)
                last = char
            t.additional_info = ''.join(temp)
    else:
        for i in t.children:
            unquote(i)

def parse(code_string):
    read_code = read_js_output(code_string)
    output = read_code.split(os.linesep)
    t = parse_bytecode("\n".join(output))
    return t

def parse_bytecode(bytecode):
    # print bytecode
    t = parse_tree(bytecode)
    tree = ToAST().transform(t)
    unquote(tree)
    return tree

regexs, rules, ToAST = parse_ebnf(r"""
    QUOTED_STRING: "'([^\\\']|\\[\\\'])*'";"""+"""
    IGNORE: " |\n";
    data: <dict> | <QUOTED_STRING> | <list>;
    dict: ["{"] (dictentry [","])* dictentry ["}"];
    dictentry: QUOTED_STRING [":"] data;
    list: ["["] (data [","])* data ["]"];
""")
parse_tree = make_parse_function(regexs, rules, eof=True)
