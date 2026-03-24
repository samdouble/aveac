from typing import Annotated

import yaml
from pydantic import BaseModel, Field

from groove.operations.convert import ConvertOperation
from groove.operations.cut import CutOperation
from groove.operations.download import DownloadOperation

CONFIG_PATH = "/app/config.yaml"

Operation = Annotated[
    ConvertOperation | CutOperation | DownloadOperation,
    Field(discriminator="type"),
]


class Step(BaseModel):
    name: str | None = None
    operations: list[Operation]


class Config(BaseModel):
    steps: list[Step]


def load_config(path: str) -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return Config.model_validate(raw)


def main() -> None:
    config = load_config(CONFIG_PATH)
    for step in config.steps:
        if step.name:
            print(f"\n── Step: {step.name} ──")
        for op in step.operations:
            op.run()


if __name__ == "__main__":
    main()
