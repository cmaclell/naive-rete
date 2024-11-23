from py_rete.common import WME
from py_rete.common import V
from py_rete.network import ReteNetwork
from py_rete.conditions import Cond
from py_rete.conditions import Bind
from py_rete.conditions import AND
from py_rete.conditions import NOT
from py_rete.conditions import OR
from py_rete.conditions import Neg
from py_rete.conditions import Ncc
from py_rete.production import Production, compile_disjuncts, get_rete_conds
from py_rete.fact import Fact
import py_rete.fact  # So we can patch fact.gen_variable

from unittest.mock import sentinel, Mock
from pytest import mark, raises


def test_compile_disjuncts():
    r0 = compile_disjuncts(OR(sentinel.OR1, sentinel.OR2))
    assert r0 == (sentinel.OR1, sentinel.OR2)
    r1 = compile_disjuncts(AND(sentinel.AND1, sentinel.AND2))
    assert r1 == ((sentinel.AND1, sentinel.AND2),)
    r2 = compile_disjuncts(AND(sentinel.AND1, NOT(sentinel.NOT1)))
    assert r2 == ((sentinel.AND1, NOT(sentinel.NOT1,)),)
    r3 = compile_disjuncts(AND(sentinel.AND1, NOT(sentinel.NOT1, sentinel.NOT2)))
    assert r3 == ((sentinel.AND1, NOT(sentinel.NOT1, sentinel.NOT2)),)
    r4 = compile_disjuncts(sentinel.SIMPLE)
    assert r4 == (sentinel.SIMPLE,)
    r5 = compile_disjuncts(sentinel.SIMPLE, nest=False)
    assert r5 == sentinel.SIMPLE


def test_get_rete_conds(monkeypatch):
    it0 = [Cond(sentinel.ID0, sentinel.ATTR0, sentinel.VAL0)]
    rc0 = list(get_rete_conds(it0))
    assert rc0 == it0

    it1 = [NOT(Cond(sentinel.ID1, sentinel.ATTR1, sentinel.VAL1))]
    rc1 = list(get_rete_conds(it1))
    assert rc1 == [Neg(sentinel.ID1, sentinel.ATTR1, sentinel.VAL1)]

    it2 = [NOT(AND(Bind(sentinel.FUNC2, sentinel.TO2)))]
    rc2 = list(get_rete_conds(it2))
    assert rc2 == [Ncc(Bind(sentinel.FUNC2, sentinel.TO2))]

    it3 = [NOT(Bind(sentinel.FUNC3A, sentinel.TO3A), Bind(sentinel.FUNC3B, sentinel.TO3B))]
    rc3 = list(get_rete_conds(it3))
    assert rc3 == [Ncc(Bind(sentinel.FUNC3A, sentinel.TO3A), Bind(sentinel.FUNC3B, sentinel.TO3B))]

    monkeypatch.setattr(py_rete.fact, 'gen_variable', Mock(side_effect=["gv1", "gv2", "gv3", "gv4", "gv5", "gv6"]))
    with_id_fact = Fact(name=sentinel.VALUE6)
    with_id_fact.id = sentinel.ID
    it4 = [Fact(name=sentinel.VALUE4, subfact=Fact(name=sentinel.VALUE5), another=with_id_fact)]
    rc4 = list(get_rete_conds(it4))
    assert rc4 == [
        Cond("gv2", "name", sentinel.VALUE5),
        Cond("gv2", "__fact_type__", Fact),
        Cond(sentinel.ID, "name", sentinel.VALUE6),
        Cond(sentinel.ID, "__fact_type__", Fact),
        Cond("gv3", "name", sentinel.VALUE4),
        Cond("gv3", "subfact", "gv2"),
        Cond("gv3", "another", sentinel.ID),
        Cond("gv3", "__fact_type__", Fact),
    ]

def test_get_rete_conds_ncc_neg():
    it5 = [Ncc(Bind(sentinel.FUNC2, sentinel.TO2))]
    rc5 = list(get_rete_conds(it5))
    assert rc5 == []


def test_invalid_decoration_production():
    x = Production()
    with raises(AttributeError):
        x()
    with raises(ValueError):
        repr(x)

    # Legitimate use.
    def function(x):
        pass
    prod_func = Production()(function)
    assert prod_func._wrapped_args == {'x'}
    assert repr(prod_func) == "IF None THEN function(x)"


def test_var_keyword_decoration_production():
    @Production()
    def demo(positional, *, variable, **special_case):
        pass

    assert demo._wrapped_args == []


def test_call_production():
    @Production()
    def demo_1(x):
        return 2 * x + 1

    assert 9 == demo_1(4)

    @Production()
    def demo_kw(**kwargs):
        return 2 * kwargs['x'] + 1

    assert 9 == demo_kw(x=4)

    demo_1.id = "demo_1"
    demo_kw.id = "demo_kw"
    assert demo_1 == demo_1
    assert demo_1 != demo_kw


def test_production():

    class Block(Fact):
        pass

    @Production(Block(name=V('x'), clear=True))
    def is_clear(x):
        print(x)

    net = ReteNetwork()
    net.add_production(is_clear)


def test_root():
    # network is root, uses hash
    net = ReteNetwork()

    c0 = Cond('a', 'b', 'c')
    am0 = net.build_or_share_alpha_memory(c0)
    assert am0 is not None

    am1 = net.build_or_share_alpha_memory(c0)
    assert am0 == am1

    assert len(net.alpha_hash) == 1

    wme = WME('a', 'b', 'c')
    net.add_wme(wme)

    assert len(am0.items) == 1
