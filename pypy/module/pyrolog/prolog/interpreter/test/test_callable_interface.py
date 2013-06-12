from prolog.interpreter.parsing import parse_file, TermBuilder
from prolog.interpreter.term import Atom, Number, Term, Callable, \
        specialized_term_classes, NumberedVar, MutableCallable
from prolog.interpreter.test.tool import parse
from prolog.interpreter.heap import Heap
import py

def parse(inp):
    t = parse_file(inp)
    builder = TermBuilder()
    return builder.build(t)
    
atom = parse('a.')[0]
term = parse('t(a, b, c, d, f).')[0]
def test_atom_get_signature():
    r = atom.get_prolog_signature() 
    r.name() == '/'
    assert r.argument_at(0).signature().string() == 'a/0'
    assert r.argument_at(1).num == 0

def test_atom_get_arguments():
    assert atom.arguments() == []
    
def test_atom_arguemtn_count():
    assert atom.argument_count() == 0
    
def test_atom_get_argument_at():
    assert py.test.raises(IndexError, 'atom.argument_at(0)')
    
def test_term_get_signature():
    r = term.get_prolog_signature()
    print r
    assert r.name() == '/'
    r.name() == '/'
    assert r.argument_at(0).signature().string() == 't/0'
    assert r.argument_at(1).num == 5
    
def test_term_get_arguments():
    t = term.arguments()
    assert isinstance(t, list)
    assert len(t) == 5
    
def test_term_get_argument_out_of_range():
    py.test.raises(IndexError, 'term.argument_at(5)')

def test_term_get_argument_in_range():
    t =  term.argument_at(2)
    assert t.name() == 'c'
    
def test_term_argument_count():
    assert term.argument_count() == 5
    
def test_callable_name():
    c = Callable()
    py.test.raises(NotImplementedError, 'c.name()')
    
def test_callable_signature():
    c = Callable()
    py.test.raises(NotImplementedError, 'c.signature()')
    
def test_atom_name():
    assert atom.name() == 'a'

def test_atom_signature():
    assert atom.signature().string() == 'a/0'
    
def test_term_name():
    assert term.name() == 't'
    
def test_term_signature():
    assert term.signature().string() == 't/5'
    
def test_callable_factory_for_atom():
    r = Callable.build('foo')
    assert isinstance(r, Atom)
    assert r.signature().string() == 'foo/0'

def test_callable_factory_for_term_with_empty_args():
    r = Callable.build('bar', [])
    assert isinstance(r, Atom)
    assert r.signature().string() == 'bar/0'

def test_callable_factory_for_term():
    r = Callable.build('foo', [1, 2])
    assert isinstance(r, Callable)
    assert r.signature().string() == 'foo/2'
    
def test_callable_factory_for_cons():
    r = Callable.build('.', [1, Callable.build('[]')])
    assert isinstance(r, specialized_term_classes['.', 2])
    assert r.signature().string() == './2'
    assert r.name() == '.'
    assert r.argument_count() == 2
    assert r.arguments() == [1, Callable.build('[]')]
    assert r.argument_at(0) == 1
    assert r.argument_at(1) == Callable.build('[]')

def test_callable_mutable():
    for name in [".", "f"]:
        t = Callable.build(name, [NumberedVar(0), NumberedVar(1)])
        res = t.copy_standardize_apart(Heap(), [None, None])
        assert isinstance(res, MutableCallable)
        res.set_argument_at(0, 1)
        assert res.argument_at(0) == 1
        res.set_argument_at(1, 7)
        assert res.argument_at(0) == 1
        assert res.argument_at(1) == 7

