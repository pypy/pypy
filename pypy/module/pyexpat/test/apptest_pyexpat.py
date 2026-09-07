# spaceconfig = {"usemodules": ["pyexpat"]}
import pyexpat
import pytest

def test_error():
    info = pytest.raises(TypeError, pyexpat.ParserCreate, namespace_separator=1)
    assert "ParserCreate() argument 'namespace_separator' must be str or None, not int" in str(info.value)
    info = pytest.raises(TypeError, pyexpat.ParserCreate, encoding=1)
    assert "ParserCreate() argument 'encoding' must be str or None, not int" in str(info.value)

def test_set_activation_threshold():
    parser = pyexpat.ParserCreate()
    # Raises on error
    parser.SetAllocTrackerActivationThreshold(1000)

def test_set_maximum_amplification():
    parser = pyexpat.ParserCreate()
    # Raises on error
    parser.SetAllocTrackerMaximumAmplification(3.0)

def _billion_laughs_payload(nrows, ncols):
    body = '\n'.join(
        '<!ENTITY row%d "%s">' % (i + 1, ("&row%d;" % i) * ncols)
        for i in range(nrows))
    return ('<?xml version="1.0"?>\n<!DOCTYPE doc [\n<!ENTITY row0 ".">\n'
            '<!ELEMENT doc (#PCDATA)>\n%s\n]>\n<doc>&row%d;</doc>'
            % (body, nrows))

def test_billion_laughs_setters():
    parser = pyexpat.ParserCreate()
    assert parser.SetBillionLaughsAttackProtectionActivationThreshold(0) is None
    assert parser.SetBillionLaughsAttackProtectionMaximumAmplification(1.0) is None
    assert parser.SetBillionLaughsAttackProtectionMaximumAmplification(float('inf')) is None
    pytest.raises(TypeError, parser.SetBillionLaughsAttackProtectionActivationThreshold, 1.0)
    pytest.raises(ValueError, parser.SetBillionLaughsAttackProtectionActivationThreshold, -5)
    pytest.raises(OverflowError, parser.SetBillionLaughsAttackProtectionActivationThreshold, 2**64)
    pytest.raises(TypeError, parser.SetBillionLaughsAttackProtectionMaximumAmplification, None)
    pytest.raises(TypeError, parser.SetBillionLaughsAttackProtectionMaximumAmplification, 'abc')
    for bad in (float('nan'), 0.99):
        info = pytest.raises(pyexpat.ExpatError,
            parser.SetBillionLaughsAttackProtectionMaximumAmplification, bad)
        assert "'max_factor' must be at least 1.0" in str(info.value)
    sub = parser.ExternalEntityParserCreate(None)
    info = pytest.raises(pyexpat.ExpatError,
        sub.SetBillionLaughsAttackProtectionActivationThreshold, 12345)
    assert "parser must be a root parser" in str(info.value)
    info = pytest.raises(pyexpat.ExpatError,
        sub.SetBillionLaughsAttackProtectionMaximumAmplification, 123.45)
    assert "parser must be a root parser" in str(info.value)

def test_billion_laughs_rejected():
    parser = pyexpat.ParserCreate()
    parser.SetBillionLaughsAttackProtectionActivationThreshold(0)
    parser.SetBillionLaughsAttackProtectionMaximumAmplification(1.0)
    info = pytest.raises(pyexpat.ExpatError, parser.Parse,
                         _billion_laughs_payload(nrows=2, ncols=1), True)
    assert "limit on input amplification factor" in str(info.value)

    parser = pyexpat.ParserCreate()
    parser.SetBillionLaughsAttackProtectionActivationThreshold(0)
    parser.SetBillionLaughsAttackProtectionMaximumAmplification(1e4)
    assert parser.Parse(_billion_laughs_payload(nrows=2, ncols=1), True)

