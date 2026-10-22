import pytest
from pydantic import ValidationError
from app.rag.contracts import Ask

@pytest.mark.parametrize('value', [{}, {'scope': {}, 'question':'a'}, {'scope':{'kind':'all_visible'},'project_id':'p','question':'a'}, {'scope':{'kind':'all_visible'},'question':'a','history':[{'question':'a'}]*7}, {'scope':{'kind':'all_visible','acl':[]},'question':'a'}])
def test_invalid_contract(value):
    with pytest.raises(ValidationError): Ask.model_validate(value)

def test_both_supported_contracts():
    assert Ask(project_id='p', question='hi').resolved_scope() == {'kind':'project','project_id':'p'}
    assert Ask(scope={'kind':'all_visible'},question='hi').resolved_scope() == {'kind':'all_visible'}
