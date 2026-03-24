from typing import Annotated

import yaml
from pydantic import BaseModel, Field

from groove.operations.convert import ConvertOperation
from groove.operations.download import DownloadOperation

CONFIG_PATH = "/app/config.yaml"

Operation = Annotated[
    ConvertOperation | DownloadOperation,
    Field(discriminator="type"),
]


class Config(BaseModel):
    operations: list[Operation]


def load_config(path: str) -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return Config.model_validate(raw)


def main():
    config = load_config(CONFIG_PATH)
    for op in config.operations:
        op.run()


if __name__ == "__main__":
    main()
