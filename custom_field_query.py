"""
Custom field queries: conditions on the values of documents' custom fields,
sent to Paperless as the JSON that its custom_field_query filter reads.

Paperless's grammar is a nested list.  An atom is [field, operator, value], and
["AND", [...]], ["OR", [...]], and ["NOT", atom] combine atoms.  These models
cover the atoms and one level of AND or OR.  They leave out NOT, nested groups,
and the date-part operators like "year__exact".

paperless-ngx validates a query in documents/filters.py, CustomFieldQueryParser.
It decides which operators a field's data type supports, and its error detail
reaches the model through the error middleware.
"""

import json
from typing import Annotated, Literal

from pydantic import BaseModel, Field

# Paperless refuses a query with more than this many atoms.
MAX_CONDITIONS = 20

FieldReference = Annotated[
    int | str,
    Field(description="The custom field's ID or exact name, from list_custom_fields"),
]
Scalar = str | int | float | bool


class Condition(BaseModel):
    """One atom of a custom field query: a field, an operator, and a value."""

    field: FieldReference
    operator: str
    value: object

    def to_paperless(self) -> list[object]:
        return [self.field, self.operator, self.value]


class ComparisonCondition(Condition):
    """Compares a custom field's value with one value."""

    operator: Literal[
        "exact", "gt", "gte", "lt", "lte", "icontains", "istartswith", "iendswith"
    ] = Field(
        description=(
            "exact: equal to the value, case-sensitive.  gt, gte, lt, lte: greater "
            "than, at least, less than, at most.  icontains, istartswith, "
            "iendswith: case-insensitive substring match"
        )
    )
    value: Scalar = Field(
        description=(
            'A date as "YYYY-MM-DD", a number, true or false, text, or a select '
            "option's id or label.  Compare a monetary field with a plain amount, "
            'like 100 or "12.50"'
        )
    )


class MembershipCondition(Condition):
    """Matches a custom field whose value is one of several values."""

    operator: Literal["in"]
    value: list[Scalar] = Field(
        min_length=1,
        description="The values to match, each in the form a comparison takes",
    )


class RangeCondition(Condition):
    """Matches a custom field whose value is between two bounds, inclusive."""

    operator: Literal["range"]
    value: list[str | int | float] = Field(
        min_length=2,
        max_length=2,
        description='The lower and upper bound, like ["2026-01-01", "2026-12-31"]',
    )


class PresenceCondition(Condition):
    """Matches on whether a document has a custom field, or a value for it."""

    operator: Literal["exists", "isnull"] = Field(
        description=(
            "exists: true matches documents that have the field, false matches "
            "documents without it.  isnull: true matches documents that have the "
            "field with no value set, and false matches documents that have a value "
            "for it"
        )
    )
    value: bool


class DocumentLinkCondition(Condition):
    """Matches a document link field that links to all of these documents."""

    operator: Literal["contains"]
    value: list[int] = Field(min_length=1, description="Document IDs")


CustomFieldCondition = Annotated[
    ComparisonCondition
    | MembershipCondition
    | RangeCondition
    | PresenceCondition
    | DocumentLinkCondition,
    Field(discriminator="operator"),
]


class CustomFieldQuery(BaseModel):
    """Conditions on documents' custom field values."""

    match: Literal["all", "any"] = Field(
        default="all",
        description=(
            "all: a document must meet every condition.  any: a document must "
            "meet at least one"
        ),
    )
    conditions: list[CustomFieldCondition] = Field(
        min_length=1, max_length=MAX_CONDITIONS
    )

    def to_paperless(self) -> str:
        combine = "AND" if self.match == "all" else "OR"
        atoms = [condition.to_paperless() for condition in self.conditions]
        return json.dumps([combine, atoms])
