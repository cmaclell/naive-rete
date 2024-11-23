from py_rete.production import Production
from py_rete.conditions import AND
from py_rete.conditions import Cond
from py_rete.conditions import Neg
from py_rete.conditions import Ncc
from py_rete.conditions import Bind
from py_rete.conditions import Filter
from py_rete.fact import Fact
from py_rete.common import WME
from py_rete.common import Token
from py_rete.common import V
from py_rete.network import ReteNetwork
from py_rete.bind_node import BindNode
from py_rete.join_node import JoinNode
from py_rete.negative_node import NegativeNode
from py_rete.ncc_node import NccNode, NccPartnerNode
from py_rete.pnode import PNode

import py_rete.ncc_node

import pytest
from unittest.mock import Mock, MagicMock, call, sentinel

@pytest.mark.parametrize("func_result,expected_calls",
    [
        (sentinel.OLD_VALUE,
            [call(sentinel.TOKEN, sentinel.WME, {V('self'): sentinel.SELF, sentinel.TO: sentinel.OLD_VALUE})]),
        (sentinel.NEW_VALUE,
            [])
    ]
)
def test_bind_node_stubs(func_result, expected_calls):
    func = Mock(name='func', return_value=func_result)
    parent = Mock(name='parent')
    network = MagicMock(name='rete', __in__=False)
    child = Mock(name='child')

    bn = BindNode([child], parent, func, sentinel.TO, network)
    bn.left_activation(sentinel.TOKEN, sentinel.WME, {V('self'): sentinel.SELF, sentinel.TO: sentinel.OLD_VALUE})
    assert func.mock_calls == [
        call(self=sentinel.SELF)
    ]
    assert child.left_activation.mock_calls == expected_calls


def test_join_node_stubs():
    """JoinNode lines 95, 99-100. ancestor and ancestor.right_unlinked; ValueError on index()"""
    ancestor_1 = Mock(right_unlinked=False)
    ancestor_0 = Mock(right_unlinked=True, nearest_ancestor_with_same_amem=ancestor_1)
    parent = Mock(name='parent', find_nearest_ancestor_with_same_amem=Mock(return_value=ancestor_0))
    amem = Mock(name='AlphaMemory', successors=[sentinel.PREVIOUS_NODE])
    condition = Mock(name='Cond', vars=[('name', sentinel.VALUE)])
    node = JoinNode(children=[], parent=parent, amem=amem, condition=condition)
    node.update_nearest_ancestor_with_same_amem()

    node.relink_to_alpha_memory()

    assert amem.successors == [node, sentinel.PREVIOUS_NODE]

def test_negative_node_stubs():
    ancestor_1 = Mock(name='ancestor_1', right_unlinked=False)
    ancestor_0 = Mock(name='ancestor_0', right_unlinked=True, find_nearest_ancestor_with_same_amem=Mock(return_value=ancestor_1))
    parent = Mock(name='parent', find_nearest_ancestor_with_same_amem=Mock(return_value=ancestor_0))
    amem = Mock(name='AlphaMemory', successors=[sentinel.PREVIOUS_NODE])
    condition = Mock(name='Cond', vars=[('name', sentinel.VALUE)])
    node = NegativeNode(children=[], parent=parent, amem=amem, condition=condition)

    nearest = node.find_nearest_ancestor_with_same_amem(amem)
    assert nearest == node

    node.relink_to_alpha_memory()
    assert amem.successors == [node, sentinel.PREVIOUS_NODE]
    assert node.right_unlinked

def test_ncc_node_stubs(monkeypatch):
    # See https://docs.python.org/3/library/unittest.mock.html#attaching-mocks-as-attributes.

    ancestor_0 = sentinel.ANCESTOR_0
    result = Mock(name="result")
    parent = Mock(
        find_nearest_ancestor_with_same_amem=Mock(return_value=ancestor_0),
    )

    partner = Mock(new_result_buffer = [result])
    partner.parent = parent
    node = NccNode(partner=partner)
    assert node.partner == partner
    assert node.partner.parent == parent

    nearest = node.find_nearest_ancestor_with_same_amem(sentinel.AMEM)
    assert nearest == ancestor_0

    new_token = Mock()
    monkeypatch.setattr(py_rete.ncc_node, 'Token', Mock(return_value=new_token))

    node.left_activation(sentinel.PARENT, Mock(), {"self", Mock()})
    assert result.owner == new_token

