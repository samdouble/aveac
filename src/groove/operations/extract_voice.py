from pathlib import Path
from typing import Literal
from uuid import uuid4

import librosa
import numpy as np
import soundfile as sf
from pydantic import BaseModel, Field


class ExtractVoiceOperation(BaseModel):
    type: Literal["extract_voice"]
    input: str
    target: Literal["vocals", "instrumental", "both"] = "vocals"
    margin_vocals: float = 10.0
    margin_instrumental: float = 2.0
    power: int = 2
    name: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))
    output: str | None = None

    def run(self, output_dir: Path) -> Path:
        input_path = Path(self.input)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        label = self.name or input_path.name
        print(f"[{self.id}] Extracting voice from: {label}")

        y, sr = librosa.load(str(input_path), mono=True)
        s_full, phase = librosa.magphase(librosa.stft(y))

        s_filter = librosa.decompose.nn_filter(
            s_full,
            aggregate=np.median,
            metric="cosine",
            width=int(librosa.time_to_frames(2, sr=sr)),
        )
        s_filter = np.minimum(s_full, s_filter)

        mask_instrumental = librosa.util.softmask(
            s_filter,
            self.margin_instrumental * (s_full - s_filter),
            power=self.power,
        )
        mask_vocals = librosa.util.softmask(
            s_full - s_filter,
            self.margin_vocals * s_filter,
            power=self.power,
        )

        stem = input_path.stem
        primary_path: Path | None = None

        if self.target in ("vocals", "both"):
            y_vocals = librosa.istft(mask_vocals * s_full * phase)
            vocals_path = output_dir / f"{stem}_vocals.wav"
            sf.write(str(vocals_path), y_vocals, sr)
            print(f"[{self.id}] Vocals → {vocals_path.name}")
            primary_path = vocals_path

        if self.target in ("instrumental", "both"):
            y_instrumental = librosa.istft(mask_instrumental * s_full * phase)
            instrumental_path = output_dir / f"{stem}_instrumental.wav"
            sf.write(str(instrumental_path), y_instrumental, sr)
            print(f"[{self.id}] Instrumental → {instrumental_path.name}")
            if primary_path is None:
                primary_path = instrumental_path

        print(f"[{self.id}] Done.")
        assert primary_path is not None
        return primary_path
