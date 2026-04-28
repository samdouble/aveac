from pathlib import Path

import pytest
from pydantic import ValidationError

from groove.operations.add_text import AddTextOperation


def _make_op(tmp_path: Path, **kwargs: object) -> AddTextOperation:
    font = tmp_path / "f.ttf"
    font.touch()
    d: dict[str, object] = {
        "type": "add_text",
        "input": str(tmp_path / "in.mp4"),
        "text": "Hi",
        "fontfile": str(font),
        "x": "10",
        "y": "20",
        "start": 1.0,
        "end": 3.0,
    }
    d.update(kwargs)
    return AddTextOperation.model_validate(d)


class TestAddTextOperationValidation:
    def test_end_after_start(self, tmp_path: Path) -> None:
        font = tmp_path / "f.ttf"
        font.touch()
        with pytest.raises(ValidationError) as e:
            AddTextOperation(
                type="add_text",
                input=str(tmp_path / "i.mp4"),
                text="x",
                fontfile=str(font),
                x="0",
                y="0",
                start=2.0,
                end=2.0,
            )
        assert "end" in str(e.value).lower()

    def test_start_non_negative(self, tmp_path: Path) -> None:
        font = tmp_path / "f.ttf"
        font.touch()
        with pytest.raises(ValidationError):
            AddTextOperation(
                type="add_text",
                input=str(tmp_path / "i.mp4"),
                text="x",
                fontfile=str(font),
                x="0",
                y="0",
                start=-0.1,
                end=1.0,
            )

    def test_fade_values_non_negative(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            _make_op(tmp_path, fade_in=-0.1)
        with pytest.raises(ValidationError):
            _make_op(tmp_path, fade_out=-0.1)

    def test_total_fade_must_fit_in_time_window(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            _make_op(tmp_path, start=1.0, end=2.0, fade_in=0.7, fade_out=0.5)

    def test_text_single_line(self, tmp_path: Path) -> None:
        op = _make_op(tmp_path, text="one line")
        assert op.text == "one line"

    def test_text_rejects_newline(self, tmp_path: Path) -> None:
        font = tmp_path / "f.ttf"
        font.touch()
        with pytest.raises(ValidationError):
            AddTextOperation(
                type="add_text",
                input=str(tmp_path / "i.mp4"),
                text="a\nb",
                fontfile=str(font),
                x="0",
                y="0",
                start=0.0,
                end=1.0,
            )

    def test_id_is_auto_generated(self, tmp_path: Path) -> None:
        a = _make_op(tmp_path)
        b = _make_op(tmp_path)
        assert a.id != b.id

    def test_name_defaults_to_none(self, tmp_path: Path) -> None:
        op = _make_op(tmp_path)
        assert op.name is None


class TestAddTextOperationBuildInvocation:
    def test_raises_when_input_missing(self, tmp_path: Path) -> None:
        op = _make_op(tmp_path, input="/nonexistent/in.mp4")
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            op.build_invocation(tmp_path / "out")

    def test_resolve_input_path_uses_operation_results(self, tmp_path: Path) -> None:
        file_path = tmp_path / "resolved.mp4"
        file_path.touch()
        op = _make_op(tmp_path, input={"id": "intro"})
        resolved = op.resolve_input_path(results_by_id={"intro": file_path})
        assert resolved == file_path

    def test_resolve_input_path_raises_on_unknown_id(self, tmp_path: Path) -> None:
        op = _make_op(tmp_path, input={"id": "intro"})
        with pytest.raises(ValueError, match="Unknown operation id reference"):
            op.resolve_input_path(results_by_id={})

    def test_raises_when_font_missing(self, tmp_path: Path) -> None:
        v = tmp_path / "v.mp4"
        v.touch()
        op = AddTextOperation(
            type="add_text",
            input=str(v),
            text="x",
            fontfile="/nonexistent/font.ttf",
            x="0",
            y="0",
            start=0.0,
            end=1.0,
        )
        with pytest.raises(FileNotFoundError, match="Font file not found"):
            op.build_invocation(tmp_path / "out")

    def test_build_invocation_ffmpeg(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        v = tmp_path / "v.mp4"
        v.touch()
        out = tmp_path / "step_out"
        out.mkdir()
        op = _make_op(
            tmp_path, input=str(v), name="Clip", x="(w-text_w)/2", y="h*0.8", id="id1"
        )
        invocation = op.build_invocation(output_dir=out)
        call = invocation.command
        assert call[0] == "ffmpeg"
        assert "-vf" in call
        vf = call[call.index("-vf") + 1]
        assert "drawtext=" in vf
        assert "textfile=" in vf
        assert "enable=between(t\\,1.0\\,3.0)" in vf
        assert "fontfile=" in vf
        assert "fontsize=32" in vf
        assert "fontcolor=white" in vf
        assert "x=(w-text_w)/2" in vf
        assert "y=h*0.8" in vf
        assert "alpha=" not in vf
        assert invocation.output_path == out / "v_addtext.mp4"
        captured = capsys.readouterr()
        assert "Clip" in captured.out
        assert "Hi" in captured.out

    def test_build_invocation_with_fade_adds_alpha(self, tmp_path: Path) -> None:
        v = tmp_path / "v.mp4"
        v.touch()
        out = tmp_path / "step_out"
        out.mkdir()
        op = _make_op(tmp_path, input=str(v), fade_in=0.5, fade_out=0.75)
        invocation = op.build_invocation(output_dir=out)
        call = invocation.command
        vf = call[call.index("-vf") + 1]
        assert "alpha=" in vf
        assert "enable=between(t\\,1.0\\,3.0)" in vf

    def test_build_invocation_uses_builder_output(self, tmp_path: Path) -> None:
        v = tmp_path / "v.mp4"
        v.touch()
        out = tmp_path / "step_out"
        out.mkdir()
        op = _make_op(tmp_path, input=str(v), id="bld-id")

        invocation = op.build_invocation(output_dir=out)

        assert invocation.command[0] == "ffmpeg"
        assert invocation.output_path == out / "v_addtext.mp4"
        assert invocation.cleanup_paths == [out / "bld-id.txt"]
