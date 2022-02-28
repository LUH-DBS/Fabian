from itertools import combinations
from typing import Dict, List, Set, Tuple
from urllib.parse import urlsplit

from wpdxf.wrapping.objects.pairs import Example, Query


def uri_to_list(uri: str):
    us = urlsplit(uri)
    path = us.path.split("/")[1:]
    if us.query:
        path.append(us.query)
    if us.fragment:
        path.append(us.fragment)
    return us.netloc, path


def all_pw_disjoint(matches: List[set]) -> bool:
    # All sets are pairwise disjunct,
    # if there exists no duplicates between the already seen values and the current set.
    _union = set()
    for m in matches:
        if m & _union:
            return False
        _union |= m
    return True


class URITree:
    def __init__(self) -> None:
        self.root_nodes = {}

    def __str__(self) -> str:
        return "\n".join(str(node) for node in self.root_nodes.values())

    def add_uri(self, uri: str, ex_matches, q_matches, allow_new=True):
        host, path = uri_to_list(uri)
        if host not in self.root_nodes:
            if not allow_new:
                return
            root = URITreeNode(host, None)
            self.root_nodes[host] = root
        else:
            root = self.root_nodes[host]
        root.add_path(*path, ex_matches=ex_matches, q_matches=q_matches, leaf=uri)
        return root

    def reduce(self, tau):
        self.root_nodes = {
            k: v for k, v in self.root_nodes.items() if len(v.ex_matches) >= tau
        }

    def to_dict(self):
        result = {}
        for node in self.root_nodes.values():
            result.update(node.to_dict())
        return result


class URITreeNode:
    def __init__(self, label, parent) -> None:
        self.label = label
        self.parent = parent
        self.children = dict()
        self.ex_matches = set()
        self.q_matches = set()

    def __str__(self) -> str:
        return self.__str_off__()  # self.label + ": " + str(self.children.keys())

    def __str_off__(self, off=0) -> str:
        s = (
            off * " "
            + f"{self.label} "
            + f"{self.ex_matches} "
            + f"{self.q_matches} "
            + (f"{self.uri}" if not self.children else "")
            + "\n"
        )
        for c in self.children.values():
            s += c.__str_off__(off + 2)
        return s

    @staticmethod
    def create_uri_trees(candidates: Dict[str, Tuple[Set[int], Set[int]]]):
        """Creates a forest of uri trees. 
        Each leaf represents a unique website (the uri is stored for each leaf node), 
        each internal node represents a step (/step/...) of the uri path.
        The root of each tree is the 'netloc' or domain.
        The matches are stored for each internal and external node.

        Example:
            Input: {
                "www.exA.com/stepA/stepC": ({0},{1}), 
                "www.exA.com/stepA/stepD": ({1},{0}), 
                "www.exA.com/stepB": ({0},{0}), 
                "www.exB.com/stepA": ({0},{1})
            }
            Output:
            exA.com ({0,1}, {0,1})  - stepA ({0,1},{0,1})   - stepC ({0},{1})
                                    |                       - stepD ({1},{0})
                                    - stepB ({0},{0})

            exB.com ({0},{1})       - stepA ({0},{1})

        Args:
            candidates (Dict[str, Tuple[Set[int], Set[int]]]): uri -> matches mapping, 
            where matches is a tuple of matches in the examples and matches in the queries.

        Returns:
            Dict[str, URITree]: A forest of uritrees, as a dict (keys are the values of the trees' roots).
        """
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
                tree = URITreeNode(u_split.netloc, None)
                forest[u_split.netloc] = tree

            tree.add_path(*path, ex_matches=ex_matches, q_matches=q_matches, leaf=uri)

        return forest

    def add_child(self, label: str):
        """The children of each node are considered as unique.
        The method checks whether a child with the 'label' exists. 
        If so, it returns the existing child. 
        Otherwise, it creates the child and returns the new cild.

        Args:
            label (str): Unique label for a (new) child of self.

        Returns:
            URITreeNode: The child with value 'label'.
        """
        if label in self.children:
            return self.children[label]
        child = URITreeNode(label, self)
        self.children[label] = child
        return child

    def add_path(
        self, *args: Tuple[str], ex_matches: Set[int], q_matches: Set[int], leaf: str
    ):
        """Adds a new path into the tree. Starting at self, traversing all nodes in args (given by labels).
        The matches for each node on the path are updated with the given 'ex_matches' and 'q_matches'.

        Args:
            ex_matches (Set[int]): Examples matched by the path's leaf.
            q_matches (Set[int]): Queries matched by the path's leaf.
            leaf (str): The leaf's uri.
        """
        node = self
        while node:
            node.ex_matches |= set(ex_matches)
            node.q_matches |= set(q_matches)
            if args:
                arg0, *args = args
                node = node.add_child(arg0)
            else:
                node.uri = leaf
                node = None

    def leaves(self):
        return self.bfs_filter(lambda n: len(n.children) == 0)

    def path(self):
        path = self.label
        parent = self.parent
        while parent:
            path = parent.label + "/" + path
            parent = parent.parent
        return path

    def bfs_filter(self, filter_func) -> list:
        """Traverses the tree with BFS-strategy. 
        Evaluates the 'filter_func' on each node during traversal. 
        Returns the first node on each path where the 'filter_func' evaluates to True.

        Args:
            filter_func : A method that consumes a URITreeNode and returns a bool.

        Returns:
            List[URITreeNode]: All "first" nodes where 'filter_func' evaluates to True.
        """
        result = []
        queue = [self]
        while queue:
            node = queue.pop()
            if filter_func(node):
                result.append(node)
            else:
                queue.extend(node.children.values())
        return result

    def decompose(self, tau) -> list:
        children = list(
            filter(lambda n: len(n.ex_matches) >= tau, self.children.values())
        )
        # If a decomposition would result in a loss of queries,
        # return node as resource
        if not children or set.union(*[n.q_matches for n in children]) < self.q_matches:
            return [self]

        decomposition = [_n for c in children for _n in c.decompose(tau)]

        # If decomposition leads to partitions that have all pairwise disjunct example sets,
        # return node as resource.
        if len(decomposition) > 1 and all_pw_disjoint(
            map(lambda x: x.ex_matches, decomposition)
        ):
            return [self]

        return decomposition

    def to_dict(self) -> Dict[str, Tuple[Set[Example], Set[Query]]]:
        return {l.uri: (l.ex_matches, l.q_matches) for l in self.leaves()}


