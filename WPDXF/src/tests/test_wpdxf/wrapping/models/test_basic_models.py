from lxml.etree import fromstring
from wpdxf.wrapping.models.basic.evaluate import BasicEvaluator
from wpdxf.wrapping.objects.pairs import Example, Query
from wpdxf.wrapping.objects.resource import Resource
from wpdxf.wrapping.objects.webpage import WebPage


def test_eval_types():
    pair = Example(0, "Input Value", "Output Value")
    html = fromstring(
        "<div><a><h1>input</h1> value</a><b>Output Value</b><c>value input</c></div>"
    )

    # eval_type_0
    q0, arg0, q1, arg1 = eval_type_0(pair)

    target = []
    output = html.xpath(q0, **arg0)
    assert target == output

    target = [html.find("b")]
    output = html.xpath(q1, **arg1)
    assert target == output

    # eval_type_1
    q0, arg0, q1, arg1 = eval_type_1(pair)

    target = [html.find("a")]
    output = html.xpath(q0, **arg0)
    assert target == output

    target = [html.find("b")]
    output = html.xpath(q1, **arg1)
    assert target == output

    # eval_type_2
    q0, arg0, q1, arg1 = eval_type_2(pair)

    target = [html.find("a"), html.find("c")]
    output = html.xpath(q0, **arg0)
    assert target == output

    target = [html.find("b")]
    output = html.xpath(q1, **arg1)
    assert target == output


def test_eval_initial():
    e = BasicEvaluator()
    # eval_wp_initial
    wp = WebPage("www.example.com")
    wp._html = "<div><a>Input Value</a><b>Output Value</b><a>Value Input</a><b>Value Output</b><a>Query Value</a><b>Output Query</b></div>"

    examples = [
        Example(0, "Input Value", "Output Value"),
        Example(1, "Value Input", "Value Output"),
        Example(2, "Missing", "Output Value"),
        Example(3, "Input Value", "Missing"),
    ]
    queries = [Query(4, "Query Value"), Query(5, "Missing")]

    target_ex_matches = {0, 1}
    target_q_matches = {
        4,
    }

    e._eval_wp_initial(wp, examples + queries, eval_type_0)

    assert target_ex_matches == set(wp.matches)
    assert target_q_matches == set(wp.q_matches)

    # eval_initial (based on webpage above)
    r = Resource("example.com", [])
    r.webpages = [wp]

    e.eval_initial(r, examples + queries, 0)
    assert target_ex_matches == r.matched_examples()
    assert target_q_matches == r.matched_queries()

# TODO: eval_query

