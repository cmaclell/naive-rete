# from py_rete.production import Bind
from py_rete.conditions import Cond
from py_rete.conditions import AND
from py_rete.production import Production
from py_rete.common import WME
from py_rete.common import V
from py_rete.fact import Fact
from py_rete.conditions import Bind
from py_rete.conditions import Filter
from py_rete.network import ReteNetwork
import py_rete.network
from py_rete.negative_node import NegativeNode
from py_rete.pnode import PNode, Production
from py_rete.ncc_node import NccNode, NccPartnerNode
from py_rete.filter_node import FilterNode
from py_rete.bind_node import BindNode
from py_rete.beta import BetaMemory

from unittest.mock import MagicMock, Mock, sentinel, call
from pytest import mark, raises


def test_network_run(monkeypatch):
    match = Mock(name="Match")
    n = ReteNetwork()
    p = property(Mock(side_effect=[[match], []]))
    monkeypatch.setattr(ReteNetwork, 'matches', p)
    n.run()
    assert match.fire.mock_calls == [call()]


def test_network_repr():
    n = ReteNetwork()
    p = Mock(name="Production", id=sentinel.PROD_ID)
    n.productions = set([p])

    dup_fact = {
        sentinel.SIMPLE: sentinel.VALUE,
        sentinel.SUBFACT: Fact(name="subfact")
    }
    dup_fact[sentinel.SUBFACT].id = sentinel.SUBFACT_ID
    f = Mock(name="Fact", id=sentinel.ID, duplicate=Mock(return_value=dup_fact))
    n.facts = {
        f.id: f
    }
    wme = Mock(name="Working Memory")
    n.working_memory = set([wme])
    text = repr(n)

    assert list(dup_fact.items()) == [(sentinel.SIMPLE, sentinel.VALUE), (sentinel.SUBFACT, sentinel.SUBFACT_ID)]
    assert "sentinel.PROD_ID: <Mock name='Production'" in text
    assert "sentinel.ID: {sentinel.SIMPLE: sentinel.VALUE, sentinel.SUBFACT: sentinel.SUBFACT_ID}" in text
    assert "<Mock name='Working Memory'" in text


def test_network_num_nodes():
    n = ReteNetwork()

    n.beta_root = Mock(children=[])
    assert n.num_nodes() == 1

    n.beta_root = Mock(children=[Mock(children=[])])
    assert n.num_nodes() == 2


def test_network_add_remove_get_fact():
    n = ReteNetwork()
    subfact_id = Fact(name="sub_id")
    n.add_fact(subfact_id)  # Assigns ID.
    subfact = Fact(name="sub")
    top_fact = Fact(name="top", subfact=subfact, subfact_id=subfact_id)
    n.add_fact(top_fact)
    # EQ tests require comparing objects with the id's updated.
    assert n.facts == {'f-0': subfact_id, 'f-1': subfact, 'f-2': top_fact}

    with raises(ValueError):
        n.add_fact(top_fact)
    with raises(ValueError):
        n.remove_fact(Fact(not_in_evidence=True))

    assert n.get_fact_by_id('f-0') == subfact_id


def test_network_get_new_match():
    n = ReteNetwork()
    old = Mock(name="PNode", new=False)
    n.pnodes = [old]
    assert n.get_new_match() is None


def test_network_add_production():
    n = ReteNetwork()
    n.productions = {sentinel.EXISTING: Mock}
    with raises(ValueError):
        n.add_production(Mock(id=sentinel.EXISTING))
    with raises(ValueError):
        n.remove_production(Mock(id=None))


def test_network_add_remove_wme():
    n = ReteNetwork()
    wme_0 = Mock(identifier="#*#", attribute=sentinel.ATTR, value=sentinel.VALUE)
    with raises(ValueError):
        n.add_wme(wme_0)

    jr = Mock(owner=Mock(node=None, join_results=[]))
    jr.owner.join_results.append(jr)

    wme_1 = Mock(amems=[], tokens=[], negative_join_results=[jr])
    n.working_memory = set([wme_1])
    n.remove_wme(wme_1)


def test_network_alpha_mem():
    n = ReteNetwork()
    with raises(ValueError):
        cond_0 = Mock(identifier="#*#", attribute=sentinel.ATTR, value=sentinel.VALUE)
        n.build_or_share_alpha_memory(cond_0)

    cond_1 = Mock(
        identifier=sentinel.ID,
        attribute=V(sentinel.ATTR_V),
        value=sentinel.VALUE
    )
    key = (sentinel.ID, "#*#", sentinel.VALUE)
    n.alpha_hash = {key: sentinel.COND}
    c = n.build_or_share_alpha_memory(cond_1)
    assert c == sentinel.COND
    # assert n.alpha_hash == {key: sentinel.COND}


