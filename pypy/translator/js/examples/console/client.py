
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

def create_text(txt):
    return dom.document.createTextNode(txt)

def set_text(txt):
    data_elem = dom.document.getElementById("data")
    while data_elem.childNodes:
        data_elem.removeChild(data_elem.childNodes[0])
    data_elem.appendChild(dom.document.createTextNode(txt))    

def refresh_console(msg):
    inp_elem = dom.document.getElementById("inp")
    #inp_elem.disabled = False
    if msg[0] == "refresh":
        data = msg[1]
        if data:
            inp_elem.scrollIntoView()
        inp_elem.focus()
        exported_methods.refresh_empty(glob.sess_id, refresh_console)
        add_text(data)
    elif msg[0] == 'disconnected':
        inp_elem.disabled = True
        name_bar = dom.document.getElementById("namebar")
        name_bar.style.color = "red"
        text = name_bar.lastChild.nodeValue
        name_bar.removeChild(name_bar.lastChild)
        name_bar.appendChild(create_text(text + " [DEFUNCT]"))

def set_sessid(data):
    sessid = int(data[0])
    help_msg = data[1]
    glob.sess_id = sessid
    inp_elem = dom.document.getElementById("inp")
    inp_elem.disabled = False 
    name_bar = dom.document.getElementById("namebar")
    name_bar.style.color = "black"
    name_bar.removeChild(name_bar.lastChild)
    name_bar.appendChild(create_text("Python console"))
    dom.document.getElementById("helpcontents").innerHTML = help_msg
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

def nothing2(msg):
    pass

def cleanup_console():
    inp_elem = dom.document.getElementById("inp")
    inp_elem.disabled = True
    set_text("")
    exported_methods.kill_console(glob.sess_id, nothing2)

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

def add_snippet(snippet):
    add_text(snippet)
    exported_methods.refresh(glob.sess_id, snippet, refresh_console)

def execute_snippet(name='python', number=3):
    exported_methods.execute_snippet(name, number, add_snippet)

def console_onload():
    #createLoggingPane(True)
    #inp_elem = dom.document.getElementById("inp")
    #inp_elem.focus()
    dom.document.onkeypress = keypressed
    #exported_methods.get_console("python", set_sessid)

