from pathlib import Path
from typing import Literal
from uuid import uuid4

import ffmpeg
from pydantic import BaseModel, Field


class ConvertOperation(BaseModel):
    type: Literal["convert"]
    input: str
    name: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))
    output_format: Literal["mp3"] = "mp3"
    audio_bitrate: str = "192k"

    def run(self) -> None:
        input_path = Path(self.input)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        output_path = input_path.with_suffix(f".{self.output_format}")
        label = self.name or input_path.name
        print(f"[{self.id}] Converting: {label} -> {output_path.name}")
        (
            ffmpeg.input(str(input_path))
            .output(
                str(output_path),
                format=self.output_format,
                audio_bitrate=self.audio_bitrate,
                vn=None,
            )
            .overwrite_output()
            .run(quiet=True)
        )
        print(f"[{self.id}] Done.")
