from pydantic import BaseModel


class OperationInputRef(BaseModel):
    id: str


OperationInput = str | OperationInputRef
