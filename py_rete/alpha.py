"""
Alpha Memory structure.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Optional
    from typing import List
    from py_rete.join_node import JoinNode
    from py_rete.common import WME


class AlphaMemory:

    def __init__(self, items: Optional[List[WME]] = None,
                 successors: Optional[List[JoinNode]] = None) -> None:
        """
        Stores a set of WMEs (items). If activating an activated wme does not
        exist, then it addes it. It also right activates all of its successors,
        which correspond to beta nodes.
        """
        self.items: List[WME] = items if items else []
        self.successors: List[JoinNode] = successors if successors else []
        self.reference_count = 0

    def activation(self, wme: WME) -> None:
        """
        Adds the wme to the alpha memory and then right activates the children
        in the beta network. Note, these are activated in reversed order to
        prevent duplicate matches.
        """
        self.items.append(wme)
        wme.amems.append(self)
        for child in reversed(self.successors):
            child.right_activation(wme)
