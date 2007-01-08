
""" Using narcisus to generate code
"""

# TODO Should be replaced by a real parser

import os
import py
import re
from subprocess import Popen, PIPE, STDOUT
from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
from pypy.rlib.parsing.ebnfparse import Symbol

class JsSyntaxError(Exception):
    pass

def read_js_output(code_string):
    stripped_code = code_string.replace("\n", "")
    jsdir = py.path.local(__file__).dirpath().join("js")
    jsdefs = jsdir.join("jsdefs.js").read()
    jsparse = jsdir.join("jsparse.js").read()
    pipe = Popen("js", stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    pipe.stdin.write(jsdefs + jsparse + "\n")
    stripped_code = stripped_code.replace("'",r"\'")
    pipe.stdin.write("print(parse('%s'));\n" % stripped_code)
    pipe.stdin.close()
    retval = pipe.stdout.read()
    if not retval.startswith("{"):
        raise JsSyntaxError(retval)
    return retval

def unquote(t):
    if isinstance(t, Symbol):
        if t.symbol == "QUOTED_STRING":
            t.additional_info = t.additional_info.strip("'")
    else:
        for i in t.children:
            unquote(i)

def parse(code_string):
    read_code = read_js_output(code_string)
    output = read_code.split(os.linesep)
    #print '\n'.join(output)
    t = parse_bytecode("\n".join(output))
    #print "-----------------\n",t
    #print "-----------------\n",t.children[0].children[0].additional_info
    return t

def parse_bytecode(bytecode):
    t = parse_tree(bytecode)
    #print "0000000",t
    tree = ToAST().transform(t)
    unquote(tree)
    return tree

regexs, rules, ToAST = parse_ebnf("""
    QUOTED_STRING: "'[^\\']*'";
    IGNORE: " |\n";
    data: <dict> | <QUOTED_STRING> | <list>;
    dict: ["{"] (dictentry [","])* dictentry ["}"];
    dictentry: QUOTED_STRING [":"] data;
    list: ["["] (data [","])* data ["]"];
""")
parse_tree = make_parse_function(regexs, rules, eof=True)
