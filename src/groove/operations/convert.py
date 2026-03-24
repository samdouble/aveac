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
    output: str | None = None

    def run(self, output_dir: Path) -> Path:
        input_path = Path(self.input)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        output_path = output_dir / input_path.with_suffix(f".{self.output_format}").name
        label = self.name or input_path.name
        print(f"[{self.id}] Converting: {label} -> {output_path.name}")
        (
            ffmpeg.input(str(input_path))
            .output(
                str(output_path),
                format=self.output_format,
                **{"b:a": self.audio_bitrate},
                vn=None,
            )
            .overwrite_output()
            .run()
        )
        print(f"[{self.id}] Done.")
        return output_path