def test_ncc_partner_node_stubs(monkeypatch):
    ncc_node = Mock(items=[])
    node = NccPartnerNode(sentinel.PARENT, ncc_node)
    new_token = sentinel.NEW_TOKEN
    monkeypatch.setattr(py_rete.ncc_node, 'Token', Mock(return_value=new_token))

    node.left_activation(sentinel.TOKEN, sentinel.WME, {"self", sentinel.NODE})
    assert len(node.new_result_buffer) == 1
    result = node.new_result_buffer[0]
    assert result == sentinel.NEW_TOKEN

def test_pnode_pop_new_token_stubs():
    production = Mock(name="Production")
    token = Mock(name="Token", children=[])
    wme = Mock(name="WME", tokens=[])
    binding = sentinel.BINDING

    node = PNode(production)
    node.left_activation(token, wme, binding)
    assert node.new
    assert node.items

    new = node.pop_new_token()
    assert new.parent == token
    assert new.wme == wme
    assert new.binding == sentinel.BINDING

    assert node.pop_new_token() is None

def test_pnode_new_activations_stubs():
    production = Mock(name="Production")
    token = Mock(name="Token", children=[])
    wme = Mock(name="WME", tokens=[])
    binding = sentinel.BINDING

    node = PNode(production)
    node.left_activation(token, wme, binding)
    assert node.new
    assert node.items

    activations = list(node.new_activations())
    assert len(activations) == 1
    new = activations[0]
    assert new.parent == token
    assert new.wme == wme
    assert new.binding == sentinel.BINDING


def test_network_case0():
    net = ReteNetwork()
    c0 = Cond('x', 'id', '1')
    c1 = Cond('x', 'kind', '8')

    @Production(AND(c0, c1))
    def p0():
        pass

    net.add_production(p0)

    w0 = WME('x', 'id', '1')
    w1 = WME('x', 'kind', '8')

    net.add_wme(w0)
    assert len(list(p0.activations)) == 0

    net.remove_wme(w0)
    net.add_wme(w1)
    assert len(list(p0.activations)) == 0

    net.add_wme(w0)
    net.add_wme(w1)
    assert len(list(p0.activations)) > 0


def test_bind_first():
    net = ReteNetwork()

    @Production(Bind(lambda: 1+1, V('x')))
    def test(x):
        pass

    net.add_production(test)

    assert len(list(net.matches)) == 1


def test_filter_first():
    net = ReteNetwork()

    @Production(Filter(lambda: True))
    def test():
        pass

    net.add_production(test)

    assert len(list(net.matches)) == 1


def test_filter_first2():
    net = ReteNetwork()
    net.add_fact(Fact())

    @Production(Filter(lambda: True) & Fact())
    def test():
        pass

    net.add_production(test)

    assert len(list(net.matches)) == 1


def test_filter_second():
    net = ReteNetwork()
    net.add_fact(Fact())

    @Production(Fact() & Filter(lambda: True) & Fact())
    def test():
        pass

    net.add_production(test)

    assert len(list(net.matches)) == 1


def test_empty_prod():
    net = ReteNetwork()

    @Production()
    def test():
        pass

    net.add_production(test)

    len(list(net.matches)) == 1


