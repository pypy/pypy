import objspace
thisdir = os.getcwd()
syspath = sys.path
sys.path.insert(0,thisdir)
sys.path.append('..')


#######################################
# import the module you want to test
# import yourmodule
#######################################

os.chdir('..')
#import your_object_class
os.chdir(thisdir)

# End HACK
class TestYourObjectClass(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_test1(self):
        pass


if __name__ == '__main__':
    unittest.main()
