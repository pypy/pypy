
""" Some helpers
"""

from pypy.translator.js.modules.dom import document

def escape(s):
    #return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"). \
    #    replace("'", "\\'").replace(" ", "&nbsp;").replace("\n", "<br/>")
    return s

def create_debug_div():
    debug_div = document.createElement("div")
    debug_div.setAttribute("id", "debug_div")
    # XXX attach it somewhere...
    #body = document.getElementsByTagName('body')[0]
    document.childNodes[0].childNodes[1].appendChild(debug_div)
    return debug_div

def __show_traceback(tb, exc):
    debug_div = document.getElementById("debug_div")
    if not debug_div:
        # create div here
        debug_div = create_debug_div()

    pre_div = document.createElement("pre")
    pre_div.style.color = "#FF0000"
    debug_div.appendChild(pre_div)
    txt = document.createTextNode("")
    pre_div.appendChild(txt)
    for tb_entry in tb[1:]:
        # list of tuples...
        fun_name, args, filename, lineno = tb_entry
        # some source maybe? or so?
        line1 = escape("%s %s" % (fun_name, args))
        line2 = escape("  %s: %s\n" % (filename, lineno))
        txt.nodeValue += line1 + '\n' + line2

    txt.nodeValue += str(exc)

__show_traceback.explicit_traceback = True
