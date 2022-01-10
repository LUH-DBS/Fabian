from wpdxf.wrapping.tree.uritree import URITree


class TauMatchFilter:
    def __init__(self, tau: int = 2):
        self.tau = tau

    def node_filter(self, node: URITree) -> bool:
        """Evaluates to True when the node matches at least tau examples and there is no child that matches the same examples. False, otherwise.

        Args:
            node (URITree): Node to be evaluated.

        Returns:
            bool: True indicates that the node should be considered, False indicates that the node can be ignored.
        """
        if not self.filter(node.ex_matches, node.q_matches):
            return False
        if node.children:
            for c in node.children.values():
                if c.ex_matches == node.ex_matches:
                    return False
                # if len(c.ex_matches) < self.tau:
                #     return True
        return True

    def filter(self, ex_matches: set, q_matches: set) -> bool:
        return len(ex_matches) >= self.tau
