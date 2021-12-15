from typing import List

from wrapping.objects.xpath.node import XPathNode
from wrapping.objects.xpath.path import XPath


def merge(xpaths: List[XPath]) -> XPath:
    result = XPath()
    # All xpaths must have the same length (aligned).
    xpath_len = len(xpaths[0])
    for i in range(xpath_len):
        axisname = xpaths[0][i].axisname
        nodetest = xpaths[0][i].nodetest
        predicates = xpaths[0][i].predicates
        for xpath in xpaths[1:]:
            # These are reduced representations of the formal definitions.
            # axisname
            if axisname != xpath[i].axisname:
                axisname = "descendant-or-self"

            # nodetest
            if nodetest != xpath[i].nodetest:
                nodetest = "node()"

            # predicates
            if predicates != xpath[i].predicates:
                predicates = None

        result.append(
            XPathNode(axisname=axisname, nodetest=nodetest, predicates=predicates)
        )
    return result

