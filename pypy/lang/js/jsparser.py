
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
    stripped_code = code_string.replace("\n", "\\n")
    stripped_code = stripped_code.replace("'",r"\'")
    jsdir = py.path.local(__file__).dirpath().join("js")
    jsdefs = jsdir.join("jsdefs.js").read()
    jsparse = jsdir.join("jsparse.js").read()
    f = open('/tmp/jstobeparsed.js','w')
    f.write(jsdefs)
    f.write(jsparse)
    f.write("print(parse('%s'));\n" % stripped_code)
    f.close()
    pipe = os.popen("js -f /tmp/jstobeparsed.js", 'r')
    retval = pipe.read()
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
    t = parse_bytecode("\n".join(output))
    return t

def parse_bytecode(bytecode):
    t = parse_tree(bytecode)
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
