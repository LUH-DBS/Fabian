from typing import Dict, List, Set, Tuple
from urllib.parse import urlsplit


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
                tree = URITree(u_split.netloc, None)
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
            URITree: The child with value 'label'.
        """
        if label in self.children:
            return self.children[label]
        child = URITree(label, self)
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
                node = node.add_child(args[0])
                args = args[1:]
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
            filter_func : A method that consumes a URITree and returns a bool.

        Returns:
            List[URITree]: All "first" nodes where 'filter_func' evaluates to True.
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
