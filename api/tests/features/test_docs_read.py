"""@api BDD — binds the docs_read.feature scenarios at the Gateway (TestClient),
validating the architected invariants, not evolving a design."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from scree.access.authority import Authority
from scree.gateway.app import create_app
from scree.knowledge.models import Doc
from scree.knowledge.store import DocStore

scenarios("docs_read.feature")


@pytest.fixture
def world() -> dict:
    return {"docs": [], "readable": {}, "response": None}


@pytest.fixture
def client(world) -> TestClient:
    return TestClient(create_app(DocStore(world["docs"]), Authority(world["readable"]), allow_insecure_header_auth=True))


@given(parsers.parse('doc "{doc_id}" in space "{space}"'))
def add_doc(world, doc_id, space):
    world["docs"].append(Doc(id=doc_id, title=doc_id, space=space, body=f"body of {doc_id}"))


@given(parsers.parse('"{principal}" can read space "{space}"'))
def grant(world, principal, space):
    world["readable"].setdefault(principal, set()).add(space)


@when(parsers.parse('"{principal}" lists docs'))
def list_docs(world, client, principal):
    world["response"] = client.get("/docs", headers={"X-Spike-User": principal})


@when(parsers.parse('"{principal}" reads doc "{doc_id}"'))
def read_doc(world, client, principal, doc_id):
    world["response"] = client.get(f"/docs/{doc_id}", headers={"X-Spike-User": principal})


@then(parsers.parse('the results include "{doc_id}"'))
def results_include(world, doc_id):
    assert doc_id in [d["id"] for d in world["response"].json()]


@then(parsers.parse('the results exclude "{doc_id}"'))
def results_exclude(world, doc_id):
    assert doc_id not in [d["id"] for d in world["response"].json()]


@then(parsers.parse("the response status is {status:d}"))
def check_status(world, status):
    assert world["response"].status_code == status


@then(parsers.parse('the returned doc id is "{doc_id}"'))
def returned_id(world, doc_id):
    assert world["response"].json()["id"] == doc_id
