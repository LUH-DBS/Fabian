import logging
from distutils.log import debug
from itertools import combinations
from typing import Dict, List, Set

from lxml import etree
from wpdxf.wrapping.objects.resource import Resource

from flashextract.dsl.basic import learn
from flashextract.dsl.regions import WebRegion
from flashextract.dsl.webdsl import WebDSL
from flashextract.schema import SCHEMA, Field, parse_schema

# class FlashExtractReduction:
#     def reduce_ambiguity(self, resource: Resource):
#         out_matches = sorted(
#             resource.relative_xpaths().items(), key=lambda x: -len(x[1])
#         )
#         print(out_matches)


class ExtractionProgSynthesizer:
    def induce(self, resource: Resource, examples: list = None):
        schema = parse_schema("Seq([T] Struct(input: [I] str, output: [O] str))")
        print(schema)

        relative_xpaths = [
            val for vals in resource.relative_xpaths().values() for val in vals
        ]

        for wp in resource.webpages:
            document = wp.html

            regions1 = []
            for example in wp.examples.values():
                for inp, outs in example.items():
                    regions1.append(etree.tostring(inp).decode("utf-8"))
                    regions1.extend(
                        [*map(lambda x: etree.tostring(x).decode("utf-8"), outs)]
                    )
            # print(regions1)
            regions2 = []

            highlighting = {}
            _field = schema["T"]

            synthesize_field_extraction_prog(
                document, schema, highlighting, _field, regions1, []
            )
        # for xpath, wp in relative_xpaths:
        #     document = wp.html

        #     highlighting = ("T", [])
        #     _field = schema["T"]
        #     regions1 = (xpath.root_node, None)
        #     synthesize_field_extraction_prog(document, schema, highlighting, _field, regions1, [])

        #     highlighting = ("I", [])
        #     highlighting = ("O", [])


def synthesize_field_extraction_prog(
    document: str,
    schema: dict,
    highlighting: Dict[str, Set[str]],
    field: Field,
    regions1,
    regions2,
    dsl,
):
    regions1 = set(regions1)
    regions2 = set(regions2)
    print(regions1)
    for f in field.ancestors():
        f: Field
        if not f.is_materialized(highlighting) and f.name != "ALL":
            continue
        if f.name == "ALL":
            regions = [document]
        else:
            regions = highlighting[f.name]

        if f.is_seq_ancestor_of(field):
            ex = []

            for region in regions:
                subregions1 = {reg1 for reg1 in regions1 if reg1 in region}
                subregions2 = {reg2 for reg2 in regions2 if reg2 in region}

                subregions1 = sorted(subregions1, key=lambda x: x.position)
                subregions2 = sorted(subregions2, key=lambda x: x.position)

                if subregions1 or subregions2:
                    ex.append((region, subregions1, subregions2))
            progs = synthesize_seq_region_prog(ex, dsl)
        else:
            ex = []
            for region in regions:
                subregions1 = [reg1 for reg1 in regions1 if reg1 != region]

                if subregions1:
                    ex.append((region, subregions1))

            progs = synthesize_region_prog(ex, dsl)

        for i, prog in enumerate(progs):
            res = sorted(
                set.union(*map(lambda x: set(prog(x)), regions)),
                key=lambda x: x.position,
            )
            tmp_highlighting = {field.name: res}
            for key, values in highlighting.items():
                value_set = tmp_highlighting.get(key, set())
                value_set |= values
                tmp_highlighting[key] = value_set
            if is_consistent(tmp_highlighting, schema):
                return prog, tmp_highlighting
            return None, highlighting


def is_consistent(highlighting, schema):
    all_regions = [region for regions in highlighting.values() for region in regions]
    for i, r1 in enumerate(all_regions):
        for r2 in all_regions[i + 1 :]:
            if not (
                r2 in r1  # r2 nested inside r1
                or r1 in r2  # r1 nested inside r2
                or r1.disjunct(r2)  # r1 and r2 do not overlap
            ):
                return False
    for name1, regions1 in highlighting.items():
        field1 = schema[name1]
        for name2, regions2 in highlighting.items():
            field2 = schema[name2]
            if field1 == field2:
                continue
            # All regions of a field are nested inside their ancestors
            field1: Field
            if field1 in field2.ancestors():
                for r2 in regions2:
                    if not all(r1 in r2):
                        return False

            # All struct ancestors have at most one region
            if not field1.is_seq_ancestor_of(field2):
                for r1 in regions1:
                    all_r2 = [r2 for r2 in regions2 if r2 in r1]
                    if len(all_r2) > 1:
                        return False

            # "For every leaf field f in M , the value of any f-region in CR is of type f."
            # Not relevant, for now, as all values are treated as strings.

            return True


