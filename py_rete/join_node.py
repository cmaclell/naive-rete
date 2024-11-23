"""
Join Node: a kind of Rete Node
with an alpha memory connected to its right side,
and another node in the beta network on the right.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from py_rete.common import Token
from py_rete.common import WME
from py_rete.common import V
from py_rete.alpha import AlphaMemory
from py_rete.beta import ReteNode

if TYPE_CHECKING:  # pragma: no cover
    # Mypy for 3.8...
    from typing import Dict
    from typing import Any
    from py_rete.conditions import Cond


class JoinNode(ReteNode):
    """
    A beta network class. Does the heavly lifting of joining tokens from a beta
    memory with wmes from an alpha memory.

    This class has an alpha memory connected to its right side, which triggers
    right_activations.

    The parent constitutes the left side (another node in the beta network),
    which triggers left_activations.

    When the JoinNode is right activated, it checks the incoming wme against
    all the tokens in the parent (on the left side), using the tests. For
    every match, updated bindings are created and the children are activated.

    When the JoinNode is left activated, it checks the incoming token against
    the wmes from the alpha memory instead (essentially the opposite direction
    as above). Similarly, for matches, updated bindings are created and
    children are activated.
    """
    def __init__(self, amem: AlphaMemory, condition: Cond, **kwargs):
        super().__init__(**kwargs)
        self.amem: AlphaMemory = amem
        self.condition = condition
        self.nearest_ancestor_with_same_amem = None
        self.vars = [(v, field) for field, v in self.condition.vars if
                     isinstance(v, V)]

    @property
    def amem_recently_nonempty(self) -> bool:
        return len(self.amem.items) == 1

    @property
    def parent_recently_nonempty(self) -> bool:
        return len(self.parent.items) == 1

    @property
    def right_unlinked(self) -> bool:
        return len(self.parent.items) == 0

    @property
    def left_unlinked(self) -> bool:
        return len(self.amem.items) == 0

    def update_nearest_ancestor_with_same_amem(self):
        ancestor = self.parent.find_nearest_ancestor_with_same_amem(self.amem)
        self.nearest_ancestor_with_same_amem = ancestor

    def find_nearest_ancestor_with_same_amem(self, amem: AlphaMemory):
        if self.amem == amem:
            return self
        return self.parent.find_nearest_ancestor_with_same_amem(amem)

    def right_activation(self, wme: WME, new_node=False) -> None:
        """
        Called when an element is added to the respective alpha memory.

        The new_node parameter handles the edge case
        where the right activation comes from
        ``update_new_node_with_matches_from_above(...)``.
        In this case, it looks like the amem was recently non-empty,
        but it actually isn't the case.
        """
        if self.amem_recently_nonempty and not new_node:
            self.relink_to_beta_memory()
            if not self.parent.items:
                self.amem.successors.remove(self)
        for token in self.parent.items:
            if self.perform_join_test(token, wme):
                binding = self.make_binding(token, wme)
                for child in self.children:
                    child.left_activation(token, wme, binding)

    def relink_to_alpha_memory(self):
        ancestor = self.nearest_ancestor_with_same_amem
        while ancestor and ancestor.right_unlinked:
            ancestor = ancestor.nearest_ancestor_with_same_amem
        if ancestor:
            try:
                loc = self.amem.successors.index(ancestor)
            except ValueError:
                loc = -1
            self.amem.successors.insert(loc+1, self)
        else:
            self.amem.successors.insert(0, self)

    def relink_to_beta_memory(self):
        self.parent.children.append(self)

    def left_activation(self, token: Token) -> None:
        """
        Called when an element is added to the parent beta node.
        """
        if self.parent_recently_nonempty:
            self.relink_to_alpha_memory()
            if not self.amem.items:
                self.parent.children.remove(self)
        for wme in self.amem.items:
            if self.perform_join_test(token, wme):
                binding = self.make_binding(token, wme)
                for child in self.children:
                    child.left_activation(token=token, wme=wme,
                                          binding=binding)

    def perform_join_test(self, token: Token, wme: WME) -> bool:
        """
        Test if the token and wme are compatible.
        """
        for v, field in self.vars:
            if (v in token.binding and
                    getattr(wme, field) != token.binding[v]):
                return False
        return True

    def make_binding(self, token: Token, wme: WME) -> Dict[V, Any]:
        """
        Makes updated bindings that result from joining token and wme.
        """
        new_binding = {v: getattr(wme, field) for v, field in self.vars}
        if new_binding:
            binding = token.binding.copy()
            binding.update(new_binding)
            return binding
        else:
            return token.binding
