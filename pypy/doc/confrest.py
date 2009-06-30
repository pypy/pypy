import py

# XXX importing/inheriting from an internal py lib class is hackish
from confrest_oldpy import Project, Page, relpath
html = py.xml.html

class PyPyPage(Page): 
    def fill_menubar(self):
        self.menubar = html.div(
            html.a("home", 
                   href=self.get_doclink("index.html"), 
                   class_="menu"), 
            " ",
            html.a("blog", href="http://morepypy.blogspot.com", class_="menu"),
            " ", 
            html.a("getting-started",
                   href=self.get_doclink("getting-started.html"),
                   class_="menu"), 
            " ",
            html.a("documentation", href=self.get_doclink("docindex.html"),
                   class_="menu"),
            " ", 
            html.a("svn", href="https://codespeak.net/viewvc/pypy/trunk/",
                   class_="menu"),
            " ", 
            html.a("issues",
                   href="https://codespeak.net/issue/pypy-dev/",
                   class_="menu"),
            " ", id="menubar")

    def get_doclink(self, target):
        return relpath(self.targetpath.strpath,
                       self.project.docpath.join(target).strpath)
        

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
