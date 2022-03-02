from lxml.etree import fromstring
from wpdxf.wrapping.models.basic.evaluate import BasicEvaluator
from wpdxf.wrapping.objects.pairs import Example, Query
from wpdxf.wrapping.objects.resource import Resource
from wpdxf.wrapping.objects.webpage import WebPage

def test_eval_initial():
    e = BasicEvaluator()
    wp = WebPage("www.example.com")
    wp._html = "<div><a>Input Value</a><b>Output Value</b><a>Value Input</a><b>Value Output</b><a>Query Value</a><b>Output Query</b></div>"

    examples = [
        Example("Input Value", "Output Value"),
        Example("Value Input", "Value Output"),
        Example("Missing", "Output Value"),
        Example("Input Value", "Missing"),
    ]
    queries = [Query("Query Value"), Query("Missing")]

    target_ex_matches = [examples[0], examples[1]]

    # eval_initial (based on webpage above)
    r = Resource("example.com", [])
    r.webpages = [wp]

    e.evaluate_initial(r, examples, queries)
    assert target_ex_matches == list(r.examples().keys())
    
    r._xpath = "//*[./a=$abs_start_path]/b"
    result = e.evaluate(r, examples, queries)
    target_matches = set([Query("Input Value"), Query("Value Input"), Query("Query Value")])
    assert target_matches == set(result.keys())
