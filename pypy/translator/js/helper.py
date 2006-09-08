
""" Some helpers
"""

from pypy.translator.js.modules._dom import get_document

def escape(s):
    #return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"). \
    #    replace("'", "\\'").replace(" ", "&nbsp;").replace("\n", "<br/>")
    return s

def create_debug_div():
    debug_div = get_document().createElement("div")
    # XXX attach it somewhere...
    #body = get_document().getElementsByTagName('body')[0]
    get_document().childNodes[0].childNodes[1].appendChild(debug_div)
    return debug_div

def show_traceback(tb, exc):
    debug_div = get_document().getElementById("debug_div")
    if not debug_div:
        # create div here
        debug_div = create_debug_div()

    pre_div = get_document().createElement("pre")
    pre_div.style.color = "#FF0000"
    debug_div.appendChild(pre_div)
    txt = get_document().createTextNode("")
    pre_div.appendChild(txt)
    for tb_entry in tb[1:]:
        # list of tuples...
        fun_name, args, filename, lineno = tb_entry
        # some source maybe? or so?
        line1 = escape("%s %s" % (fun_name, args))
        line2 = escape("  %s: %s\n" % (filename, lineno))
        txt.nodeValue += line1 + '\n' + line2

    txt.nodeValue += str(exc)
