import shutil
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field

from groove.ffmpeg_runtime import run_ffmpeg
from groove.operations.add_image import AddImageOperation
from groove.operations.add_text import AddTextOperation
from groove.operations.apply_filter import ApplyFilterOperation
from groove.operations.concatenate import ConcatenateOperation
from groove.operations.convert import ConvertOperation
from groove.operations.cut import CutOperation
from groove.operations.download import DownloadOperation
from groove.operations.extract_voice import ExtractVoiceOperation

CONFIG_PATH = "/app/config.yaml"

Operation = Annotated[
    AddImageOperation
    | AddTextOperation
    | ApplyFilterOperation
    | ConcatenateOperation
    | ConvertOperation
    | CutOperation
    | DownloadOperation
    | ExtractVoiceOperation,
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
    results_by_id: dict[str, Path] = {}
    for step in config.steps:
        if step.name:
            print(f"\n── Step: {step.name} ──")
        for op in step.operations:
            output_dir = Path(f"tmp/steps.{step.id}/operations.{op.id}")
            output_dir.mkdir(parents=True, exist_ok=True)
            if isinstance(op, (AddImageOperation, AddTextOperation)):
                resolved_input = op.resolve_input_path(results_by_id)
                result = run_ffmpeg(
                    op.build_invocation(output_dir=output_dir, input_path=resolved_input)
                )
            elif isinstance(op, ConcatenateOperation):
                resolved_inputs = op.resolve_input_paths(results_by_id)
                result = run_ffmpeg(
                    op.build_invocation(output_dir=output_dir, input_paths=resolved_inputs)
                )
            elif isinstance(op, (ApplyFilterOperation, ConvertOperation, CutOperation)):
                result = run_ffmpeg(op.build_invocation(output_dir=output_dir))
            else:
                result = op.run(output_dir=output_dir)
            results_by_id[op.id] = result
            print(f"[{op.id}] Done → {result.name}")
            if op.output is not None:
                dest = Path(op.output)
                if not dest.is_absolute():
                    dest = config.output_dir / dest
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(result, dest)
                print(f"  → copied to {dest}")


if __name__ == "__main__":
    main()