def test_network_case1():
    # setup
    net = ReteNetwork()
    c0 = Cond(V('x'), 'on', V('y'))
    c1 = Cond(V('y'), 'left-of', V('z'))
    c2 = Cond(V('z'), 'color', 'red')

    @Production(AND(c0, c1, c2))
    def p0():
        pass
    net.add_production(p0)

    # end

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

    am0 = net.build_or_share_alpha_memory(c0)
    am1 = net.build_or_share_alpha_memory(c1)
    am2 = net.build_or_share_alpha_memory(c2)
    dummy_join = am0.successors[0]
    join_on_value_y = am1.successors[0]
    join_on_value_z = am2.successors[0]
    match_c0 = dummy_join.children[0]
    match_c0c1 = join_on_value_y.children[0]
    match_c0c1c2 = join_on_value_z.children[0]

    assert am0.items == [wmes[0], wmes[1], wmes[3], wmes[7]]
    assert am1.items == [wmes[4], wmes[6]]
    assert am2.items == [wmes[2], wmes[8]]
    assert len(match_c0.items) == 4
    assert len(match_c0c1.items) == 2
    assert len(match_c0c1c2.items) == 1

    t0 = Token(Token(None, None), wmes[0])
    t1 = Token(t0, wmes[4])
    t2 = Token(t1, wmes[8])
    assert match_c0c1c2.items[0].wme == t2.wme

    print(wmes[0].tokens)
    print(match_c0.items)
    print(match_c0c1.items)
    print(match_c0c1c2.items)
    print()

    net.remove_wme(wmes[0])

    print(wmes[0].tokens)
    print(match_c0.items)
    print(match_c0c1.items)
    print(match_c0c1c2.items)

    assert am0.items == [wmes[1], wmes[3], wmes[7]]
    assert am1.items == [wmes[4], wmes[6]]
    assert am2.items == [wmes[2], wmes[8]]
    assert len(match_c0.items) == 3
    assert len(match_c0c1.items) == 1
    assert len(match_c0c1c2.items) == 0


def test_dup():
    # setup
    net = ReteNetwork()
    c0 = Cond(V('x'), 'self', V('y'))
    c1 = Cond(V('x'), 'color', 'red')
    c2 = Cond(V('y'), 'color', 'red')

    @Production(AND(c0, c1, c2))
    def p0():
        pass
    net.add_production(p0)

    wmes = [
        WME('B1', 'self', 'B1'),
        WME('B1', 'color', 'red'),
    ]
    for wme in wmes:
        net.add_wme(wme)
    # end

    am = net.build_or_share_alpha_memory(c2)
    join_on_value_y = am.successors[1]
    match_for_all = join_on_value_y.children[0]

    assert len(match_for_all.items) == 1


def test_negative_condition():
    # setup
    net = ReteNetwork()
    c0 = Cond(V('x'), 'on', V('y'))
    c1 = Cond(V('y'), 'left-of', V('z'))
    c2 = Neg(V('z'), 'color', 'red')

    @Production(AND(c0, c1, c2))
    def p0():
        pass
    net.add_production(p0)

    # end

    wmes = [
        WME('B1', 'on', 'B2'),
        WME('B1', 'on', 'B3'),
        WME('B1', 'color', 'red'),
        WME('B2', 'on', 'table'),
        WME('B2', 'left-of', 'B3'),
        WME('B2', 'color', 'blue'),
        WME('B3', 'left-of', 'B4'),
        WME('B3', 'on', 'table'),
        WME('B3', 'color', 'red'),
    ]
    for wme in wmes:
        net.add_wme(wme)

    am0 = net.build_or_share_alpha_memory(c0)
    am1 = net.build_or_share_alpha_memory(c1)
    am2 = net.build_or_share_alpha_memory(c2)
    dummy_join = am0.successors[0]
    join_on_value_y = am1.successors[0]
    join_on_value_z = am2.successors[0]
    match_c0 = dummy_join.children[0]
    match_c0c1 = join_on_value_y.children[0]
    match_c0c1c2 = join_on_value_z.children[0]

    print(match_c0.items)
    print(match_c0c1.items)
    print(type(join_on_value_z))
    print(match_c0c1c2.items)

    assert list(p0.activations)[0].wmes == [
        WME('B1', 'on', 'B3'),
        WME('B3', 'left-of', 'B4'),
        None
    ]


