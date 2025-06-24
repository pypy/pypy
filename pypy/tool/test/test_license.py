import py, datetime

def test_license():
    lic = (py.path.local(__file__).dirpath().dirpath()
                                  .dirpath().dirpath().join('LICENSE'))
    text = lic.read()
    COPYRIGHT_HOLDERS="PyPy Copyright holders 2003"
    assert COPYRIGHT_HOLDERS in text
