#pythonexecutables = ('python2.2', 'python2.3',) 
#pythonexecutable = 'python2.2' 

def setup_module(extpy):
    mod = extpy.resolve() 
    mod.module = 23
    directory = pypath.root.dirpath()
    
    
    
    
# standard options (modified from cmdline) 
verbose = 0 
nocapture = False 
collectonly = False 
exitfirstproblem = False 
fulltrace = False 
showlocals = False
nomagic = False 
