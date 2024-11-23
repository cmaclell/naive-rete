# -*- coding: utf-8 -*-
from py_rete.conditions import Cond
from py_rete.conditions import Ncc
from py_rete.conditions import ConditionalList
from py_rete.common import WME
from py_rete.common import Token
from py_rete.common import V
from py_rete.fact import Fact
from py_rete.network import ReteNetwork
from py_rete.production import Production
from py_rete.conditions import AND
from py_rete.conditions import Bind
from py_rete.conditions import OR
from py_rete.conditions import NOT
from py_rete.conditions import Filter
from py_rete.conditions import Neg
from py_rete.beta import BetaMemory
from py_rete.join_node import JoinNode
from py_rete.negative_node import NegativeNode
from py_rete.ncc_node import NccNode, NccPartnerNode

from unittest.mock import sentinel, Mock, call, MagicMock
from pytest import raises, mark


def test_readme_facts():

    f = Fact(a=1, b=2)
    assert f['a'] == 1

    f = Fact('a', 'b', 'c')
    assert f[0] == 'a'

    f = Fact('a', 'b', c=3, d=4)
    assert f[0] == 'a'
    assert f['c'] == 3


def test_readme_productions():

    @Production(Fact(color='red'))
    def alert_something_red():
        print("I found something red")

    @Production(AND(OR(Fact(color='red'),
                       Fact(color='blue')),
                    NOT(Fact(color='green'))))
    def alert_something_complex():
        print("I found something red or blue without any green present")

    @Production((Fact(color='red') | Fact(color='blue')) &
                ~Fact(color='green'))
    def alert_something_complex2():
        print("I found something red or blue without any green present")

    @Production(Fact(firstname='Chris', lastname=V('lastname')) &
                Fact(first='John', lastname=V('lastname')))
    def found_relatives(lastname):
        print("I found a pair of relatives with the lastname: "
              "{}".format(lastname))

    @Production(Fact(value=V('a')) &
                Fact(value=V('b')) &
                Filter(lambda a, b: a > b) &
                Fact(value=V('c')) &
                Filter(lambda b, c: b > c))
    def three_values(a, b, c):
        print("{} is greater than {} is greater than {}".format(a, b, c))


def test_readme_production_bind():

    @Production(V('name_fact') << Fact(name=V('name')))
    def found_name(name_fact):
        print("I found a name fact {}".format(name_fact))


def test_readme_production_nested_match():

    @Production(Fact(name=V('name'), against__scissors=1, against__paper=-1))
    def what_wins_to_scissors_and_losses_to_paper(name):
        print(name)


def test_readme_network():

    net = ReteNetwork()

    f1 = Fact(light_color="red")
    net.add_fact(f1)

    f1['light_color'] = "green"
    net.update_fact(f1)

    net.remove_fact(f1)

    f1 = Fact(light_color="red")

    @Production(V('fact') << Fact(light_color="red"))
    def make_green(net, fact):
        print('making green')
        fact['light_color'] = 'green'
        net.update_fact(fact)

    @Production(V('fact') << Fact(light_color="green"))
    def make_red(net, fact):
        print('making red')
        fact['light_color'] = 'red'
        net.update_fact(fact)

    light_net = ReteNetwork()
    light_net.add_fact(f1)
    light_net.add_production(make_green)
    light_net.add_production(make_red)
    light_net.update_fact(f1)

    # print(light_net)
    light_net.run(5)

    matches = list(light_net.matches)
    print(matches)
    new = list(light_net.new_matches)  # noqa E262
    matches[0].fire()


def test_token():
    tdummy = Token(None, None)
    t0 = Token(tdummy, WME('B1', 'on', 'B2'))

    assert tdummy.parent is None
    assert t0.parent == tdummy

    assert tdummy.children == [t0]
    assert t0.children == []

    # Is this the inherited implementation from ``object``?
    assert hash(t0) == hash(id(t0))


def test_token_delete_betamemory():
    amem_list = MagicMock()
    amem = Mock(successors=amem_list)
    jn = JoinNode(amem=amem, condition=Mock(vars=[]))
    bm = BetaMemory(items=[], children=[jn])
    # token_children_list = MagicMock(wraps=list())
    t = Token(parent=Mock(), wme=Mock(), node=bm)
    # t.children = token_children_list
    bm.items=[t]
    t.delete_token_and_descendents()

    # TODO: final assertions on list removals
    # t.children.__bool__.mock_calls == [call()]