def test_network_negative_node():
    n = ReteNetwork()
    amem = Mock(successors=[], reference_count=0)
    other = Mock(name="ReteNode", items=[], amem=sentinel.AMEM, condition=sentinel.COND)
    condition = Mock(name="condition", vars=[("name", sentinel.VALUE)])
    negative = NegativeNode(items=[], amem=amem, condition=condition)
    parent = Mock(name="Parent ReteNode", children=[other, negative])
    new = n.build_or_share_negative_node(parent, amem, condition)
    assert new == negative


def test_network_beta_memory():
    n = ReteNetwork()
    other = Mock(name="not BetaMemory")
    beta = BetaMemory(items=[])
    parent = Mock(name="Parent ReteNode", children=[other, beta])
    new = n.build_or_share_beta_memory(parent)
    assert new == beta


def test_network_pnode():
    n = ReteNetwork()
    other = Mock(name="ReteNode")
    pnode = PNode(production=sentinel.PROD, items=[])
    parent = Mock(name="Parent ReteNode", children=[other, pnode])
    new = n.build_or_share_p(parent, sentinel.PROD)
    assert new == pnode


def test_network_ncc_node(monkeypatch):
    monkeypatch.setattr(ReteNetwork, 'build_or_share_network_for_conditions', Mock(return_value=sentinel.BOTTOM))
    n = ReteNetwork()
    other = Mock(name="ReteNode")
    nccnode = NccNode(partner=Mock(name="NccPartnerNode", parent=None), items=[])
    nccnode.partner.parent = sentinel.BOTTOM
    parent = Mock(name="Parent JoinNode", children=[other, nccnode])
    new = n.build_or_share_ncc_nodes(parent, sentinel.CANDIDATE_NCC, earlier_conds=[])
    assert new == nccnode


def test_network_filter_node():
    n = ReteNetwork()
    other = Mock(name="ReteNode")
    filternode = FilterNode(children=[], parent=Mock(), func=sentinel.FUNC, rete=sentinel.RETE)
    parent = Mock(name="Parent ReteNode", children=[other, filternode])
    new = n.build_or_share_filter_node(parent, Mock(func=sentinel.FUNC))
    assert new == filternode


def test_network_bind_node():
    n = ReteNetwork()
    other = Mock(name="ReteNode")
    bindnode = BindNode(children=[], parent=Mock(), func=sentinel.FUNC, to=sentinel.TO, rete=sentinel.RETE)
    parent = Mock(name="Parent ReteNode", children=[other, bindnode])
    new = n.build_or_share_bind_node(parent, Mock(func=sentinel.FUNC, to=sentinel.TO))
    assert new == bindnode


def test_network_delete_unused():
    n = ReteNetwork()
    node = NccPartnerNode()
    def cleanup():
        # Side-effect of a complex bit of processing in Token.
        node.new_result_buffer = []
    token = Mock(network=n, delete_token_and_descendents=Mock(side_effect=cleanup))
    node.new_result_buffer = [token]
    n.delete_node_and_any_unused_ancestors(node)
    assert token.delete_token_and_descendents.mock_calls == [call()]


def test_network_update_beta_memory():
    n = ReteNetwork()
    parent = BetaMemory(items=[sentinel.TOKEN])
    new_node = Mock(left_activation=Mock())
    new_node.parent = parent
    n.update_new_node_with_matches_from_above(new_node)
    assert new_node.left_activation.mock_calls == [call(token=sentinel.TOKEN)]


def test_network_update_negative_node():
    n = ReteNetwork()
    token_0 = Mock(binding=sentinel.BINDING, join_results=True)
    token_1 = Mock(binding=sentinel.BINDING, join_results=False)
    parent = NegativeNode(items=[token_0, token_1], amem=sentinel.AMEM, condition=Mock(vars=[(sentinel.NAME, sentinel.VALUE)]))
    new_node = Mock(left_activation=Mock())
    new_node.parent = parent
    n.update_new_node_with_matches_from_above(new_node)
    assert new_node.left_activation.mock_calls == [call(token_1, None, sentinel.BINDING)]


def test_network_update_ncc_node():
    n = ReteNetwork()
    token_0 = Mock(binding=sentinel.BINDING, ncc_results=True)
    token_1 = Mock(binding=sentinel.BINDING, ncc_results=False)
    parent = NccNode(items=[token_0, token_1], partner=sentinel.PARTNER)
    new_node = Mock(left_activation=Mock())
    new_node.parent = parent
    n.update_new_node_with_matches_from_above(new_node)


def init_network():
    net = ReteNetwork()
    c0 = Cond(V('x'), 'on', V('y'))
    c1 = Cond(V('y'), 'left-of', V('z'))
    c2 = Cond(V('z'), 'color', 'red')

    @Production(AND(c0, c1, c2))
    def test():
        pass

    net.add_production(test)

    return net


