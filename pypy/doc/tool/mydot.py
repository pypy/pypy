#!/usr/bin/env python

import py
import string
import re

nonalpha = "".join([chr(i) for i in range(256) if not chr(i).isalpha()])
replacement = (string.ascii_letters * (int(len(nonalpha) / len(string.ascii_letters)) + 1))[:len(nonalpha)]
transtable = string.maketrans(nonalpha, replacement)
del nonalpha
del replacement

def find_replacement(tex, used={}):
    replacement = tex.translate(transtable)
    while replacement in used:
        replacement += "a"
    used[replacement] = True
    return replacement

def create_tex_eps(dot, temppath):
    result = ["\\documentclass{article}",
              "\\usepackage[dvips]{graphicx}",
              "\\usepackage{psfrag}",
              "\\pagestyle{empty}",
              "\\begin{document}",
              "\\onecolumn"]
    texre = re.compile("(\$.*?\$)")
    dotcontent = dot.read()
    def repl(match, already_seen={}):
        tex = match.group(1)
        if tex in already_seen:
            return already_seen[tex]
        r = find_replacement(tex)
        already_seen[tex] = r
        result.append("\\psfrag{%s}[cc][cc]{%s}" % (r, tex))
        return r
    tempdot = temppath.join(dot.basename)
    eps = tempdot.new(ext='eps')
    dotcontent = texre.sub(repl, dotcontent)
    result.append("\\includegraphics{%s}" % eps)
    result.append("\\end{document}")
    tempdot.write(dotcontent)
    tex = eps.new(ext="tex")
    texcontent = "\n".join(result)
    tex.write(texcontent)

    epscontent = py.process.cmdexec("dot -Tps %s" % (tempdot, ))
    eps.write(re.sub("\n\[.*\]\nxshow", "\nshow", epscontent))
    return tex, eps
 
def process_dot(dot):
    temppath = py.test.ensuretemp("dot")
    tex, texcontent = create_tex_eps(dot, temppath)
    dvi = tex.new(ext="dvi")
    output = dvi.new(ext="ps")
    oldpath = dot.dirpath()
    dvi.dirpath().chdir()
    py.process.cmdexec("latex %s" % (tex, ))
    py.process.cmdexec("dvips -o %s %s" % (output, dvi))
    oldpath.chdir()
    return output

if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-T", dest="format",
                      help="output format")
    options, args = parser.parse_args()
    if len(args) != 1:
        raise ValueError, "need exactly one argument"
    psfile = process_dot(py.path.local(args[0]))
    if options.format == "ps":
        print psfile.read()
    elif options.format == "eps":
        py.process.cmdexec("ps2eps -l -f %s" % psfile)
        eps = psfile.new(ext="eps")
        print eps.read()
    elif options.format == "png":
        py.process.cmdexec("convert %s %s" %
                           (psfile, psfile.new(ext="png")))
        png = psfile.new(ext="png")
        print png.read()
    

