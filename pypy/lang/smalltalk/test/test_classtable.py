from pypy.lang.smalltalk.classtable import classtable
import pypy.lang.smalltalk.classtable as ct

def inherits_from(m_cls, m_superclass):
    m_p = m_cls
    while m_p and m_p != m_superclass:
        m_p = m_p.m_superclass
    return m_p == m_superclass

def test_every_class_is_an_instance_of_a_metaclass():
    for (nm, m_cls) in classtable.items():
        assert (m_cls.m_metaclass is ct.m_Metaclass or
                m_cls.m_metaclass.m_metaclass is ct.m_Metaclass)
        
def test_every_metaclass_inherits_from_class_and_behavior():
    for (nm, m_cls) in classtable.items():
        if m_cls.m_metaclass is ct.m_Metaclass:
            assert inherits_from(m_cls, ct.m_Class)
    assert inherits_from(ct.m_Class, ct.m_Behavior)

def test_metaclass_of_metaclass_is_an_instance_of_metaclass():
    assert ct.m_Metaclass.m_metaclass.m_metaclass is ct.m_Metaclass
