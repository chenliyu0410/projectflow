from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class ProjectScope(Strict):
    kind: Literal['project']
    project_id: str = Field(min_length=1, max_length=36)

class AllScope(Strict):
    kind: Literal['all_visible']

class TurnContext(Strict):
    question: str = Field(min_length=1, max_length=2000)
    query_id: str | None = Field(default=None, min_length=1, max_length=36)

class Ask(Strict):
    scope: ProjectScope | AllScope | None = None
    question: str = Field(min_length=1, max_length=2000)
    history: list[TurnContext] = Field(default_factory=list, max_length=6)
    project_id: str | None = Field(default=None, min_length=1, max_length=36)
    previous_question: str | None = Field(default=None, max_length=1000)

    @model_validator(mode='after')
    def validate_format(self):
        if not self.question.strip():
            raise ValueError('empty question')
        if self.scope is not None:
            if 'project_id' in self.model_fields_set or 'previous_question' in self.model_fields_set:
                raise ValueError('mixed formats')
        elif not self.project_id or 'history' in self.model_fields_set:
            raise ValueError('scope required')
        if sum(len(t.question) for t in self.history) > 6000:
            raise ValueError('history limit')
        return self

    def resolved_scope(self):
        return self.scope.model_dump() if self.scope else {'kind':'project', 'project_id':self.project_id}

class Revalidate(Strict):
    query_ids: list[str] = Field(max_length=100)
