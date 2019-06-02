import sys
if sys.platform != 'win32':
    raise ImportError("The '_overlapped' module is only available on Windows")
    
def write_input():
    print("Write input")

def read_output():
    print("Read output")