def test_fire():
    fire_counting()


def add_to_depth():
    net = ReteNetwork()

    @Production(Fact(number=V('x'), depth=V('xd')) &
                Fact(number=V('y'), depth=V('yd')) &
                Filter(lambda xd, yd: xd+yd < 1))
    def add(net, x, y, xd, yd):
        f = Fact(number=x+y, depth=xd+yd+1)
        net.add_fact(f)

    net.add_fact(Fact(name="1", number=1, depth=0))
    net.add_fact(Fact(name="2", number=2, depth=0))
    # net.add_fact(Fact(name="3", number=3, depth=0))
    # net.add_fact(Fact(name="5", number=5, depth=0))
    # net.add_fact(Fact(name="7", number=7, depth=0))

    net.add_production(add)

    while len(list(net.new_matches)) > 0:
        # print(len(list(net.new_matches)))
        m = net.get_new_match()
        m.fire()


def fire_counting():
    net = ReteNetwork()

    @Production(Fact(number=V('x')) &
                ~Fact(before=V('x')) &
                Bind(lambda x: str(int(x) + 1), V('y')))
    def add1(net, x, y):
        f = Fact(number=y, before=x)
        net.add_fact(f)

    net.add_production(add1)
    assert len(net.wmes) == 0

    net.add_fact(Fact(number='1'))
    assert len(net.wmes) == 2

    print(net)

    for i in range(5):
        net.run(1)
        assert len(net.wmes) == (3*(i+1))+2


def test_fire_counting(benchmark):
    benchmark(fire_counting)


def add_wmes():
    net = init_network()
    wmes = [
        WME('B1', 'on', 'B2'),
        WME('B1', 'on', 'B3'),
        WME('B1', 'color', 'red'),
        WME('B2', 'on', 'table'),
        WME('B2', 'left-of', 'B3'),
        WME('B2', 'color', 'blue'),
        WME('B3', 'left-of', 'B4'),
        WME('B3', 'on', 'table'),
        WME('B3', 'color', 'red')
    ]
    for wme in wmes:
        net.add_wme(wme)

    return net


def test_add_to_depth(benchmark):
    benchmark(add_to_depth)


def test_init_network(benchmark):
    benchmark(init_network)


def test_add_wmes(benchmark):
    benchmark(add_wmes)


def test_activation():
    net = ReteNetwork()
    c0 = Cond(V('x'), 'on', V('y'))
    c1 = Cond(V('y'), 'color', 'red')

    @Production(AND(c0, c1))
    def p():
        pass

    net.add_production(p)

    activations = [p for p in net.matches]
    assert len(activations) == 0

    wmes = [WME('B1', 'on', 'B2'),
            WME('B2', 'color', 'red')]

    for wme in wmes:
        net.add_wme(wme)

    print(net.working_memory)
    print(net)

    activations = [p for p in net.matches]
    assert len(activations) == 1

    net.remove_wme(wmes[0])

    activations = [p for p in net.matches]
    assert len(activations) == 0


def test_facts():
    net = ReteNetwork()

    wmes = [e for e in net.wmes]
    assert len(wmes) == 0

    wmes = set([WME('B1', 'on', 'B2'), WME('B2', 'color', 'red')])

    for wme in wmes:
        net.add_wme(wme)

    stored_wmes = set([e for e in net.wmes])
    assert len(stored_wmes) == 2
    assert len(wmes.union(stored_wmes)) == 2

    wmes = list(wmes)
    net.remove_wme(wmes[0])
    stored_wmes = [e for e in net.wmes]
    assert len(stored_wmes) == 1
    assert stored_wmes == wmes[1:]


def test_updating_pmatch():

    net = ReteNetwork()

    f1 = Fact(name="hello")
    f2 = Fact(name="world")
    net.add_fact(f1)
    net.add_fact(f2)

    @Production(AND(Fact(name="hello"),
                    Fact(name="world")))
    def beep():
        pass

    net.add_production(beep)

    assert len(list(net.matches)) == 1

    f1['name'] = "beep"
    net.update_fact(f1)

    assert(len(list(net.matches))) == 0


def test_rule_with_star():

    # need to make sure that values are not equality to the wildcard matchers
    # now we check for '#*#' as the matcher instead of '*'. This decreases the
    # likelihood of collision with string with star.

    net = ReteNetwork()

    fo1 = Fact(id='initial_operator', value='*', contentEditable=False)
    net.add_fact(fo1)

    @Production(AND(
        Fact(id='initial_operator', value='*', contentEditable=False),
        ))
    def beep():
        pass

    net.add_production(beep)

    assert len(list(net.matches)) == 1

    fo1['value'] = '+'
    net.update_fact(fo1)

    assert len(list(net.matches)) == 0


if __name__ == "__main__":
    add_to_depth()
