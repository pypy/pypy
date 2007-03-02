
from pypy.translator.js.modules import dom
from pypy.translator.js.modules.mochikit import log, createLoggingPane
from pypy.translator.js.examples.console.console import exported_methods

class Glob(object):
    pass

glob = Glob()

def add_text(txt):
    data_elem = dom.document.getElementById("data")
    if data_elem.childNodes:
        data = data_elem.childNodes[0].nodeValue + txt
    else:
        data = txt
    while data_elem.childNodes:
        data_elem.removeChild(data_elem.childNodes[0])
    data_elem.appendChild(dom.document.createTextNode(data))

def refresh_console(msg):
    inp_elem = dom.document.getElementById("inp")
    #inp_elem.disabled = False
    inp_elem.scrollIntoView()
    log(msg[0])
    if msg[0] == "refresh":
        data = msg[1]
        log(data)
        exported_methods.refresh_empty(glob.sess_id, refresh_console)
        add_text(data)
    elif msg[0] == 'disconnect':
        dom.document.getElementById("error").innerHTML = "ERROR! disconnected"

def set_sessid(sessid):
    glob.sess_id = sessid
    exported_methods.refresh_empty(sessid, refresh_console)

def empty_callback(msg):
    inp_elem = dom.document.getElementById("inp")
    #inp_elem.disabled = False
    inp_elem.scrollIntoView()

def keypressed(key):
    kc = key.keyCode
    if kc == ord("\r"):
        inp_elem = dom.document.getElementById("inp")
        cmd = inp_elem.value
        inp_elem.value = ''
        add_text(cmd + "\n")
        #if not cmd:
        #    exported_methods.refresh(glob.sess_id, cmd, empty_callback)
        #else:
        exported_methods.refresh(glob.sess_id, cmd + "\n", refresh_console)

def console_onload():
    createLoggingPane(True)
    inp_elem = dom.document.getElementById("inp")
    inp_elem.focus()
    dom.document.onkeypress = keypressed
    exported_methods.get_console(set_sessid)

