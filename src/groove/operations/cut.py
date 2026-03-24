from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

import ffmpeg
from pydantic import BaseModel, Field, field_validator, model_validator


def _parse_timestamp(value: str) -> float:
    parts = value.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(value)


class CutOperation(BaseModel):
    type: Literal["cut"]
    input: str
    start: Annotated[str, Field(description="Start timestamp (HH:MM:SS, MM:SS, or seconds)")]
    end: Annotated[str, Field(description="End timestamp (HH:MM:SS, MM:SS, or seconds)")]
    name: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))
    output: str | None = None

    @field_validator("start", "end")
    @classmethod
    def must_be_valid_timestamp(cls, v: str) -> str:
        try:
            _parse_timestamp(v)
        except ValueError as err:
            raise ValueError(
                f"Invalid timestamp: {v!r}. Expected HH:MM:SS, MM:SS, or seconds."
            ) from err
        return v

    @model_validator(mode="after")
    def end_must_be_after_start(self) -> "CutOperation":
        if _parse_timestamp(self.end) <= _parse_timestamp(self.start):
            raise ValueError(f"end ({self.end}) must be after start ({self.start})")
        return self

    def run(self, output_dir: Path) -> Path:
        input_path = Path(self.input)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        start_s = _parse_timestamp(self.start)
        end_s = _parse_timestamp(self.end)
        duration = end_s - start_s

        output_path = output_dir / f"{input_path.stem}_cut{input_path.suffix}"
        label = self.name or input_path.name
        print(f"[{self.id}] Cutting: {label} [{self.start} → {self.end}]")
        (
            ffmpeg.input(str(input_path), ss=start_s, t=duration)
            .output(str(output_path), c="copy")
            .overwrite_output()
            .run()
        )
        print(f"[{self.id}] Done → {output_path.name}")
        return output_path
