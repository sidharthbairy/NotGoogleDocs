from ot_engine.utils.apply_changeset import apply_changeset
from ot_engine.transformation import transform
from ot_engine.utils.constructors import changeset, retain, insert, delete


def test_baseball_example():
    doc = "baseball"

    # baseball -> basil
    a = changeset(
        base_length=len(doc),
        ops=[
            retain(2),
            insert("si"),
            delete(5),
            retain(1),
        ],
    )

    # baseball -> below
    #
    # Keep b
    # Insert e
    # Delete a s e b a
    # Keep first l
    # Delete second l
    # Insert ow
    b = changeset(
        base_length=len(doc),
        ops=[
            retain(1),
            insert("e"),
            delete(5),
            retain(1),
            delete(1),
            insert("ow"),
        ],
    )

    b_prime = transform(a, b, True)

    doc_after_a = apply_changeset(doc, a)
    final = apply_changeset(doc_after_a, b_prime)

    assert doc_after_a == "basil"
    assert final == "besiow"


def test_convergence_simple_insert_insert():
    doc = "abc"

    a = changeset(
        base_length=len(doc),
        ops=[
            retain(1),
            insert("X"),
            retain(2),
        ],
    )

    b = changeset(
        base_length=len(doc),
        ops=[
            retain(1),
            insert("Y"),
            retain(2),
        ],
    )

    b_prime = transform(a, b, True)
    a_prime = transform(b, a, False)

    doc_ab = apply_changeset(apply_changeset(doc, a), b_prime)
    doc_ba = apply_changeset(apply_changeset(doc, b), a_prime)

    assert doc_ab == doc_ba
    assert doc_ab == "aXYbc"
