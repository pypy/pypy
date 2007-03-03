
from pypy.translator.js.modules import dom
from pypy.translator.js.modules.mochikit import log, createLoggingPane
from pypy.translator.js.examples.console.console import exported_methods

class Glob(object):
    def __init__(self):
        self.console_running = False

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

def set_text(txt):
    data_elem = dom.document.getElementById("data")
    while data_elem.childNodes:
        data_elem.removeChild(data_elem.childNodes[0])
    data_elem.appendChild(dom.document.createTextNode(txt))    

def refresh_console(msg):
    inp_elem = dom.document.getElementById("inp")
    #inp_elem.disabled = False
    if msg[0] == "refresh":
        inp_elem.scrollIntoView()
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

def nothing(msg):
    pass

def cleanup_console():
    inp_elem = dom.document.getElementById("inp")
    inp_elem.disabled = True
    set_text("")
    exported_methods.kill_console(glob.sess_id, nothing)

def load_console(python="python"):
    if glob.console_running:
        cleanup_console()
    inp_elem = dom.document.getElementById("inp")
    main = dom.document.getElementById("main")
    main.style.visibility = "visible"
    inp_elem.disabled = False
    inp_elem.focus()
    glob.console_running = True
    exported_methods.get_console(python, set_sessid)

def console_onload():
    #createLoggingPane(True)
    #inp_elem = dom.document.getElementById("inp")
    #inp_elem.focus()
    dom.document.onkeypress = keypressed
    #exported_methods.get_console("python", set_sessid)

