import os
import time
from pathlib import Path
from typing import Literal
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field, model_validator

UPLOAD_URL = "https://sunoapiorg.redpandaai.co/api/file-stream-upload"
EXTEND_URL = "https://api.sunoapi.org/api/v1/generate/upload-extend"
POLL_URL = "https://api.sunoapi.org/api/v1/generate/record-info"

TERMINAL_STATUSES = {
    "SUCCESS",
    "CREATE_TASK_FAILED",
    "GENERATE_AUDIO_FAILED",
    "SENSITIVE_WORD_ERROR",
}


class SunoExtendOperation(BaseModel):
    type: Literal["suno_extend"]
    input: str
    model: Literal["V4", "V4_5", "V4_5PLUS", "V4_5ALL", "V5"] = "V4_5"
    default_param_flag: bool = False
    instrumental: bool = True
    prompt: str | None = None
    style: str | None = None
    title: str | None = None
    continue_at: float | None = None
    name: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))
    output: str | None = None
    poll_interval: float = 5.0
    poll_timeout: float = 300.0

    @model_validator(mode="after")
    def validate_custom_params(self) -> "SunoExtendOperation":
        if self.default_param_flag:
            if self.style is None:
                raise ValueError("style is required when default_param_flag is True")
            if self.title is None:
                raise ValueError("title is required when default_param_flag is True")
            if not self.instrumental and self.prompt is None:
                raise ValueError(
                    "prompt is required when default_param_flag is True and instrumental is False"
                )
        return self

    def _api_key(self) -> str:
        key = os.environ.get("SUNO_API_KEY")
        if not key:
            raise RuntimeError("SUNO_API_KEY environment variable is not set")
        return key

    def _upload_file(self, client: httpx.Client, input_path: Path) -> str:
        print(f"[{self.id}] Uploading {input_path.name}...")
        with open(input_path, "rb") as f:
            response = client.post(
                UPLOAD_URL,
                files={"file": (input_path.name, f)},
                data={"uploadPath": "groove-on-a-real-train"},
            )
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            raise RuntimeError(f"File upload failed: {data.get('msg')}")
        return str(data["data"]["downloadUrl"])

    def _submit_extend(self, client: httpx.Client, upload_url: str) -> str:
        payload: dict[str, object] = {
            "uploadUrl": upload_url,
            "defaultParamFlag": self.default_param_flag,
            "model": self.model,
            "instrumental": self.instrumental,
            "callBackUrl": "https://placeholder.example.com/callback",
        }
        if self.prompt is not None:
            payload["prompt"] = self.prompt
        if self.style is not None:
            payload["style"] = self.style
        if self.title is not None:
            payload["title"] = self.title
        if self.continue_at is not None:
            payload["continueAt"] = self.continue_at

        print(f"[{self.id}] Submitting extend task (model={self.model})...")
        response = client.post(EXTEND_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 200:
            raise RuntimeError(f"Extend request failed: {data.get('msg')}")
        task_id: str = str(data["data"]["taskId"])
        print(f"[{self.id}] Task created: {task_id}")
        return task_id

    def _poll(self, client: httpx.Client, task_id: str) -> list[dict[str, object]]:
        deadline = time.time() + self.poll_timeout
        while time.time() < deadline:
            response = client.get(POLL_URL, params={"taskId": task_id})
            response.raise_for_status()
            data = response.json()
            status: str = data["data"]["status"]
            print(f"[{self.id}] Status: {status}")
            if status == "SUCCESS":
                suno_data: list[dict[str, object]] = data["data"]["response"]["sunoData"]
                return suno_data
            if status in TERMINAL_STATUSES:
                raise RuntimeError(
                    f"Task {task_id} failed with status {status}: "
                    f"{data['data'].get('errorMessage')}"
                )
            time.sleep(self.poll_interval)
        raise TimeoutError(f"Task {task_id} did not complete within {self.poll_timeout}s")

    def _download(self, client: httpx.Client, audio_url: str, output_dir: Path) -> Path:
        filename = audio_url.split("?")[0].split("/")[-1]
        if not filename.endswith(".mp3"):
            filename = f"{Path(self.input).stem}_extended.mp3"
        output_path = output_dir / filename
        print(f"[{self.id}] Downloading result → {output_path.name}")
        with client.stream("GET", audio_url) as response:
            response.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        return output_path

    def run(self, output_dir: Path) -> Path:
        input_path = Path(self.input)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        label = self.name or input_path.name
        print(f"[{self.id}] SunoExtend: {label}")

        headers = {"Authorization": f"Bearer {self._api_key()}"}
        with httpx.Client(headers=headers, timeout=60.0) as client:
            upload_url = self._upload_file(client, input_path)
            task_id = self._submit_extend(client, upload_url)
            suno_data = self._poll(client, task_id)
            audio_url = str(suno_data[0]["audioUrl"])
            output_path = self._download(client, audio_url, output_dir)

        print(f"[{self.id}] Done.")
        return output_path
