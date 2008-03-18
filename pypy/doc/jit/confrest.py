from pypy.doc.confrest import *

class PyPyPage(PyPyPage): 
    def fill(self):
        super(PyPyPage, self).fill()
        self.menubar[:] = html.div(
            html.a("general documentation", href="../index.html",
                   class_="menu"), py.xml.raw("&nbsp;" * 3),
            html.a("JIT documentation", href="index.html",
                   class_="menu"), " ",
            " ", id="menubar")

class Project(Project): 
    stylesheet = "../style.css"
    title = "PyPy JIT"
    prefix_title = "PyPy JIT"
    Page = PyPyPage 
