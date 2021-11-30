from urllib.parse import urlsplit


def group_uris(candidates, res_filter):
    forest = {}
    for uri, (ex_matches, q_matches) in candidates.items():
        u_split = urlsplit(uri)
        path = u_split.path.split("/")[1:]
        if u_split.query:
            path.append(u_split.query)
        if u_split.fragment:
            path.append(u_split.fragment)

        tree = forest.get(u_split.netloc)
        if tree is None:
            tree = URITree(u_split.netloc, None)
            forest[u_split.netloc] = tree

        tree.add(*path, ex_matches=ex_matches, q_matches=q_matches, leaf=uri)

    groups = []
    filtered_forest = []
    for tree in forest.values():
        filter_result = tree.traverse(res_filter.node_filter)
        groups.extend(filter_result)
        if filter_result:
            filtered_forest.append(tree)

    print(f"Grouping of webpages resulted in {len(forest)} trees, of which {len(filtered_forest)} trees are considered as relevant:")
    print("\n".join([str(tree) for tree in filtered_forest]))

    return [(t.path(), [l.uri for l in t.leaves()]) for t in groups]


class URITree:
    def __init__(self, label, parent) -> None:
        self.label = label
        self.parent = parent
        self.children = dict()
        self.ex_matches = set()
        self.q_matches = set()

    def __str__(self) -> str:
        return self.__str_off__()  # self.label + ": " + str(self.children.keys())

    def __str_off__(self, off=0) -> str:
        s = off * " " + self.label + str(self.ex_matches) + str(self.q_matches) + "\n"
        for c in self.children.values():
            s += c.__str_off__(off + 2)
        return s

    def add_child(self, label):
        if not label in self.children:
            child = URITree(label, self)
            self.children[label] = child
        else:
            child = self.children[label]
        return child

    def add(self, *args, ex_matches, q_matches, leaf):
        self.ex_matches |= set(ex_matches)
        self.q_matches |= set(q_matches)
        if len(args) > 0:
            child = self.add_child(args[0])
            child.add(*args[1:], ex_matches=ex_matches, q_matches=q_matches, leaf=leaf)
        else:
            self.uri = leaf

    def leaves(self):
        return self.traverse(lambda n: len(n.children) == 0)

    def path(self):
        path = self.label
        parent = self.parent
        while parent:
            path = parent.label + "/" + path
            parent = parent.parent
        return path

    def traverse(self, filter_func):
        result = []
        queue = [self]
        while queue:
            node = queue.pop()
            if filter_func(node):
                result.append(node)
            else:
                queue.extend(node.children.values())
        return result
