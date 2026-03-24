from pathlib import Path

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from groove.operations.download import DownloadOperation

URL = "https://www.youtube.com/watch?v=abc123"


def make_op(**kwargs: object) -> DownloadOperation:
    return DownloadOperation(type="download", url=URL, **kwargs)


class TestDownloadOperationValidation:
    def test_valid_youtube_com_url(self) -> None:
        op = make_op()
        assert "youtube.com" in str(op.url)

    def test_valid_youtu_be_url(self) -> None:
        op = DownloadOperation(type="download", url="https://youtu.be/abc123")
        assert "youtu.be" in str(op.url)

    def test_non_youtube_url_raises(self) -> None:
        with pytest.raises(ValidationError, match="YouTube"):
            DownloadOperation(type="download", url="https://vimeo.com/123")

    def test_invalid_url_raises(self) -> None:
        with pytest.raises(ValidationError):
            DownloadOperation(type="download", url="not-a-url")

    def test_id_is_auto_generated(self) -> None:
        op1 = make_op()
        op2 = make_op()
        assert op1.id != op2.id

    def test_explicit_id_is_preserved(self) -> None:
        op = make_op(id="my-id")
        assert op.id == "my-id"

    def test_name_defaults_to_none(self) -> None:
        op = make_op()
        assert op.name is None

    def test_explicit_name_is_preserved(self) -> None:
        op = make_op(name="My Video")
        assert op.name == "My Video"

    def test_output_defaults_to_none(self) -> None:
        op = make_op()
        assert op.output is None


class TestDownloadOperationRun:
    def _mock_ydl(self, mocker: MockerFixture, tmp_path: Path) -> object:
        downloaded_file = tmp_path / "video.mp4"
        downloaded_file.touch()
        mock_ydl = mocker.MagicMock()
        mock_ydl.__enter__ = mocker.MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = mocker.MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {
            "title": "Test Video",
            "requested_downloads": [{"filepath": str(downloaded_file)}],
        }
        mocker.patch("groove.operations.download.yt_dlp.YoutubeDL", return_value=mock_ydl)
        return mock_ydl

    def test_run_returns_downloaded_path(self, mocker: MockerFixture, tmp_path: Path) -> None:
        self._mock_ydl(mocker, tmp_path)
        op = make_op()
        result = op.run(output_dir=tmp_path)
        assert result == tmp_path / "video.mp4"

    def test_run_calls_extract_info_with_download(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mock_ydl = self._mock_ydl(mocker, tmp_path)
        op = make_op()
        op.run(output_dir=tmp_path)
        mock_ydl.extract_info.assert_called_once_with(str(op.url), download=True)

    def test_run_uses_name_as_label_when_set(
        self, mocker: MockerFixture, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._mock_ydl(mocker, tmp_path)
        op = make_op(name="My Song", id="test-id")
        op.run(output_dir=tmp_path)
        captured = capsys.readouterr()
        assert "My Song" in captured.out
