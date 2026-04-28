from pathlib import Path

import pytest
from pydantic import ValidationError

from groove.operations.add_image import AddImageOperation


def _make_op(tmp_path: Path, **kwargs: object) -> AddImageOperation:
    image = tmp_path / "overlay.png"
    image.touch()
    data: dict[str, object] = {
        "type": "add_image",
        "input": str(tmp_path / "in.mp4"),
        "image": str(image),
        "x": "10",
        "y": "20",
        "start": 1.0,
        "end": 3.0,
    }
    data.update(kwargs)
    return AddImageOperation.model_validate(data)


class TestAddImageOperationValidation:
    def test_end_after_start(self, tmp_path: Path) -> None:
        image = tmp_path / "overlay.png"
        image.touch()
        with pytest.raises(ValidationError):
            AddImageOperation(
                type="add_image",
                input=str(tmp_path / "i.mp4"),
                image=str(image),
                x="0",
                y="0",
                start=2.0,
                end=2.0,
            )

    def test_fade_values_non_negative(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            _make_op(tmp_path, fade_in=-0.1)
        with pytest.raises(ValidationError):
            _make_op(tmp_path, fade_out=-0.1)

    def test_total_fade_must_fit_in_time_window(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            _make_op(tmp_path, start=1.0, end=2.0, fade_in=0.7, fade_out=0.5)

    def test_id_is_auto_generated(self, tmp_path: Path) -> None:
        a = _make_op(tmp_path)
        b = _make_op(tmp_path)
        assert a.id != b.id

    def test_name_defaults_to_none(self, tmp_path: Path) -> None:
        op = _make_op(tmp_path)
        assert op.name is None


class TestAddImageOperationBuildInvocation:
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

    def test_raises_when_image_missing(self, tmp_path: Path) -> None:
        v = tmp_path / "v.mp4"
        v.touch()
        op = AddImageOperation(
            type="add_image",
            input=str(v),
            image="/nonexistent/overlay.png",
            x="0",
            y="0",
            start=0.0,
            end=1.0,
        )
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            op.build_invocation(tmp_path / "out")

    def test_build_invocation_contains_overlay_filter(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        v = tmp_path / "v.mp4"
        v.touch()
        out = tmp_path / "step_out"
        out.mkdir()
        op = _make_op(
            tmp_path,
            input=str(v),
            name="Clip",
            x="(W-w)/2",
            y="H*0.8",
            id="id1",
        )
        invocation = op.build_invocation(output_dir=out)
        cmd = invocation.command
        assert cmd[0] == "ffmpeg"
        assert "-loop" in cmd
        assert "-filter_complex" in cmd
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert "overlay=" in fc
        assert "enable=between(t\\,1.0\\,3.0)" in fc
        assert invocation.output_path == out / "v_addimage.mp4"
        captured = capsys.readouterr()
        assert "Clip" in captured.out

    def test_build_invocation_with_fade_adds_fade_filters(self, tmp_path: Path) -> None:
        v = tmp_path / "v.mp4"
        v.touch()
        out = tmp_path / "step_out"
        out.mkdir()
        op = _make_op(tmp_path, input=str(v), fade_in=0.5, fade_out=0.75)
        invocation = op.build_invocation(output_dir=out)
        fc = invocation.command[invocation.command.index("-filter_complex") + 1]
        assert "fade=t=in" in fc
        assert "fade=t=out" in fc
