from py_rete.fact import Fact
from py_rete.network import ReteNetwork
from py_rete.conditions import Cond
from py_rete.common import V

from unittest.mock import sentinel
from pytest import raises


class SubFact(Fact):
    pass


def test_invalid_fact():
    with raises(ValueError):
        f0 = Fact(sentinel.POSITIONAL, name=sentinel.NAMED, __fact_type__="invalid")
    with raises(ValueError):
        "hello" << Fact(sentinel.POS0, sentinel.POS1)
    with raises(ValueError):
        f2 = Fact(sentinel.POS0, sentinel.POS1)
        wmes = list(f2.wmes)
    with raises(ValueError):
        f3 = Fact(V(sentinel.NAME), sentinel.POS1)
        f3.id = sentinel.ID
        wmes = list(f3.wmes)


def test_cond_list():
    f0 = Fact(sentinel.POS0, sentinel.POS1, name=sentinel.VALUE)
    f0.id = sentinel.ID
    assert list(f0.conds) == [
        Cond(sentinel.ID, 0, sentinel.POS0),
        Cond(sentinel.ID, 1, sentinel.POS1),
        Cond(sentinel.ID, "name", sentinel.VALUE),
        Cond(sentinel.ID, "__fact_type__", Fact)
    ]


def test_fact():

    f3 = Fact(1, 2, name="test")
    assert f3[0] == 1
    assert f3[1] == 2
    assert f3['name'] == 'test'

    f4 = Fact(name="John")
    assert f4['name'] == 'John'
    assert hash(f4) == hash(f"Fact-{f4.id}")

    f5 = Fact(sentinel.POSITIONAL)
    f5.gen_var = V(sentinel.V)
    f5.bound = sentinel.BOUND
    assert repr(f5) == "V(sentinel.V) << Fact(0=sentinel.POSITIONAL)"

    f3_eq = Fact(1, 2, name="test")
    assert f3 is not f3_eq, "Confirm f3 and fe_eq are distinct"
    assert f3 == f3_eq

    f3_ne = Fact(3, 4, name="not test")
    assert f3 is not f3_ne, "Confirm f3 and fe_ne are distinct"
    assert not (f3 == f3_ne)
    assert not (f3_ne == f3)  # Slightly different key comparisons.
    assert f3 == f3
    assert not ("this" == f3)  # Technically, a test of str()
    assert not (f3 == "that")
    assert not(f3 != f3), "Seems silly by __ne__ might have an issue."

    f3_b = Fact(1, 2, 3, name="test", extra="no match")
    assert not (f3_b == f3)
    assert not (f3 == f3_b)


def test_adding_removing_facts():
    net = ReteNetwork()
    f = Fact()

    net.add_fact(f)
    assert f.id is not None

    assert len(net.working_memory) > 0

    net.remove_fact(f)
    assert f.id is None

    assert len(net.working_memory) == 0
