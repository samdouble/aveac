import shutil
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field

from groove.operations.convert import ConvertOperation
from groove.operations.cut import CutOperation
from groove.operations.download import DownloadOperation
from groove.operations.extract_voice import ExtractVoiceOperation

CONFIG_PATH = "/app/config.yaml"

Operation = Annotated[
    ConvertOperation
    | CutOperation
    | DownloadOperation
    | ExtractVoiceOperation
    Field(discriminator="type"),
]


class Step(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str | None = None
    operations: list[Operation]


class Config(BaseModel):
    output_dir: Path = Path("/output")
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
            output_dir = Path(f"tmp/steps.{step.id}/operations.{op.id}")
            output_dir.mkdir(parents=True, exist_ok=True)
            result = op.run(output_dir=output_dir)
            if op.output is not None:
                dest = Path(op.output)
                if not dest.is_absolute():
                    dest = config.output_dir / dest
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(result, dest)
                print(f"  → copied to {dest}")


if __name__ == "__main__":
    main()
