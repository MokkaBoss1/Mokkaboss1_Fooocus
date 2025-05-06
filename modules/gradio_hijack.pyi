
class Image(
    BaseImage,
    Editable,
    Clearable,
    Changeable,
    Streamable,
    Selectable,
    Uploadable,
    ImgSerializable,
    TokenInterpretable,
):
    """
    Creates an image component that can be used to upload/draw images (as an input) or display images (as an output).
    """
    def __init__(
        self,
        value: str | _PilImage | np.ndarray | None = None,
        *,
        shape: tuple[int, int] | None = None,
        height: int | None = None,
        width: int | None = None,
        object_fit: Literal["cover", "contain"] | None = None,
        image_mode: Literal[
            "1", "L", "P", "RGB", "RGBA", "CMYK", "YCbCr", "LAB", "HSV", "I", "F"
        ] = "RGB",
        invert_colors: bool = False,
        source: Literal["upload", "webcam", "canvas"] = "upload",
        tool: Literal["editor", "select", "sketch", "color-sketch"] | None = None,
        type: Literal["numpy", "pil", "filepath"] = "numpy",
        label: str | None = None,
        every: float | None = None,
        show_label: bool | None = None,
        show_download_button: bool = True,
        container: bool = True,
        scale: int | None = None,
        min_width: int = 160,
        interactive: bool | None = None,
        visible: bool = True,
        streaming: bool = False,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        mirror_webcam: bool = True,
        brush_radius: float | None = None,
        brush_color: str = "#000000",
        mask_opacity: float = 0.7,
        show_share_button: bool | None = None,
        **kwargs,
    ):
        # Save object_fit for get_config
        self.object_fit = object_fit

        # Core settings
        self.type = type
        self.shape = shape
        self.height = height
        self.width = width
        self.image_mode = image_mode
        self.invert_colors = invert_colors
        self.source = source
        self.tool = tool if tool is not None else ("sketch" if source == "canvas" else "editor")
        self.streaming = streaming
        self.show_download_button = show_download_button
        self.mirror_webcam = mirror_webcam
        self.brush_radius = brush_radius
        self.brush_color = brush_color
        self.mask_opacity = mask_opacity
        self.show_share_button = (
            (utils.get_space() is not None) if show_share_button is None else show_share_button
        )

        # Validations
        if self.type not in ["numpy", "pil", "filepath"]:
            raise ValueError(f"Invalid type: {self.type}")
        if self.source not in ["upload", "webcam", "canvas"]:
            raise ValueError(f"Invalid source: {self.source}")
        if self.streaming and self.source != "webcam":
            raise ValueError("Image streaming only available if source is 'webcam'.")

        # Note: DO NOT forward object_fit to super().__init__
        super().__init__(
            label=label,
            every=every,
            show_label=show_label,
            container=container,
            scale=scale,
            min_width=min_width,
            interactive=interactive,
            visible=visible,
            elem_id=elem_id,
            elem_classes=elem_classes,
            value=value,
            width=width,
            height=height,
            **kwargs,
        )
        TokenInterpretable.__init__(self)

    def get_config(self) -> dict[str, Any]:
        conf = {
            "image_mode": self.image_mode,
            "shape": self.shape,
            "height": self.height,
            "width": self.width,
            **({"object_fit": self.object_fit} if self.object_fit is not None else {}),
            "source": self.source,
            "tool": self.tool,
            "streaming": self.streaming,
            "mirror_webcam": self.mirror_webcam,
            "brush_radius": self.brush_radius,
            "brush_color": self.brush_color,
            "mask_opacity": self.mask_opacity,
            **({"show_share_button": self.show_share_button} if hasattr(self, "show_share_button") else {}),
            **({"show_download_button": self.show_download_button} if hasattr(self, "show_download_button") else {}),
        }
        conf.update(IOComponent.get_config(self))
        return conf



    @staticmethod
    def update(
        value: Any | Literal[_Keywords.NO_VALUE] | None = _Keywords.NO_VALUE,
        height: int | None = None,
        width: int | None = None,
        label: str | None = None,
        show_label: bool | None = None,
        show_download_button: bool | None = None,
        container: bool | None = None,
        scale: int | None = None,
        min_width: int | None = None,
        interactive: bool | None = None,
        visible: bool | None = None,
        brush_radius: float | None = None,
        brush_color: str | None = None,
        mask_opacity: float | None = None,
        show_share_button: bool | None = None,
    ):
        return {
            "height": height,
            "width": width,
            "label": label,
            "show_label": show_label,
            "show_download_button": show_download_button,
            "container": container,
            "scale": scale,
            "min_width": min_width,
            "interactive": interactive,
            "visible": visible,
            "value": value,
            "brush_radius": brush_radius,
            "brush_color": brush_color,
            "mask_opacity": mask_opacity,
            "show_share_button": show_share_button,
            "__type__": "update",
        }

    def _format_image(
        self, im: _Image.Image | None
    ) -> np.ndarray | _Image.Image | str | None:
        """Helper method to format an image based on self.type"""
        if im is None:
            return im
        fmt = im.format
        if self.type == "pil":
            return im
        elif self.type == "numpy":
            return np.array(im)
        elif self.type == "filepath":
            path = self.pil_to_temp_file(
                im, dir=self.DEFAULT_TEMP_DIR, format=fmt or "png"
            )
            self.temp_files.add(path)
            return path
        else:
            raise ValueError(
                "Unknown type: "
                + str(self.type)
                + ". Please choose from: 'numpy', 'pil', 'filepath'."
            )

    def style(self, *, height: str | int | None = None, width: str | int | None = None, object_fit: str | None = None, **kwargs):
            """
            Proxy to the underlying BaseImage.style so you can do
            .style(height='350px', object_fit='contain').
            """
            return super().style(height=height, width=width, object_fit=object_fit, **kwargs)
    from typing import Callable, Literal, Sequence, Any, TYPE_CHECKING
    from gradio.blocks import Block
    if TYPE_CHECKING:
        from gradio.components import Timer
        from gradio.components.base import Component

    