from py_rete.conditions import AND, OR, NOT

from py_rete.production import dnf as disjunctive_normal_form

def test_and():
    dnf = disjunctive_normal_form(AND('A', 'B'))
    assert dnf == [['A', 'B']]

def test_or():
    dnf = disjunctive_normal_form(OR('A', 'B'))
    assert dnf == [['A'], ['B']]

def test_not1():
    dnf = disjunctive_normal_form(NOT('A'))
    assert dnf == [[NOT('A')]]

def test_not2():
    dnf = disjunctive_normal_form(NOT(NOT('A')))
    assert dnf == disjunctive_normal_form('A') == [['A']]

def test_not_and():
    dnf = disjunctive_normal_form(NOT(AND('A', 'B')))
    assert dnf == disjunctive_normal_form(OR(NOT('A'), NOT('B')))

def test_not_or():
    dnf = disjunctive_normal_form(NOT(OR('A', 'B')))
    assert dnf == disjunctive_normal_form(AND(NOT('A'), NOT('B')))
    #assert dnf == disjunctive_normal_form(OR(NOT('A'), NOT('B')))

def test_chain1():
    dnf = disjunctive_normal_form(AND('A', OR('B', 'C')))
    assert dnf == [['A', 'B'], ['A', 'C']]

def test_chain2():
    dnf = disjunctive_normal_form(OR('A', AND('B', 'C')))
    assert dnf == [['A'], ['B', 'C']]

def test_chain3():
    dnf = disjunctive_normal_form(OR('A', AND('B', OR('C', 'D'))))
    assert dnf == [['A'], ['B', 'C'], ['B', 'D']]

def test_chain4():
    dnf = disjunctive_normal_form(AND('A', OR('B', AND('C', 'D'))))
    assert dnf == [['A', 'B'], ['A', 'C', 'D']]

def test_chain5():
    dnf = disjunctive_normal_form(AND('A', OR('B', NOT(OR('C', 'D')))))
    assert dnf == [['A', 'B'], ['A', NOT('C'), NOT('D')]]

def test_chain6():
    dnf = disjunctive_normal_form(OR('A', NOT(OR('C', 'D'))))
    assert dnf == [['A'], [NOT('C'), NOT('D')]] == disjunctive_normal_form(OR('A', AND(NOT('C'), NOT('D'))))