def test_multi_productions():
    net = ReteNetwork()
    c0 = Cond(V('x'), 'on', V('y'))
    c1 = Cond(V('y'), 'left-of', V('z'))
    c2 = Cond(V('z'), 'color', 'red')
    c3 = Cond(V('z'), 'on', 'table')
    c4 = Cond(V('z'), 'left-of', 'B4')

    @Production(AND(c0, c1, c2))
    def p0():
        pass

    @Production(AND(c0, c1, c3, c4))
    def p1():
        pass

    net.add_production(p0)
    net.add_production(p1)

    wmes = [
        WME('B1', 'on', 'B2'),
        WME('B1', 'on', 'B3'),
        WME('B1', 'color', 'red'),
        WME('B2', 'on', 'table'),
        WME('B2', 'left-of', 'B3'),
        WME('B2', 'color', 'blue'),
        WME('B3', 'left-of', 'B4'),
        WME('B3', 'on', 'table'),
        WME('B3', 'color', 'red'),
    ]
    for wme in wmes:
        net.add_wme(wme)

    # add product on the fly
    @Production(AND(c0, c1, c3, c2))
    def p2():
        pass
    net.add_production(p2)

    assert len(list(p0.activations)) == 1
    assert len(list(p1.activations)) == 1
    assert len(list(p2.activations)) == 1
    assert list(p0.activations)[0].wmes == [wmes[0], wmes[4], wmes[8]]
    assert list(p1.activations)[0].wmes == [wmes[0], wmes[4], wmes[7], wmes[6]]
    assert list(p2.activations)[0].wmes == [wmes[0], wmes[4], wmes[7], wmes[8]]

    net.remove_production(p2)

    print(type(p2))
    assert len(list(p2.activations)) == 0


def test_ncc():
    net = ReteNetwork()
    c0 = Cond(V('x'), 'on', V('y'))
    c1 = Cond(V('y'), 'left-of', V('z'))
    c2 = Cond(V('z'), 'color', 'red')
    c3 = Cond(V('z'), 'on', V('w'))

    # @Production(AND(c0, c1, NOT(AND(c2, c3))))
    @Production(c0 & c1 & ~(c2 & c3))
    def p0():
        pass

    net.add_production(p0)

    wmes = [
        WME('B1', 'on', 'B2'),
        WME('B1', 'on', 'B3'),
        WME('B1', 'color', 'red'),
        WME('B2', 'on', 'table'),
        WME('B2', 'left-of', 'B3'),
        WME('B2', 'color', 'blue'),
        WME('B3', 'left-of', 'B4'),
        WME('B3', 'on', 'table'),
    ]
    for wme in wmes:
        net.add_wme(wme)
    assert len(list(p0.activations)) == 2
    net.add_wme(WME('B3', 'color', 'red'))
    assert len(list(p0.activations)) == 1


def test_black_white():
    net = ReteNetwork()
    c1 = Cond(V('item'), 'cat', V('cid'))
    c2 = Cond(V('item'), 'shop', V('sid'))
    white = Ncc(
        Neg(V('item'), 'cat', '100'),
        Neg(V('item'), 'cat', '101'),
        Neg(V('item'), 'cat', '102'),
    )
    n1 = Neg(V('item'), 'shop', '1')
    n2 = Neg(V('item'), 'shop', '2')
    n3 = Neg(V('item'), 'shop', '3')

    @Production(AND(c1, c2, white, n1, n2, n3))
    def p0():
        pass

    net.add_production(p0)

    wmes = [
        WME('item:1', 'cat', '101'),
        WME('item:1', 'shop', '4'),
        WME('item:2', 'cat', '100'),
        WME('item:2', 'shop', '1'),
    ]
    for wme in wmes:
        net.add_wme(wme)

    assert len(list(p0.activations)) == 1
    assert list(p0.activations)[0].binding[V('item')] == 'item:1'