def test_token_delete_negativenode():
    # A NegativeNode is *also* a BetaMemory and a JoinNode
    amem = Mock(successors=[])
    nn = NegativeNode(amem=amem, condition=Mock(vars=[]), items=[], children=[])
    t = Token(parent=Mock(), wme=Mock(), node=nn)
    jr = Mock(wme=Mock(negative_join_results=[]))
    jr.wme.negative_join_results = [jr]
    t.join_results = [jr]
    amem.successors = [nn]
    nn.items = [t]
    t.delete_token_and_descendents()

    # TODO: final assertions on list removals


def test_token_delete_nccnode():
    # An NCCNode is a BetaMemory
    partner = Mock()
    nccn = NccNode(partner, items=[])
    t = Token(parent=Mock(), wme=Mock(), node=nccn)
    t.node.items = [t]
    result_items = Mock(name="result_tok items", wme=Mock(tokens=[]), parent=Mock(children=[]))
    result_empty = Mock(name="result_tok empty", wme=None, parent=None)
    result_items.wme.tokens = [result_items]
    result_items.parent.children = [result_items]
    t.ncc_results = [result_empty, result_items]
    t.delete_token_and_descendents()

    # TODO: Final assertions on various list removals


def test_token_delete_nccpartnernode():
    nccpn = NccPartnerNode(ncc_node=None)
    owner = Mock(name="owner", binding=sentinel.BINDING, ncc_results=[])
    t = Token(parent=Mock(), wme=Mock(), node=nccpn)
    owner.ncc_results = [t]
    t.owner = owner
    t.delete_token_and_descendents()

    # TODO: Final assertions on various list removals


def test_condition_vars():
    c0 = Cond(V('x'), 'is', V('y'))
    assert len(c0.vars) == 2


def test_condition_contain():
    c0 = Cond(V('a'), V('b'), V('c'))
    assert c0.contain(V('a'))
    assert not c0.contain(V('d'))


def test_condition_test():
    c0 = Cond(V('x'), 'color', 'red')
    w0 = WME('B1', 'color', 'red')
    w1 = WME('B1', 'color', 'blue')
    assert c0.test(w0)
    assert not c0.test(w1)


def test_codition_hash():
    c0 = Cond(sentinel.IDENTIFIER, sentinel.ATTRIBUTE, sentinel.VALUE)
    assert hash(c0) == hash(('cond', sentinel.IDENTIFIER, sentinel.ATTRIBUTE, sentinel.VALUE))


def test_condtional_list():
    cl = ConditionalList(sentinel.C1, sentinel.C2)
    assert repr(cl) == "ConditionalList(sentinel.C1, sentinel.C2)"

    # Is this the inherited implementation from ``tuple``?
    assert hash(cl) == hash((ConditionalList.__name__, tuple(cl)))


def test_composable_cond():
    and_left = AND(sentinel.L1, sentinel.L2)
    and_right = AND(sentinel.R1, sentinel.R2)

    assert and_left & and_right == AND(sentinel.L1, sentinel.L2, sentinel.R1, sentinel.R2)
    assert OR(sentinel.L1) & and_right == AND(OR(sentinel.L1), sentinel.R1, sentinel.R2)
    assert and_left & OR(sentinel.R1) == AND(sentinel.L1, sentinel.L2, OR(sentinel.R1))

    or_left = OR(sentinel.L1, sentinel.L2)
    or_right = OR(sentinel.R1, sentinel.R2)

    assert or_left | or_right == OR(sentinel.L1, sentinel.L2, sentinel.R1, sentinel.R2)
    assert AND(sentinel.L1) | or_right == OR(AND(sentinel.L1), sentinel.R1, sentinel.R2)
    assert or_left | AND(sentinel.R1) == OR(sentinel.L1, sentinel.L2, AND(sentinel.R1))


