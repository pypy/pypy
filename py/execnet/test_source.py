
from py.__impl__.execnet.source import Source

def test_source_str_function():
    x = Source("3")
    assert str(x) == "3" 

    x = Source("   3")
    assert str(x) == "3" 

    x = Source("""
        3
    """) 
    assert str(x) == "3" 

def test_source_indent_simple():
    source = Source("raise ValueError")
    source.putaround(
        "try:", 
      """
        except ValueError:
            x = 42
        else:
            x = 23""")
    assert str(source)=="""\
try:
    raise ValueError
except ValueError:
    x = 42
else:
    x = 23"""
  
def XXXtest_source_indent_simple():
    x = StrSource("x=3")
    assert not x.isindented()
    x.indent("try:", "except: pass")
    assert x.read() == "try:\n    x=3\nexcept: pass"

    #x.indent("try:", 
    #       """except:
