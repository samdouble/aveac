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


class TestDownloadOperationRun:
    def test_run_calls_yt_dlp_with_correct_url(self, mocker: MockerFixture) -> None:
        mock_ydl = mocker.MagicMock()
        mock_ydl.__enter__ = mocker.MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = mocker.MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {"title": "Test Video"}
        mocker.patch("groove.operations.download.yt_dlp.YoutubeDL", return_value=mock_ydl)

        op = make_op()
        op.run()

        mock_ydl.extract_info.assert_called_once_with(str(op.url), download=False)
        mock_ydl.download.assert_called_once_with([str(op.url)])

    def test_run_uses_name_as_label_when_set(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_ydl = mocker.MagicMock()
        mock_ydl.__enter__ = mocker.MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = mocker.MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {"title": "Test Video"}
        mocker.patch("groove.operations.download.yt_dlp.YoutubeDL", return_value=mock_ydl)

        op = make_op(name="My Song", id="test-id")
        op.run()

        captured = capsys.readouterr()
        assert "My Song" in captured.out
