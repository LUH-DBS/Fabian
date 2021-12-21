from wrapping.objects.xpath.predicate import AttributePredicate, Conjunction, Disjunction, Predicate


def test_predicates():
    predicate0 = Predicate(left='position()')
    target = "position()"
    assert target == str(predicate0)

    predicate1 = Predicate(left='position()', comp=None, right=None)
    target = "position()"
    assert target == str(predicate1)

    assert predicate0 == predicate1

    predicate1 = Predicate(left='position()', comp=None, right=1)
    target = "1"
    assert target == str(predicate1)

    assert predicate0 != predicate1

    predicate0 = AttributePredicate(left='key')
    target = "@key"
    assert target == str(predicate0)

    predicate0 = AttributePredicate(left='key', right='value')
    target = '@key="value"'
    assert target == str(predicate0)

    conjunction = Conjunction([])
    target = ""
    assert target == str(conjunction)

    conjunction = Conjunction([Predicate(left="p0"), Predicate(left="p1")])
    target= "[p0][p1]"
    assert target == str(conjunction)

    disjunction = Disjunction([])
    target = ""
    assert target == str(disjunction)

    disjunction = Disjunction([Predicate(left="p0"), Predicate(left="p1")])
    target= "p0 or p1"
    assert target == str(disjunction)

    conjunction = Conjunction([Disjunction([Predicate("p0"), Predicate("p1")]), Predicate(left="p1")])
    target= "[p0 or p1][p1]"
    assert target == str(conjunction)