"""Paging through Paperless's list endpoints."""

from typing import Annotated, Any, Self

from pydantic import BaseModel, Field

# Paperless numbers pages from 1 and answers page 0 with a 404.  It replaces a
# page size of 0 with its own default, so the reported page_size would be
# wrong.  The schema refuses both before a request is made.
PageNumber = Annotated[int, Field(ge=1)]
PageSize = Annotated[int, Field(ge=1)]


class Pagination(BaseModel):
    """The position of one page of results in the full result set."""

    total_count: int = Field(description="Total number of matching items")
    page: int = Field(description="The current page number, starting at 1")
    page_size: int = Field(description="Number of items requested per page")
    has_more: bool = Field(description="Whether another page of results exists")

    @classmethod
    def from_api(cls, data: dict[str, Any], page: int, page_size: int) -> Self:
        return cls(
            total_count=data["count"],
            page=page,
            page_size=page_size,
            has_more=data["next"] is not None,
        )
