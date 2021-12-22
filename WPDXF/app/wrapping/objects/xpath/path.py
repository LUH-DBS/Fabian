from collections import UserList
from copy import deepcopy
from typing import List, Union

from lxml.etree import _Element
from wrapping.objects.xpath.node import AXISNAMES, XPathNode
from wrapping.objects.xpath.predicate import Predicate


def node_list(tail: _Element) -> List[_Element]:
    """Returns a list of all elements on the path between the root node and 'tail'.
    Starting at the root itself.

    Args:
        tail (_Element): End of the path.

    Returns:
        List[_Element]: All elements on the path.
    """
    result = []
    element = tail
    while element is not None:
        result += [element]
        element = element.getparent()
    return result[::-1]


class XPath(UserList):
    """A XPath wrapper with the ability to represent the underlying list of XPathNode as a valid XPath."""

    def __str__(self) -> str:
        if not self:
            return "/"
        old_len = -1
        repr = "/".join(map(str, self))
        if not repr.startswith("."):
            repr = "/" + repr
        while old_len != len(repr):
            old_len = len(repr)
            repr = repr.replace("///", "//")
        if repr.endswith("/"):
            repr += "descendant-or-self::node()"
        return repr

    def __eq__(self, __o: object) -> bool:
        return (
            hasattr(__o, "__len__")
            and len(self) == len(__o)
            and all(self[i] == __o[i] for i in range(len(self)))
        )

    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)


class RelativeXPath:
    """A relative XPath that returns end_nodes matching the described pattern, relative to the start node.
    This wrapper describes relative XPaths without using 'parent'/ascending axes.
        Described as follows:
        xpath:= common_path/root[./start_path=abs_start_path]/end_path

        Example: //div[./a/b=/div/a/b]/c/d <-> ./../../c/d (relative to start_node)
    """

    def __init__(
        self,
        start_path: Union[List[XPathNode], XPath],
        start_node: _Element = None,
        end_path: Union[List[XPathNode], XPath] = None,
        end_node: _Element = None,
        common_path: Union[List[XPathNode], XPath] = None,
    ) -> None:
        """[summary]

        Args:
            start_path (Union[List[XPathNode], XPath]): The relative_path from a last common root to the start_node.
            start_node (_Element, optional): If the RelativeXPath belongs to a real example, the start_node can be initially passed. 
            Otherwise it must be passed when the general RelativeXPath is applied to a real scenario. Defaults to None.
            end_path (Union[List[XPathNode], XPath], optional): Can be set to None, when the common_root equals the end_node. 
            It can be useful in some cases, but should be avoided in general! Defaults to ".".
            end_node (_Element, optional): Similar to start_node, 
            but the end_node is just stored for completeness and has no relevance for the actual RelativeXPath. Defaults to None.
            common_path (Union[List[XPathNode], XPath], optional): The common_path shared by the abs_start_path and the abs_end_path. Defaults to "//*".
        """
        self.start_node = start_node
        self.end_node = end_node

        self.common_path = XPath(
            [XPathNode(axisname=AXISNAMES.DEOS), XPathNode(axisname=AXISNAMES.DEOS),]
            if common_path is None
            else common_path
        )
        self.start_path = XPath(start_path)
        self.end_path = XPath(end_path or [XPathNode.new_self()])

    @staticmethod
    def new_instance(start: _Element, end: _Element, container: list = None):
        """Creates a new RelativeXPath instance based on a start and an end element from the same tree.

        Args:
            start (_Element): start_node or RelativeXPath
            end (_Element): end_node of RelativeXpath
            container (list, optional): Used to bypass values without returning. Used for testing. Defaults to None.

        Returns:
            [type]: [description]
        """
        start_path = [XPathNode.new_self()]
        end_path = []
        root_element = end
        # If start and end are the same element, the relative XPath is trivial: "."
        # Due to the structure of ElementTrees, there is always at least one common 'root' element.
        if start != end:
            start_elements = node_list(start)
            end_elements = node_list(end)

            min_len = min(len(start_elements), len(end_elements))
            for idx in range(min_len):
                if start_elements[idx] != end_elements[idx]:
                    break
            # If one path contains the other,
            # the first difference is the next step of the longer path.
            else:
                idx += 1

            root_element = end_elements[idx - 1]
            start_path += XPath(map(XPathNode.new_instance, start_elements[idx:]))
            end_path += XPath(map(XPathNode.new_instance, end_elements[idx - 1 :]))

        relativeXPath = RelativeXPath(start_path, start, end_path, end)
        if container is not None:
            container.append(root_element)

        assert start.xpath(str(relativeXPath)) == [end]
        return relativeXPath

    def as_xpath(self, start_node=None, abs_start_path=None) -> str:
        start_node = self.start_node if start_node is None else start_node
        assert not (start_node is None and abs_start_path is None)
        abs_start_path = abs_start_path or start_node.getroottree().getpath(start_node)

        root = deepcopy(self.end_path[0])
        root._predicates.append(Predicate(str(self.start_path), right=abs_start_path))
        return str(self.common_path + [root] + self.end_path[1:])

    def __str__(self) -> str:
        return self.as_xpath()

    # @property
    # def xpath(self) -> XPath:
    #     return self.common_path + self.end_path

    # def abs_start_path(self):
    #     return self.start_node.getroottree().getpath(self.start_node)
