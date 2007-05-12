import py
from py.__.doc.confrest import *

class PyPyPage(Page): 
    def fill_menubar(self):
        self.menubar = html.div(
            html.a("news",
                   href="http://codespeak.net/pypy/dist/pypy/doc/news.html",
                   class_="menu"), " ",
            html.a("getting-started",
                   href=self.get_doclink("getting-started.html"),
                   class_="menu"), " ",
            html.a("documentation", href=self.get_doclink("index.html"),
                   class_="menu"), " ",
            html.a("downloads", href=self.get_doclink("download.html"),
                   class_="menu"), " ",
            html.a("svn", href="https://codespeak.net/viewvc/pypy/dist/",
                   class_="menu"), " ",
            html.a("issues",
                   href="https://codespeak.net/issue/pypy-dev/",
                   class_="menu"),
            html.a("contact", href=self.get_doclink("contact.html"),
                   class_="menu"), " ",
            html.a("EU/project",
                   href="http://pypy.org/", class_="menu"), " ",
            " ", id="menubar")

    def get_doclink(self, target):
        return relpath(self.targetpath.strpath,
                       self.project.get_docpath().join(target).strpath)

class Project(Project): 
    mydir = py.magic.autopath().dirpath()

    title = "PyPy" 
    stylesheet = 'style.css'
    encoding = 'latin1' 
    prefix_title = "PyPy"
    logo = html.div(
        html.a(
            html.img(alt="PyPy", id="pyimg", 
                     src="http://codespeak.net/pypy/img/py-web1.png", 
                     height=110, width=149)))
    Page = PyPyPage 

    def get_docpath(self):
        return self.mydir
