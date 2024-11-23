"""
Rete Node and Beta Memory -- a kind of Rete Node.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from py_rete.common import Token

if TYPE_CHECKING:  # pragma: no cover
    from typing import Any, Optional
    # 3.8 and below.
    from typing import List, Dict
    # Otherwise, use list and dict
    from py_rete.common import V
    from py_rete.common import WME
    from py_rete.alpha import AlphaMemory
    from py_rete.join_node import JoinNode


class ReteNode:
    """
    Base BetaNode class, tracks parent and children.
    """
    def __init__(self, children: Optional[List[ReteNode]] = None,
                 parent: Optional[ReteNode] = None, **kwargs):
        super().__init__(**kwargs)
        self.children: List[ReteNode] = children if children else []
        self.parent: Optional[ReteNode] = parent

    def find_nearest_ancestor_with_same_amem(self, amem: AlphaMemory
                                             ) -> Optional[JoinNode]:
        return None


class BetaMemory(ReteNode):
    """
    A memory node for the beta network. Contains items (tokens) and a list of
    `all_children`, which is used in conjunction with `children` to support
    left unlinking.
    """
    def __init__(self, items: Optional[List[Token]] = None, **kwargs):
        """
        Similar to alpha memory, but items is a set of tokens instead of wmes.
        """
        super().__init__(**kwargs)
        self.items: List[Token] = items if items else []
        self.all_children: List[ReteNode] = []

    def find_nearest_ancestor_with_same_amem(self, amem: AlphaMemory
                                             ) -> Optional[JoinNode]:
        if self.parent:
            return self.parent.find_nearest_ancestor_with_same_amem(amem)
        return None  # pragma: no cover

    def left_activation(self, token: Optional[Token] = None,
                        wme: Optional[WME] = None,
                        binding: Optional[Dict[V, Any]] = None):
        """
        Creates a new token based on the incoming token/wme, adds it to the
        memory (items) then activates the children with the token.
        """
        new_token = Token(token, wme, node=self, binding=binding)
        self.items.append(new_token)
        for child in self.children:
            child.left_activation(new_token)
