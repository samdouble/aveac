import subprocess
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _escape_concat_file_path(path: Path) -> str:
    return str(path.resolve()).replace("'", r"'\''")


class ConcatenateOperation(BaseModel):
    type: Literal["concatenate"]
    inputs: list[str]
    name: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))
    output: str | None = None

    @model_validator(mode="after")
    def must_have_at_least_two_inputs(self) -> "ConcatenateOperation":
        if len(self.inputs) < 2:
            raise ValueError("inputs must contain at least two files")
        return self

    def run(self, output_dir: Path) -> Path:
        input_paths = [Path(p) for p in self.inputs]
        for input_path in input_paths:
            if not input_path.exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")

        output_path = output_dir / f"{input_paths[0].stem}_concat{input_paths[0].suffix}"
        list_file_path = output_dir / f"{self.id}.txt"
        list_file_content = "".join(
            [f"file '{_escape_concat_file_path(path)}'\n" for path in input_paths]
        )
        list_file_path.write_text(list_file_content, encoding="utf-8")

        label = self.name or ", ".join([p.name for p in input_paths])
        print(f"[{self.id}] Concatenating: {label}")
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_file_path),
                    "-c",
                    "copy",
                    str(output_path),
                ],
                check=True,
            )
        finally:
            list_file_path.unlink(missing_ok=True)

        print(f"[{self.id}] Done → {output_path.name}")
        return output_path
