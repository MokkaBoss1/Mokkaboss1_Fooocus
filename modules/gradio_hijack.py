from __future__ import annotations
"""gr.Image() component."""

import warnings
from pathlib import Path
from typing import Any, Literal

import numpy as np
import PIL
import PIL.ImageOps
import gradio.routes
import importlib

from gradio_client import utils as client_utils
from gradio_client.documentation import document, set_documentation_group
from gradio_client.serializing import ImgSerializable
from PIL import Image as _Image  # using _ to minimize namespace pollution

from gradio import processing_utils, utils, Error

from gradio.components.base import Component as IOComponent, _Keywords
from gradio.components import Image as BaseImage
from gradio.blocks import Block

import numpy as _np
from PIL import Image as _PilImage, ImageOps
import gradio as gr
import gradio.processing_utils as processing_utils
import warnings

import PIL.Image as _PilImageModule
from PIL.Image import Image as _PilImageClass

# ----------------------------------------------------------------------------
# GRADIO 5.x COMPATIBILITY: ensure every IOComponent has an api_info() stub
if not hasattr(IOComponent, "api_info"):
    def api_info(self):
        return {}
    IOComponent.api_info = api_info
# ----------------------------------------------------------------------------

# warn_style stub
try:
    from gradio.deprecation import warn_style_method_deprecation
except ImportError:
    def warn_style_method_deprecation(component, method_name):
        pass

# TokenInterpretable stub
try:
    from gradio.interpretation import TokenInterpretable
except ImportError:
    class TokenInterpretable: pass

# Event-mixins stub
try:
    from gradio.events import (
        Changeable, Clearable, Editable,
        EventListenerMethod, Selectable,
        Streamable, Uploadable,
    )
except ImportError:
    class Changeable: pass
    class Clearable: pass
    class Editable: pass
    class Selectable: pass
    class Streamable: pass
    class Uploadable: pass

    class EventListenerMethod:
        def __init__(self, event_name: str):
            self._event_name = event_name
        def __get__(self, instance, owner):
            # no-op so .change/.upload exist without error
            return lambda *args, **kwargs: None

# ----------------------------------------------------------------------------
# MONKEY-PATCH: restore .change()/.upload() on Gradio Image components
from gradio.components import Image as GrImage
GrImage.change = EventListenerMethod("change")
GrImage.upload = EventListenerMethod("upload")
# alias our hijacked Image
Image = GrImage
# ----------------------------------------------------------------------------

# …now your original full implementation exactly as you pasted it…


@document()
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

def preprocess(self, x):
    """
    Handles:
      • None
      • str (data URL or filepath)
      • dict {"image":…, "mask":…}
      • np.ndarray
      • PIL.Image.Image
    Returns np.ndarray, PIL.Image.Image, or {"image":…, "mask":…}.
    """
    if x is None:
        return None

    # 1) Unpack sketch dict if present
    mask_data = None
    if (
        self.tool == "sketch"
        and self.source in ["upload", "webcam"]
        and isinstance(x, dict)
    ):
        mask_data = x.get("mask")
        x = x.get("image")

    # 2) Normalize to PIL.Image.Image
    if isinstance(x, _np.ndarray):
        im = _PilImageClass.fromarray(x)
    elif isinstance(x, _PilImageClass):
        im = x
    elif isinstance(x, str):
        if x.startswith("data:"):
            try:
                im = processing_utils.decode_base64_to_image(x)
            except Exception:
                raise gr.Error("Unsupported image type in input")
        else:
            im = _PilImageModule.open(x)
    else:
        raise gr.Error(f"Unsupported input type: {type(x)}")

    # 3) Apply Fooocus transforms
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        im = im.convert(self.image_mode)

    if self.shape is not None:
        im = processing_utils.resize_and_crop(im, self.shape)

    if self.invert_colors:
        im = ImageOps.invert(im)

    if (
        self.source == "webcam"
        and getattr(self, "mirror_webcam", False)
        and self.tool != "color-sketch"
    ):
        im = ImageOps.mirror(im)

    # 4) Format main image
    formatted_im = self._format_image(im)

    # 5) Decode & format mask if provided
    if mask_data is not None:
        if isinstance(mask_data, _np.ndarray):
            mask_im = _PilImageClass.fromarray(mask_data)
        elif isinstance(mask_data, _PilImageClass):
            mask_im = mask_data
        elif isinstance(mask_data, str):
            if mask_data.startswith("data:"):
                mask_im = processing_utils.decode_base64_to_image(mask_data)
            else:
                mask_im = _PilImageModule.open(mask_data)
        else:
            mask_im = None

        if mask_im is not None and mask_im.mode == "RGBA":
            alpha = mask_im.getchannel("A").convert("L")
            mask_im = _PilImageModule.merge("RGB", [alpha, alpha, alpha])

        formatted_mask = self._format_image(mask_im) if mask_im is not None else None
        return {"image": formatted_im, "mask": formatted_mask}

    # 6) No mask: return single image
    return formatted_im