if __name__ == "__main__":
    tau = 2

    def _resource_filter(node):
        # Returns True, when the node matches at least tau examples and all children cover less queries
        return (
            len(node.ex_matches) >= tau
            # and all(node.ex_matches > c.ex_matches for c in node.children.values()) # always True
            and all(node.q_matches > c.q_matches for c in node.children.values())
        )

    def _resource_filter(node):
        # Returns True, when the node matches at least tau examples and all children cover less queries
        return (
            len(node.ex_matches) >= tau
            # and all(node.ex_matches > c.ex_matches for c in node.children.values()) # always True
            and all(node.q_matches > c.q_matches for c in node.children.values())
        )

    uritree = URITree()
    uritree.add_uri("http://www.example.com/A/A1/C", {0, 1}, {0, 4})
    uritree.add_uri("http://www.example.com/A/A1/D", {2, 3}, {1, 2})
    uritree.add_uri("http://www.example.com/B/B1/F", {0, 1}, {0, 1})
    uritree.add_uri("http://www.example.com/B/B1/G", {2, 3}, {2, 3})
    uritree.add_uri("http://www.example.com/B/B1/O", {0, 1}, {2, 3})
    uritree.add_uri("http://www.example.com/B/B2/H", set(), {5,})
    uritree.add_uri("http://www.example.com/C/C1/C", set(), {5,})
    uritree.add_uri("http://www.example.com/D/D1/D", {0, 1}, set())

    tree: URITreeNode = uritree.root_nodes["www.example.com"]

    # print("Filter")
    # print(tree.label)
    # for node in tree.bfs_filter(_resource_filter):
    #     print(node)

    def all_pw_disjoint(matches: List[set]) -> bool:
        # All sets are pairwise disjunct,
        # if there exists no duplicates between the already seen values and the current set.
        _union = set()
        for m in matches:
            if m & _union:
                return False
            _union |= m
        return True

    def decompose(node: URITreeNode):
        children = list(
            filter(lambda n: len(n.ex_matches) >= tau, node.children.values())
        )
        # If a decomposition would result in a loss of queries,
        # return node as resource
        if not children or set.union(*[n.q_matches for n in children]) < node.q_matches:
            return [node]

        decomposition = [_n for c in children for _n in decompose(c)]

        # If decomposition leads to partitions that have all pairwise disjunct example sets,
        # return node as resource.
        if len(decomposition) > 1 and all_pw_disjoint(
            map(lambda x: x.ex_matches, decomposition)
        ):
            return [node]

        return decomposition

    print(tree)
    print("New Filter")
    root = tree
    res = []

    print(*[str(n) for n in decompose(tree)], sep="\n")

