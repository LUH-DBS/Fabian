from wrapping.tree.uritree import URITree


class TauMatchFilter:
    def __init__(self, tau: int = 2):
        self.tau = tau

    def node_filter(self, node: URITree) -> bool:
        if not self.filter(node.ex_matches, node.q_matches):
            return False
        if node.children:
            for c in node.children.values():
                if len(c.ex_matches) < self.tau:
                    return True
        else:
            return True
        return False

    def filter(self, ex_matches: set, q_matches: set) -> bool:
        return len(ex_matches) >= self.tau