def postprocess(
    self, y: np.ndarray | _Image.Image | str | Path | None
) -> str | None:
    """
    Parameters:
        y: image as a numpy array, PIL Image, string/Path filepath, or string URL
    Returns:
        base64 url data
    """
    if y is None:
        return None
    if isinstance(y, np.ndarray):
        # numpy → base64
        return image_utils.encode_image_array_to_base64(y)              # :contentReference[oaicite:0]{index=0}
    elif isinstance(y, _Image.Image):
        # PIL Image → base64
        return image_utils.encode_image_to_base64(y)                    # :contentReference[oaicite:1]{index=1}
    elif isinstance(y, (str, Path)):
        # file path or URL → base64
        return client_utils.encode_url_or_file_to_base64(y)            # :contentReference[oaicite:2]{index=2}
    else:
        raise ValueError(f"Cannot process this value as an Image: {type(y)}")

    def set_interpret_parameters(self, segments: int = 16):
        """…"""
        self.interpretation_segments = segments
        return self

    def _segment_by_slic(self, x):
        """…"""
        x = processing_utils.decode_base64_to_image(x)
        if self.shape is not None:
            x = processing_utils.resize_and_crop(x, self.shape)
        resized_and_cropped_image = np.array(x)
        try:
            from skimage.segmentation import slic
        except (ImportError, ModuleNotFoundError) as err:
            raise ValueError(
                "Error: running this interpretation for images requires scikit-image, please install it first."
            ) from err
        try:
            segments_slic = slic(
                resized_and_cropped_image,
                self.interpretation_segments,
                compactness=10,
                sigma=1,
                start_label=1,
            )
        except TypeError:  # For skimage 0.16 and older
            segments_slic = slic(
                resized_and_cropped_image,
                self.interpretation_segments,
                compactness=10,
                sigma=1,
            )
        return segments_slic, resized_and_cropped_image

    def tokenize(self, x):
        """…"""
        segments_slic, resized_and_cropped_image = self._segment_by_slic(x)
        tokens, masks, leave_one_out_tokens = [], [], []
        replace_color = np.mean(resized_and_cropped_image, axis=(0, 1))
        for segment_value in np.unique(segments_slic):
            mask = segments_slic == segment_value
            image_screen = np.copy(resized_and_cropped_image)
            image_screen[segments_slic == segment_value] = replace_color
            leave_one_out_tokens.append(
                processing_utils.encode_array_to_base64(image_screen)
            )
            token = np.copy(resized_and_cropped_image)
            token[segments_slic != segment_value] = 0
            tokens.append(token)
            masks.append(mask)
        return tokens, leave_one_out_tokens, masks

    def get_masked_inputs(self, tokens, binary_mask_matrix):
        """…"""
        masked_inputs = []
        for binary_mask_vector in binary_mask_matrix:
            masked_input = np.zeros_like(tokens[0], dtype=int)
            for token, b in zip(tokens, binary_mask_vector):
                masked_input = masked_input + token * int(b)
            masked_inputs.append(processing_utils.encode_array_to_base64(masked_input))
        return masked_inputs

    def get_interpretation_scores(
        self, x, neighbors, scores, masks, tokens=None, **kwargs
    ) -> list[list[float]]:
        """…"""
        x = processing_utils.decode_base64_to_image(x)
        if self.shape is not None:
            x = processing_utils.resize_and_crop(x, self.shape)
        x = np.array(x)
        output_scores = np.zeros((x.shape[0], x.shape[1]))
        for score, mask in zip(scores, masks):
            output_scores += score * mask
        max_val, min_val = np.max(output_scores), np.min(output_scores)
        if max_val > 0:
            output_scores = (output_scores - min_val) / (max_val - min_val)
        return output_scores.tolist()

    def style(self, *, height: int | None = None, width: int | None = None, **kwargs):
        """…"""
        warn_style_method_deprecation()
        if height is not None:
            self.height = height
        if width is not None:
            self.width = width
        return self

    def check_streamable(self):
        if self.source != "webcam":
            raise ValueError("Image streaming only available if source is 'webcam'.")

    def as_example(self, input_data: str | None) -> str:
        if input_data is None:
            return ""
        elif self.root_url:
            return input_data
        return str(utils.abspath(input_data))


# bottom-of-file scaffolding, unchanged
all_components = []

if not hasattr(Block, 'original__init__'):
    Block.original_init = Block.__init__

def blk_ini(self, *args, **kwargs):
    all_components.append(self)
    return Block.original_init(self, *args, **kwargs)

Block.__init__ = blk_ini

gradio.routes.asyncio = importlib.reload(gradio.routes.asyncio)

if not hasattr(gradio.routes.asyncio, 'original_wait_for'):
    gradio.routes.asyncio.original_wait_for = gradio.routes.asyncio.wait_for

def patched_wait_for(fut, timeout):
    del timeout
    return gradio.routes.asyncio.original_wait_for(fut, timeout=65535)

gradio.routes.asyncio.wait_for = patched_wait_for
