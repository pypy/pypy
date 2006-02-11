from pypy.rpython.lltypesystem import lltype


class Node(object):
    def setup(self):
        """ sets node.ref and calls database prepare_* methods """

    def write_implementation(self, codewriter):
        """ write function implementations. """ 

    def write_forward_declaration(self, codewriter):    #of arrays and structs
        """ write forward declarations for global data. """ 

    def write_global_array(self, codewriter):
        """ write out global array data.  """
        
    def write_global_struct(self, codewriter):
        """ write out global struct data.  """
