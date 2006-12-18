
""" Using narcisus to generate code
"""

# TODO Should be replaced by a real parser

import os
import py
import re
from subprocess import Popen, PIPE, STDOUT

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

def parse(code_string):
    read_code = read_js_output(code_string)
    output = read_code.split(os.linesep)
    #print '\n'.join(output)
    try:
        code = eval("\n".join(output))
    except (SyntaxError, NameError):
        for num, line in enumerate(output):
            print "%d: %s" % (num + 1, line)
        open("/tmp/out", "w").write("\n".join(output))
        raise
    return code
