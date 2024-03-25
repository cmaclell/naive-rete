from __future__ import annotations
from typing import TYPE_CHECKING
import random
from itertools import product

from py_rete.bind_node import BindNode
from py_rete.filter_node import FilterNode
from py_rete.ncc_node import NccPartnerNode
from py_rete.ncc_node import NccNode
from py_rete.negative_node import NegativeNode
from py_rete.join_node import JoinNode
from py_rete.pnode import PNode
from py_rete.common import WME
from py_rete.common import V
from py_rete.common import Match
from py_rete.fact import Fact
from py_rete.alpha import AlphaMemory
from py_rete.beta import ReteNode
from py_rete.beta import BetaMemory
from py_rete.conditions import Cond
from py_rete.conditions import Ncc
from py_rete.conditions import Neg
from py_rete.conditions import Filter
from py_rete.conditions import Bind
from py_rete.production import Production

if TYPE_CHECKING:  # pragma: no cover
    from typing import Optional
    from typing import Generator
    from typing import Dict
    from typing import Tuple
    from typing import List
    from typing import Set
    from typing import Union
    from typing import Hashable


class ReteNetwork:
    """
    A Rete Network to store all the facts and productions to compute matches.
    """

    def __init__(self):
        self.alpha_hash: Dict[
            Tuple[Hashable, Hashable, Hashable], AlphaMemory] = {}
        self.beta_root = ReteNode()
        self.buf = None
        self.pnodes: List[PNode] = []
        self.working_memory: Set[WME] = set()
        self.facts: Dict[str, Fact] = {}
        self.fact_counter: int = 0
        self.production_counter: int = 0
        self.productions: Set[Production] = set()

    def run(self, n: int = 10) -> None:
        """
        First n rules, chosen at random. After each rule is fired the facts are
        updated and new matches computed.
        """
        while n > 0:
            matches = list(self.matches)
            if len(matches) <= 0:
                break
            match = random.choice(matches)
            match.fire()
            n -= 1

    def __repr__(self):
        output = 'Productions:\n'
        for p in self.productions:
            output += "{}: {}\n".format(p.id, p)
        output += "\nFacts:\n"
        for fid in self.facts:
            copy = self.facts[fid].duplicate()
            for k in copy:
                if isinstance(copy[k], Fact):
                    copy[k] = copy[k].id
            output += "{}: {}\n".format(fid, copy)
        output += "\nWMEs:\n"
        for wme in self.working_memory:
            output += "{}\n".format(wme)
        return output

    def num_nodes(self):
        def get_nodes(node):
            if len(node.children) == 0:
                return [node]

            nodes = [node]
            for c in node.children:
                nodes += get_nodes(c)
            return nodes

        nodes = get_nodes(self.beta_root)
        return len(nodes)

    def render_graph(self):
        import networkx as nx
        from networkx.drawing.nx_agraph import graphviz_layout
        import matplotlib.pyplot as plt

        G = nx.DiGraph()
        G.add_node("root")

        def get_nodes(node):
            if len(node.children) == 0:
                return [node]

            nodes = [node]
            for c in node.children:
                nodes += get_nodes(c)
            return nodes

        def get_label(node):
            if isinstance(node, JoinNode):
                return (node, node.condition)
            if isinstance(node, AlphaMemory):
                for k in self.alpha_hash.keys():
                    if node == self.alpha_hash[k]:
                        return "{}:\n{} items".format(k, len(node.items))
                        # return "{}:\n{}".format(k, "\n".join([str(t) for t in
                        # node.items]))
            if isinstance(node, BetaMemory):
                return "{}:\n{} items".format(str(node), len(node.items))
                # return "{}:\n{}".format(str(type(node)), "\n".join([str(t)
                # for t in node.items]))

            return node

        for k in self.alpha_hash.keys():
            G.add_node(get_label(self.alpha_hash[k]))
            G.add_edge("root", get_label(self.alpha_hash[k]))

        nodes = get_nodes(self.beta_root)
        print('nodes', len(nodes))
        for n in nodes:
            G.add_node(get_label(n))
            if n.parent:
                G.add_edge(get_label(n.parent), get_label(n))
            if isinstance(n, JoinNode):
                G.add_edge(get_label(n.amem), get_label(n))

        G.add_edge('root', get_label(self.beta_root))

        pos = graphviz_layout(G, prog='dot')
        nx.draw(G, pos, with_labels=True, font_size=8)
        # nx.draw(G, with_labels=True, font_weight="bold")
        plt.show()

    def add_fact(self, fact: Fact) -> None:
        """
        Adds a fact to the network.
        """
        if fact.id is not None:
            raise ValueError("Fact already has an id, cannot add")

        copy = fact.duplicate()
        for k in copy:
            if isinstance(copy[k], Fact):
                if copy[k].id is None:
                    self.add_fact(copy[k])
                copy[k] = copy[k].id

        fact.id = "f-{}".format(self.fact_counter)
        copy.id = fact.id
        self.fact_counter += 1

        self.facts[fact.id] = fact

        for wme in copy.wmes:
            self.add_wme(wme)

    def remove_fact(self, fact: Fact) -> None:
        """
        Removes a fact from the network.
        """
        if fact.id is None or fact.id not in self.facts:
            raise ValueError("Fact has no id or does not exist in network.")

        if fact.id in self.facts:
            del self.facts[fact.id]
            self.remove_wme_by_fact_id(fact.id)

        fact.id = None

    def get_fact_by_id(self, fact_id: str) -> Fact:
        return self.facts[fact_id]

    def update_fact(self, fact: Fact) -> None:
        # TODO: Figure out a fancy way to only update part of the fact
        self.remove_fact(fact)
        self.add_fact(fact)

    def remove_wme_by_fact_id(self, identifier: str) -> None:
        to_remove = [wme for wme in self.working_memory if wme.identifier ==
                     identifier]
        for wme in to_remove:
            self.remove_wme(wme)

    def get_new_match(self) -> Optional[Match]:
        for pnode in self.pnodes:
            if pnode.new:
                t = pnode.pop_new_token()
                return Match(pnode, t)
        return None

    @property
    def new_matches(self) -> Generator[Match, None, None]:
        for pnode in self.pnodes:
            for t in pnode.new:
                yield Match(pnode, t)

    @property
    def matches(self) -> Generator[Match, None, None]:
        for pnode in self.pnodes:
            for t in pnode.activations:
                yield Match(pnode, t)

    @property
    def wmes(self) -> Set[WME]:
        return self.working_memory

    def add_production(self, prod: Production) -> None:
        """
        Adds a production to the ReteNetwork.
        """
        if prod.id is not None:
            raise ValueError("Production already has an id, cannot add")

        prod.id = "p-{}".format(self.production_counter)
        prod._rete_net = self

        self.production_counter += 1
        self.productions.add(prod)

        for conds in prod.get_rete_conds():
            current_node = self.build_or_share_network_for_conditions(
                self.beta_root, conds, [])
            p_node = self.build_or_share_p(current_node, prod)

            self.pnodes.append(p_node)
            prod.p_nodes.append(p_node)

    def remove_production(self, prod: Production) -> None:
        """
        Removes a pnode from the network
        """
        if prod.id is None:
            raise ValueError("Production has no id, cannot remove.")

        # Remove production
        self.productions.remove(prod)

        for pnode in prod.p_nodes:
            self.delete_node_and_any_unused_ancestors(pnode)
            self.pnodes.remove(pnode)

        prod.id = None
        prod.p_nodes = []

    def add_wme(self, wme: WME) -> None:
        if wme in self.working_memory:
            return

        if (wme.identifier == '#*#' or
                wme.attribute == '#*#' or
                wme.value == '#*#'):
            raise ValueError("WME cannot use the value '#*#' as this is "
                             "the wild card match symbol used internally by "
                             "py_rete.")

        keys = product([wme.identifier, '#*#'],
                       [wme.attribute, '#*#'],
                       [wme.value, '#*#'])

        for key in keys:
            if key in self.alpha_hash:
                self.alpha_hash[key].activation(wme)

        self.working_memory.add(wme)

    def remove_wme(self, wme: WME) -> None:
        for stored_wme in self.working_memory:
            if wme == stored_wme:
                wme = stored_wme

        for am in wme.amems:
            am.items.remove(wme)
            if not am.items:
                for node in am.successors:
                    if (isinstance(node, JoinNode) and
                            not isinstance(node, NegativeNode)):
                        node.parent.children.remove(node)

        while wme.tokens:
            wme.tokens[0].delete_token_and_descendents()

        for jr in wme.negative_join_results:
            jr.owner.join_results.remove(jr)
            if not jr.owner.join_results:
                if jr.owner.node and jr.owner.node.children is not None:
                    for child in jr.owner.node.children:
                        child.left_activation(jr.owner, None, jr.owner.binding)

        self.working_memory.remove(wme)

    def build_or_share_alpha_memory(self, condition):
        """
        :type condition: Condition
        :rtype: AlphaMemory
        """
        id_test = '#*#'
        attr_test = '#*#'
        value_test = '#*#'

        if (condition.identifier == id_test or
                condition.attribute == attr_test or
                condition.value == value_test):
            raise ValueError("Condition cannot use the value '#*#' as this is "
                             "the wild card match symbol used internally by "
                             "py_rete.")

        if not isinstance(condition.identifier, V):
            id_test = condition.identifier
        if not isinstance(condition.attribute, V):
            attr_test = condition.attribute
        if not isinstance(condition.value, V):
            value_test = condition.value

        key = (id_test, attr_test, value_test)

        if key in self.alpha_hash:
            return self.alpha_hash[key]

        self.alpha_hash[key] = AlphaMemory()
        self.alpha_hash[key].key = key

        for w in self.working_memory:
            if condition.test(w):
                self.alpha_hash[key].activation(w)

        return self.alpha_hash[key]

    def build_or_share_join_node(self, parent: BetaMemory, amem: AlphaMemory,
                                 condition: Cond) -> JoinNode:

        for child in parent.all_children:
            if (type(child) == JoinNode and child.amem == amem and
                    child.condition == condition):
                return child
        node = JoinNode(children=[], parent=parent, amem=amem,
                        condition=condition)
        parent.children.append(node)
        parent.all_children.append(node)
        amem.successors.append(node)
        amem.reference_count += 1
        node.update_nearest_ancestor_with_same_amem()
        if not parent.items:
            amem.successors.remove(node)
        elif not amem.items:
            parent.children.remove(node)

        return node

    def build_or_share_negative_node(self, parent: JoinNode, amem: AlphaMemory,
                                     condition: Neg) -> NegativeNode:

        for child in parent.children:
            if (isinstance(child, NegativeNode) and child.amem == amem and
                    child.condition == condition):
                return child
        node = NegativeNode(parent=parent, amem=amem, condition=condition)
        parent.children.append(node)
        amem.successors.append(node)

        amem.reference_count += 1
        node.update_nearest_ancestor_with_same_amem()
        self.update_new_node_with_matches_from_above(node)
        if not node.items:
            amem.successors.remove(node)

        return node

    def build_or_share_beta_memory(self, parent: ReteNode) -> BetaMemory:
        for child in parent.children:
            # if isinstance(child, BetaMemory):  # Don't include subclasses
            if type(child) == BetaMemory:
                return child
        node = BetaMemory(parent=parent)
        parent.children.append(node)
        self.update_new_node_with_matches_from_above(node)
        return node

    def build_or_share_p(self, parent: ReteNode, prod: Production) -> PNode:
        for child in parent.children:
            if isinstance(child, PNode):
                return child
        node = PNode(production=prod, parent=parent)
        parent.children.append(node)
        self.update_new_node_with_matches_from_above(node)
        return node

    def build_or_share_ncc_nodes(self, parent: JoinNode, ncc: Ncc,
                                 earlier_conds: List[Cond]
                                 ) -> NccNode:
        bottom_of_subnetwork = self.build_or_share_network_for_conditions(
            parent, ncc, earlier_conds)
        for child in parent.children:
            if (isinstance(child, NccNode) and child.partner.parent ==
                    bottom_of_subnetwork):
                return child

        ncc_partner = NccPartnerNode(parent=bottom_of_subnetwork)
        ncc_node = NccNode(partner=ncc_partner, children=[], parent=parent)
        ncc_partner.ncc_node = ncc_node
        parent.children.insert(0, ncc_node)
        bottom_of_subnetwork.children.append(ncc_partner)
        ncc_partner.number_of_conditions = ncc.number_of_conditions
        self.update_new_node_with_matches_from_above(ncc_node)
        self.update_new_node_with_matches_from_above(ncc_partner)
        return ncc_node

    def build_or_share_filter_node(self, parent: ReteNode,
                                   f: Filter) -> FilterNode:
        for child in parent.children:
            if isinstance(child, FilterNode) and child.func == f.func:
                return child
        node = FilterNode([], parent, f.func, self)
        parent.children.append(node)
        return node

    def build_or_share_bind_node(self, parent: ReteNode, b: Bind) -> BindNode:
        for child in parent.children:
            if (isinstance(child, BindNode) and child.func == b.func and
                    child.bind == b.to):
                return child
        node = BindNode([], parent, b.func, b.to, self)
        parent.children.append(node)
        return node

    def build_or_share_network_for_conditions(self, parent: ReteNode,
                                              rule: Union[Ncc, List[Cond]],
                                              earlier_conds: List[Cond]
                                              ) -> ReteNode:
        current_node = parent
        conds_higher_up = earlier_conds
        for cond in rule:
            if isinstance(cond, Cond) and not isinstance(cond, Neg):
                current_node = self.build_or_share_beta_memory(current_node)
                am = self.build_or_share_alpha_memory(cond)
                current_node = self.build_or_share_join_node(current_node, am,
                                                             cond)
            elif isinstance(cond, Neg):
                am = self.build_or_share_alpha_memory(cond)
                current_node = self.build_or_share_negative_node(current_node,
                                                                 am, cond)
            elif isinstance(cond, Ncc):
                current_node = self.build_or_share_ncc_nodes(current_node,
                                                             cond,
                                                             conds_higher_up)
            elif isinstance(cond, Filter):
                current_node = self.build_or_share_filter_node(current_node,
                                                               cond)
            elif isinstance(cond, Bind):
                current_node = self.build_or_share_bind_node(current_node,
                                                             cond)
            conds_higher_up.append(cond)
        return current_node

    def update_new_node_with_matches_from_above(self, new_node: ReteNode
                                                ) -> None:
        parent = new_node.parent
        if parent == self.beta_root:
            new_node.left_activation(None, None, {})
        elif (isinstance(parent, BetaMemory) and
                not isinstance(parent, (NccNode, NegativeNode))):
            for tok in parent.items:
                new_node.left_activation(token=tok)
        elif (isinstance(parent, JoinNode) and
                not isinstance(parent, NegativeNode)):
            saved_list_of_children = parent.children
            parent.children = [new_node]
            for item in parent.amem.items:
                parent.right_activation(item, new_node=True)
            parent.children = saved_list_of_children
        elif isinstance(parent, NegativeNode):
            for token in parent.items:
                if not token.join_results:
                    new_node.left_activation(token, None, token.binding)
        elif isinstance(parent, NccNode):
            for token in parent.items:
                if not token.ncc_results:
                    new_node.left_activation(token, None, token.binding)
        elif isinstance(parent, (BindNode, FilterNode)):
            saved_list_of_children = parent.children
            parent.children = [new_node]
            self.update_new_node_with_matches_from_above(parent)
            parent.children = saved_list_of_children

    def delete_alpha_memory(self, amem: AlphaMemory):
        del self.alpha_hash[amem.key]

    def delete_node_and_any_unused_ancestors(self, node: ReteNode):
        if isinstance(node, NccNode):
            self.delete_node_and_any_unused_ancestors(node.partner)

        if isinstance(node, BetaMemory):
            while node.items:
                node.items[0].delete_token_and_descendents()

        if isinstance(node, NccPartnerNode):
            while node.new_result_buffer:
                node.new_result_buffer[0].delete_token_and_descendents()

        if isinstance(node, JoinNode) and not isinstance(node, NegativeNode):
            if not node.right_unlinked:
                node.amem.successors.remove(node)

            node.amem.reference_count -= 1

            if node.amem.reference_count == 0:
                self.delete_alpha_memory(node.amem)

            if not node.left_unlinked:
                node.parent.children.remove(node)

            node.parent.all_children.remove(node)

            if not node.parent.all_children:
                self.delete_node_and_any_unused_ancestors(node.parent)

        elif node.parent:
            node.parent.children.remove(node)
            if not node.parent.children:
                self.delete_node_and_any_unused_ancestors(node.parent)