def test_neg_cond():
    c0 = Neg(sentinel.IDENTIFIER, sentinel.ATTRIBUTE, sentinel.VALUE)
    assert repr(c0) == "-(sentinel.IDENTIFIER ^sentinel.ATTRIBUTE sentinel.VALUE)"
    assert hash(c0) == hash(('neg', sentinel.IDENTIFIER, sentinel.ATTRIBUTE, sentinel.VALUE))


def test_ncc():
    c0 = Cond(V('a'), V('b'), V('c'))
    c1 = Ncc(Cond(V('x'), 'color', 'red'))
    c2 = Ncc(c0, c1)
    assert c2.number_of_conditions == 2
    assert repr(c2) == "-Ncc((V(a) ^V(b) V(c)), -Ncc((V(x) ^color red),))"
    assert hash(c1) == hash(('ncc', tuple(c1)))


def test_filter():
    c0 = Filter(sentinel.FUNC)
    assert repr(c0) == "Filter(sentinel.FUNC)"
    assert hash(c0) == hash(('filter', sentinel.FUNC))


def test_bind():
    c0 = Bind(sentinel.FUNC, sentinel.TO)
    assert repr(c0) == "Bind(sentinel.FUNC, sentinel.TO)"
    assert hash(c0) == hash(('bind', sentinel.FUNC, sentinel.TO))


def test_wme_valueerror():
    with raises(ValueError):
        w = WME(V('identifier'), 'attribute', 'value')
    with raises(ValueError):
        w = WME('identifier', V('attribute'), 'value')
    with raises(ValueError):
        w = WME('identifier', 'attribute', V('value'))
    assert not (WME('a', 'b', 'c') == 'string')
    assert not (42 == WME('a', 'b', 'c'))


def test_add_remove_empty():
    net = ReteNetwork()

    @Production()
    def empty():
        pass

    net.add_production(empty)
    assert len(net.beta_root.children) == 1

    net.remove_production(empty)
    assert len(net.beta_root.children) == 0


def test_add_remove_bind():
    net = ReteNetwork()

    @Production(Bind(lambda: 5, V('x')))
    def bind(x):
        return x

    net.add_production(bind)
    assert len(net.beta_root.children) == 1
    assert list(net.matches)[0].fire() == 5

    net.remove_production(bind)
    assert len(net.beta_root.children) == 0


def test_add_remove_filter():
    net = ReteNetwork()

    @Production(Filter(lambda: True))
    def filter_fun():
        pass

    net.add_production(filter_fun)
    assert len(net.beta_root.children) == 1

    net.remove_production(filter_fun)
    assert len(net.beta_root.children) == 0


def test_add_remove_not():
    net = ReteNetwork()

    @Production(~Cond('a', 'on', 'b'))
    def not_fun():
        pass

    net.add_production(not_fun)
    assert len(net.beta_root.children) == 1
    assert len(list(net.matches)) == 1

    wme = WME('a', 'on', 'b')
    net.add_wme(wme)
    assert len(list(net.matches)) == 0

    net.remove_wme(wme)
    assert len(list(net.matches)) == 1

    net.remove_production(not_fun)
    assert len(net.beta_root.children) == 0


def test_add_remove_join():
    net = ReteNetwork()

    @Production(Cond('a', 'on', 'b'))
    def join_fun():
        pass

    net.add_production(join_fun)
    assert len(net.beta_root.children) == 1
    assert len(list(net.matches)) == 0

    wme = WME('a', 'on', 'b')
    net.add_wme(wme)
    assert len(list(net.matches)) == 1

    wme = WME('a', 'on', 'b')
    net.remove_wme(wme)
    assert len(list(net.matches)) == 0

    net.remove_production(join_fun)
    assert len(net.beta_root.children) == 0


def test_add_remove_ncc():
    net = ReteNetwork()

    @Production(~Fact(first="hello", second="world"))
    def ncc_fun():
        pass

    net.add_production(ncc_fun)
    assert len(net.beta_root.children) == 2
    assert len(list(net.matches)) == 1

    wme = WME('a', 'on', 'b')
    net.add_wme(wme)
    f = Fact(first='hello', second='world')
    net.add_fact(f)
    assert len(list(net.matches)) == 0

    net.remove_fact(f)
    assert len(list(net.matches)) == 1

    net.remove_production(ncc_fun)
    assert len(net.beta_root.children) == 0