def synthesize_seq_region_prog(Q, dsl):
    _Q = [(R, R1) for R, R1, _ in Q]
    progs = learn(_Q, dsl.N1, num=1, do_cleanup=True)
    for p in progs:
        if all(not set(p(r)) & set(r2) for r, _, r2 in Q):
            yield p


def synthesize_region_prog(Q, dsl):
    raise NotImplementedError
    _Q = [(R, R1) for R, R1, _ in Q]
    return dsl.N2.learn()


if __name__ == "__main__":
    from lxml.etree import HTML

    _html = """
    <html>
      <body>
        <div key="T">
          <h1><div>Text: Input1 (this can be ignored)</div></h1>
          <div>Text: Output1</div>
        </div><div key="T">
          <h2><div>Text: Input2 (this can be ignored)</div></h2>
          <div>Txet: Output2</div>
        </div><div key="T">
          <h1><div>Text: Input3 (this can be ignored)</div></h1>
          <div>Text: Output3</div>
        </div>
      </body>
    </html>
    """
    html = HTML(_html)
    document = WebRegion(html)
    schema = parse_schema("Seq([T] Struct(input: [I] str, output: [O] str))")
    # schema = parse_schema("Seq([T] Struct (v: Seq([V] str)))")

    highlighting = {
        "T": {
            document.find_subregion("/html/body/div[1]"),
            document.find_subregion("/html/body/div[2]"),
            document.find_subregion("/html/body/div[3]"),
        }
    }

    _field = schema["I"]
    regions = []
    t = ("/html/body/div[1]/h1/div", "Input1")
    regions.append(document.find_subregion(*t))
    t = ("/html/body/div[2]/h2/div", "Input2")
    regions.append(document.find_subregion(*t))
    t = ("/html/body/div[3]/h1/div", "Input3")
    regions.append(document.find_subregion(*t))
    print(regions)

    P, highligth = synthesize_field_extraction_prog(
        document, schema, highlighting, _field, regions, [], dsl=WebDSL,
    )
    print(highligth)

    # _field = schema["I"]
    # regions = html.xpath("//div/text()")
    # regions = [WebRegion(r, (6, len(r))) for r in regions]
    # synthesize_field_extraction_prog(WebRegion(html), schema, {}, _field, regions, [])

    #     document = """\
    # Off Input: Input0 - Output: Output0
    # Off Input: Input1 - Output: Output1

    # Off Input: Input2 - Output: Output2
    # """
    #     document = TextRegion(document, 0)
    #     schema = parse_schema("Seq([T] Struct(input: [I] str, output: [O] str))")
    #     highlighting = {}
    #     _field = schema["T"]

    #     regions = []
    #     t = 'Input: Input0 - Output: Output0'
    #     regions.append(document.find_subregion(t))
    #     t = 'Input: Input1 - Output: Output1'
    #     regions.append(document.find_subregion(t))
    #     t = 'Input: Input2 - Output: Output2'
    #     regions.append(document.find_subregion(t))

    #     print(synthesize_field_extraction_prog(
    #         document, schema, highlighting, _field, regions, [], dsl=TextDSL,
    #     ))

    # document = TextRegion(" A\n B\n  C\n D\n", 0)
    # schema = parse_schema("Seq([T] Struct (v: Seq([V] str)))")
    # highlighting = {"T": {document[0:6], document[7:]}}
    # _field = schema["V"]

    # regions = []
    # t = "A"
    # regions.append(document.find_subregion(t))
    # t = "B"
    # regions.append(document.find_subregion(t))
    # t = "C"
    # regions.append(document.find_subregion(t))
    # t = "D"
    # regions.append(document.find_subregion(t))

    # print(
    #     synthesize_field_extraction_prog(
    #         document, schema, highlighting, _field, regions, [], dsl=TextDSL,
    #     )
    # )

    # document = TextRegion("A:name B:name  C:name D:name ", 0)
    # schema = parse_schema("Seq([T] Struct (i: [I] str, o: [O] str))")
    # highlighting = {"T": {document.find_subregion("A:name B:name "), document.find_subregion("C:name D:name ")}}
    # _field = schema["I"]

    # regions = []
    # t = "A"
    # regions.append(document.find_subregion(t))
    # # t = "B"
    # # regions.append(document.find_subregion(t))
    # t = "C"
    # regions.append(document.find_subregion(t))
    # # t = "D"
    # # regions.append(document.find_subregion(t))

    # P, highligth = synthesize_field_extraction_prog(
    #         document, schema, highlighting, _field, regions, [], dsl=TextDSL,
    #     )
    # print(highligth)
    # print(P(TextRegion("E:name F:name ",0)))

