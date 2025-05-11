import os
import gradio as gr
import math
import random
import string
import colorsys
import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageDraw
import requests
from io import BytesIO
import logging
import cv2
import json  # Ensure this is imported
import warnings

# Suppress Tornado/Uvicorn logs to avoid mixing with HTTP responses in console
for log_name in ("uvicorn.error", "uvicorn.access", "uvicorn"):
    logging.getLogger(log_name).setLevel(logging.WARNING)

warnings.filterwarnings(
    "ignore",
    message="torch.meshgrid: in an upcoming release, it will be required to pass the indexing argument",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r"You are using `torch.load` with `weights_only=False`",
    category=FutureWarning,
)




import json  # Ensure this is imported
import warnings
warnings.filterwarnings(
    "ignore",
    message="torch.meshgrid: in an upcoming release, it will be required to pass the indexing argument",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r"You are using `torch.load` with `weights_only=False`",
    category=FutureWarning,
)


# Allow duplicate OpenMP runtimes. Use with caution.
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"

# -----------------------------------------------------------------------------
# Load Server Setting from JSON (reuse from previous programs)
# -----------------------------------------------------------------------------
REMOTE_JSON_PATH = "remote_open.json"

# -----------------------------------------------------------------------------
# Shared Constants & Helpers
# -----------------------------------------------------------------------------
aspect_ratios = ["unchanged", "1:1", "2:3", "3:2", "4:3", "3:4", "16:9", "9:16",
                 "5:4", "4:5", "7:5", "5:7", "21:9"]


#####################################################################
CONFIG_FILENAME = "theme_config.json"
CONFIG_PATH     = os.path.join(os.path.dirname(__file__), CONFIG_FILENAME)

# List of allowed theme names
THEME_NAMES = [
    "Base",
    "Default",
    "Origin",
    "Citrus",
    "Monochrome",
    "Soft",
    "Glass",
    "Ocean"
]

DEFAULT_THEME = "Base"

try:
    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)
        theme_name = cfg.get("theme", DEFAULT_THEME)
except (FileNotFoundError, json.JSONDecodeError):
    theme_name = DEFAULT_THEME


# Instantiate theme object
theme = getattr(gr.themes, theme_name, gr.themes.Base)()
###############################################################


def random_filename(extension):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8)) + extension

# -----------------------------------
# Tab 1: Image Crop & Zoom Functions
# -----------------------------------
def main(input_img, aspect_ratio, exact_ratio, zoom, x_offset, y_offset,
         megapixels, out_border, in_border, border_color):
    if input_img is None:
        return None, 0, 0, 0.0, 0.0

    if aspect_ratio == "unchanged":
        target_ratio = input_img.width / input_img.height
    else:
        target_ratio = exact_ratio if exact_ratio > 0 else float(aspect_ratio.split(":")[0]) / float(aspect_ratio.split(":")[1])

    orig_width, orig_height = input_img.size
    if orig_width / orig_height > target_ratio:
        crop_height = orig_height
        crop_width = int(crop_height * target_ratio)
    else:
        crop_width = orig_width
        crop_height = int(crop_width / target_ratio)

    effective_crop_width = max(1, int(crop_width / zoom))
    effective_crop_height = max(1, int(crop_height / zoom))
    max_shift_x = crop_width - effective_crop_width
    max_shift_y = crop_height - effective_crop_height

    x_offset_pct = (x_offset + 100) / 200
    y_offset_pct = (y_offset + 100) / 200
    overall_left = int((x_offset + 100) / 200 * (input_img.width - crop_width))
    overall_top = int((y_offset + 100) / 200 * (input_img.height - crop_height))
    crop_left_within_region = int(x_offset_pct * max_shift_x)
    crop_top_within_region = int(y_offset_pct * max_shift_y)
    left = overall_left + crop_left_within_region
    top = overall_top + crop_top_within_region

    img = input_img.crop((left, top, left + effective_crop_width, top + effective_crop_height))
    img = img.resize((crop_width, crop_height), Image.Resampling.LANCZOS)

    if in_border > 0:
        draw = ImageDraw.Draw(img)
        for i in range(in_border):
            draw.rectangle((i, i, img.width - 1 - i, img.height - 1 - i), outline=border_color)

    if out_border > 0:
        img = ImageOps.expand(img, border=out_border, fill=border_color)

    if megapixels > 0:
        target_pixels = megapixels * 1e6
        current_pixels = img.width * img.height
        if current_pixels > target_pixels:
            scale = math.sqrt(target_pixels / current_pixels)
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)

    return img, img.width, img.height, img.width / img.height, (img.width * img.height) / 1e6

def save_crop_zoom_action(image, file_type, save_dir):
    if image:
        os.makedirs(save_dir, exist_ok=True)
        filename = random_filename(file_type)
        save_path = os.path.join(save_dir, filename)
        image.save(save_path, quality=95)
        return filename
    return "No image to save."

def load_image_from_url(url):
    response = requests.get(url)
    return Image.open(BytesIO(response.content))

# ----------------------------------------------
# Functions for Composition (Tab 2)
# ----------------------------------------------
def parse_aspect_ratio(aspect_ratio_str):
    try:
        w, h = aspect_ratio_str.split(":")
        return float(w.strip()) / float(h.strip())
    except Exception:
        return 1.0

def compute_dimensions_from_ratio_and_megapixels(ratio, megapixels):
    total_pixels = int(megapixels * 1_000_000)
    height = math.sqrt(total_pixels / ratio)
    width = ratio * height
    return int(round(width)), int(round(height))

def process_image(image, shrink_factor, horizontal_position, vertical_position, aspect_ratio_str, megapixels):
    if image is None:
        return None

    if aspect_ratio_str == "unchanged":
        ratio = image.width / image.height
    else:
        ratio = parse_aspect_ratio(aspect_ratio_str)

    if megapixels == 0:
        if image.width >= image.height:
            out_w = image.width
            out_h = int(round(image.width / ratio))
        else:
            out_h = image.height
            out_w = int(round(image.height * ratio))
    else:
        out_w, out_h = compute_dimensions_from_ratio_and_megapixels(ratio, megapixels)

    canvas = Image.new("RGB", (out_w, out_h), (0, 0, 0))
    scale_factor = 1 - (shrink_factor / 100.0)
    original_width, original_height = image.size
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)
    resample_method = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
    shrunken_image = image.resize((new_width, new_height), resample=resample_method)
    available_w = out_w - new_width
    available_h = out_h - new_height
    x_offset = int((available_w * horizontal_position) / 100.0)
    y_offset = int(available_h * (1 - vertical_position / 100.0))
    canvas.paste(shrunken_image, (x_offset, y_offset))
    return canvas

def save_image(image, file_type, save_folder):
    os.makedirs(save_folder, exist_ok=True)
    filename = ''.join(random.choices(string.ascii_letters + string.digits, k=8)) + file_type
    save_path = os.path.join(save_folder, filename)
    if file_type == ".jpg":
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(save_path, format="JPEG", quality=95)
    elif file_type == ".png":
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        image.save(save_path, format="PNG")
    else:
        image.save(save_path)
    return save_path, filename

def save_composition_action(image, file_type, save_dir):
    if image:
        _, filename = save_image(image, file_type, save_dir)
        return filename
    return "No image to save."

# -------------------------------------------
# Background Removal Function (Tab 3)
# -------------------------------------------
def remove_bg_from_image(image, torchscript_mode, threshold):
    from transparent_background import Remover
    if image is None:
        return None, None
    if image.mode != "RGB":
        image = image.convert("RGB")
    remover = Remover(jit=(torchscript_mode == "on"))
    rgba_image = remover.process(image, type="rgba", threshold=threshold)
    mask = rgba_image.getchannel("A")
    return rgba_image, mask

def compose_and_remove_bg(image, shrink_factor, horizontal_position, vertical_position,
                          aspect_ratio_str, megapixels, torchscript_mode, threshold):
    # first do the composition
    composed = process_image(image, shrink_factor, horizontal_position,
                             vertical_position, aspect_ratio_str, megapixels)
    # then remove the background from the composed result
    return remove_bg_from_image(composed, torchscript_mode, threshold)




# --------------------------------------
# Functions for Overlay Background (Tab 4)
# --------------------------------------
def process_images(subject_path, background_path, show_background, position, blur_enabled, blur_strength):
    subject = Image.open(subject_path).convert("RGBA")
    background = Image.open(background_path).convert("RGB")
    sub_width, sub_height = subject.size
    target_ratio = sub_width / sub_height
    bg_width, bg_height = background.size
    bg_ratio = bg_width / bg_height

    if math.isclose(bg_ratio, target_ratio, rel_tol=1e-3):
        cropped_bg = background.resize((sub_width, sub_height))
    else:
        if bg_ratio > target_ratio:
            new_width = int(bg_height * target_ratio)
            max_offset = bg_width - new_width
            left = max_offset * (position / 100)
            cropped_bg = background.crop((left, 0, left + new_width, bg_height))
        else:
            new_height = int(bg_width / target_ratio)
            max_offset = bg_height - new_height
            top = max_offset * (position / 100)
            cropped_bg = background.crop((0, top, bg_width, top + new_height))

    resized_bg = cropped_bg.resize((sub_width, sub_height))
    if blur_enabled and blur_strength > 0:
        resized_bg = resized_bg.filter(ImageFilter.GaussianBlur(radius=blur_strength))
    background_rgba = resized_bg.convert("RGBA")
    composite = Image.alpha_composite(background_rgba, subject)
    return resized_bg if show_background else composite

# -------------------------------------------
# Functions for Colour Background (Tab 5)
# -------------------------------------------
# ─── live-preview helper for solid colours ─────────────────────────────────────────
def update_solid_preview(hue, sat, lum):
    return f"""
    <div style=\"
        width:50px;
        height:50px;
        border:1px solid #000;
        background-color:hsl({hue},{sat}%,{lum}%);
    \"></div>
    """
def apply_background(
    image_path,
    background_type,
    hue, saturation, luminosity,
    top_hue, top_sat, top_lum,
    bottom_hue, bottom_sat, bottom_lum,
    generate_only=False,
    width=720,
    height=300
):
    """
    Generates a solid or gradient background. If generate_only is False and image_path is provided,
    it overlays the input image; otherwise returns just the background of given dimensions.
    """
    # Determine canvas size
    if generate_only or image_path is None:
        out_w, out_h = int(width), int(height)
    else:
        img = Image.open(image_path).convert("RGBA")
        out_w, out_h = img.size
    
    # Create background
    if background_type == "Solid Color":
        # Convert HSL to RGB
        h = hue / 360.0
        s = saturation / 100.0
        l = luminosity / 100.0
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        rgb = (int(r * 255), int(g * 255), int(b * 255), 255)
        background = Image.new("RGBA", (out_w, out_h), rgb)
    else:
        # Gradient
        def hsl_to_rgb_int(h_deg, s_pct, l_pct):
            h = h_deg / 360.0
            s = s_pct / 100.0
            l = l_pct / 100.0
            return tuple(int(255 * x) for x in colorsys.hls_to_rgb(h, l, s))

        top_rgb = hsl_to_rgb_int(top_hue, top_sat, top_lum)
        bottom_rgb = hsl_to_rgb_int(bottom_hue, bottom_sat, bottom_lum)
        # build gradient array
        y = np.linspace(0, 1, out_h)
        gradient = np.zeros((out_h, out_w, 4), dtype=np.uint8)
        for i in range(3):
            gradient[:, :, i] = np.outer((1 - y) * top_rgb[i] + y * bottom_rgb[i], np.ones(out_w))
        gradient[:, :, 3] = 255
        background = Image.fromarray(gradient, 'RGBA')

    # If generate_only, return background directly
    if generate_only or image_path is None:
        return background

    # Otherwise overlay the input image
    alpha = img.split()[-1]
    return Image.composite(img, background, alpha)
# -------------------------------------------
# Functions for Vignette (Tab 6)
# -------------------------------------------
def add_vignette_with_ui_params(
    img: np.ndarray,
    image_scale: float = 1.0,
    exposure: float = -2.372,
    hardness: float = 0.50,
    scale: float   = 0.28,
    shape: float   = 0.50,
    fill_grey: bool = False
) -> np.ndarray:
    if img is None:
        return None
    # 1) scale the input image
    if image_scale != 1.0:
        h0, w0 = img.shape[:2]
        new_w = max(1, int(w0 * image_scale))
        new_h = max(1, int(h0 * image_scale))
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    # 2) optional grey fill
    if fill_grey:
        grey_val = 0.5 * 255
        img = np.full_like(img, grey_val, dtype=np.uint8)
    h, w = img.shape[:2]
    # 3) normalized coordinate grid
    xs = np.linspace(-1, 1, w)
    ys = np.linspace(-1, 1, h)
    xv, yv = np.meshgrid(xs, ys)
    # 4) ellipse ratio from shape
    ratio = 10 ** (1 - 2 * shape)
    # 5) compute ellipse radii so that shape symmetric around circle
    if ratio >= 1.0:
        rx = scale
        ry = scale * ratio
    else:
        rx = scale / ratio
        ry = scale
    # 6) binary ellipse mask
    mask = ((xv / rx) ** 2 + (yv / ry) ** 2 <= 1.0).astype(np.float32)
    # 7) blur edge based on hardness
    max_dim = max(h, w)
    sigma = (1.0 - hardness) * (max_dim * 0.5)
    if hardness < 1.0:
        ksize = int(2 * np.ceil(2 * sigma) + 1)
        mask = cv2.GaussianBlur(mask, (ksize, ksize), sigmaX=sigma, sigmaY=sigma)
    # 8) apply exposure mapping
    exp_factor = 2.0 ** exposure
    mask_exp = exp_factor + mask * (1.0 - exp_factor)
    # 9) apply mask to image
    out = img.astype(np.float32)
    for c in range(3):
        out[..., c] *= mask_exp
    return np.clip(out, 0, 255).astype(np.uint8)

# --------------------------
# Gradio App UI
# --------------------------
with gr.Blocks(title="Image Processor", theme=theme, css=".gradio-container {max-width: 1400px}") as app:
    with gr.Tabs():
        # ---------------------------------------------------
        # Tab 1: Image Crop & Zoom
        # ---------------------------------------------------
        with gr.Tab("🖼️ Image Crop, Zoom and Resize App"):
            with gr.Row():
                with gr.Column(scale=10):
                    input_image = gr.Image(type="pil", label="Input Image", width=500, height=435)
                    image_url = gr.Textbox(label="Image URL")
                    load_url_button = gr.Button("Load Image from URL")
                with gr.Column(scale=20):
                    with gr.Row():
                        aspect_ratio = gr.Dropdown(aspect_ratios, value="unchanged", label="Aspect Ratio")
                        exact_aspect_ratio = gr.Number(0.0, label="Exact Aspect Ratio", precision=2)
                    zoom = gr.Slider(1.0, 6.0, 1.0, step=0.1, label="Zoom")
                    x_offset = gr.Slider(-100, 100, 0, step=1, label="X Offset (move subject left -> move subject right)")
                    y_offset = gr.Slider(-100, 100, 0, step=1, label="Y Offset (move subject down -> move subject up)")
                    with gr.Row():
                        outside_border = gr.Slider(0, 1000, 0, step=5, label="Outside Border")
                        inside_border = gr.Slider(0, 1000, 0, step=5, label="Inside Border")
                        border_color = gr.Dropdown(["white", "black"], value="white")
                    with gr.Row():
                        megapixels = gr.Slider(0.0, 10.0, 1.0, step=0.25, label="Megapixels")
                        file_type_crop = gr.Dropdown([".png", ".jpg", ".webp"], value=".png", label="File Type")
                    process_button_crop = gr.Button("Process Image", variant="primary")
                with gr.Column(scale=12):
                    processed_image_crop = gr.Image(type="pil", label="Output Image", interactive=False, width=500, height=205)
                    with gr.Row():
                        output_width = gr.Number(label="Width", interactive=False)
                        output_height = gr.Number(label="Height", interactive=False)
                    with gr.Row():
                        output_aspect_ratio = gr.Number(label="Aspect Ratio", interactive=False)
                        output_megapixels = gr.Number(label="Megapixels", interactive=False)
                    with gr.Row():
                        filename_display_crop = gr.Textbox(label="Filename", interactive=False)
                        save_dir_crop = gr.Textbox("D:\\imagecropandzoominterface", label="Save Directory")
                    save_button_crop = gr.Button("Save Image")
            process_button_crop.click(
                main,
                [input_image, aspect_ratio, exact_aspect_ratio, zoom, x_offset, y_offset,
                 megapixels, outside_border, inside_border, border_color],
                [processed_image_crop, output_width, output_height, output_aspect_ratio, output_megapixels]
            )
            save_button_crop.click(
                save_crop_zoom_action,
                [processed_image_crop, file_type_crop, save_dir_crop],
                filename_display_crop
            )
            load_url_button.click(load_image_from_url, inputs=image_url, outputs=input_image)

        # ---------------------------------------------------
        # Tab 2+3: Composition & Background Removal
        # ---------------------------------------------------
        with gr.Tab("✂️ Composition & Background Removal"):
            
            with gr.Row():
                with gr.Column(scale=12):
                    input_image_comp = gr.Image(type="pil", label="Input Image", height=300)
                    with gr.Accordion("✂️ Image Composition"):
                        # Composition inputs
                        with gr.Row():
                            shrink_factor = gr.Slider(0, 50, step=1, value=0, label="Shrink Factor (%)")
                            horizontal_position = gr.Slider(0, 100, step=1, value=50,
                                                            label="Horizontal Position (0=Left, 50=Center, 100=Right)")
                            vertical_position = gr.Slider(0, 100, step=1, value=50,
                                                          label="Vertical Position (0=Bottom, 50=Center, 100=Top)")
                        with gr.Row():
                            aspect_ratio_options_comp = [
                                "1:1", "2:3", "3:2", "4:3", "3:4", "16:9",
                                "9:16", "5:4", "4:5", "7:5", "5:7", "21:9", "unchanged"
                            ]
                            aspect_ratio_str_comp = gr.Dropdown(aspect_ratio_options_comp, value="unchanged",
                                                               label="Aspect Ratio")
                            megapixels_comp = gr.Slider(0, 8.0, step=0.1, value=0,
                                                        label="Megapixels (0 for natural size)")

                    with gr.Accordion("🔮 Background Removal Mode", open=False):
                    
                        bg_torchscript_mode = gr.Dropdown(
                            choices=["default", "on"],
                            value="on",
                            label="TorchScript JIT Mode",
                            info="Use 'on' for TorchScript JIT optimization"
                        )
                        bg_threshold = gr.Slider(
                            0.0, 1.0, step=0.01, value=0.5,
                            label="Background Removal Threshold",
                            info="Adjust sensitivity of background detection"
                        )

                    process_button = gr.Button("Process Image", variant="primary")

                with gr.Column(scale=12):
                    
                    bg_removed_output = gr.Image(type="pil", label="Background Removed Image", height=640)
                    with gr.Accordion("✂️ Output Mask", open=False):
                        mask_output = gr.Image(type="pil", label="Mask", height=300)

            process_button.click(
                compose_and_remove_bg,
                inputs=[
                    input_image_comp, shrink_factor, horizontal_position, vertical_position,
                    aspect_ratio_str_comp, megapixels_comp,
                    bg_torchscript_mode, bg_threshold
                ],
                outputs=[bg_removed_output, mask_output]
            )


        # ---------------------------------------------------
        # Tab 4: Overlay Background
        # ---------------------------------------------------
        with gr.Tab("🌆 Overlay Background"):
            with gr.Row():
                with gr.Column():
                    subject_img = gr.Image(type="filepath", label="Subject Image", image_mode="RGBA", height=300)
                    background_img = gr.Image(type="filepath", label="Background Image", image_mode="RGB", height=300)
                with gr.Column():
                    compositor_output = gr.Image(type="pil", label="Result", height=500)
                    with gr.Row():
                        position_slider = gr.Slider(0, 100, 50, label="Background Position")
                        show_bg_toggle = gr.Checkbox(label="Show Background Preview")
                        blur_toggle = gr.Checkbox(label="Enable Blur")
                        blur_strength = gr.Slider(0, 8, 0, step=0.1, visible=False)
            blur_toggle.change(lambda x: gr.update(visible=x), blur_toggle, blur_strength)
            components_overlay = [subject_img, background_img, show_bg_toggle, position_slider, blur_toggle, blur_strength]
            process_button_overlay = gr.Button("Process Image", variant="primary")
            process_button_overlay.click(
                process_images,
                inputs=components_overlay,
                outputs=compositor_output
            )

        # ---------------------------------------------------
        # Tab 5: Colour Background
        # ---------------------------------------------------
        with gr.Tab("🎨 Colour Background"):
            with gr.Row():
                bg_type = gr.Radio(
                    ["Solid Color", "Gradient Background"], value="Solid Color",
                    label="Background Type"
                )
                generate_only = gr.Checkbox(
                    label="Generate Background Only (skip overlay)", value=False
                )
            with gr.Row():
                with gr.Column():
                    input_img_color = gr.Image(
                        type="filepath", label="Input Image", image_mode="RGBA",
                        visible=True
                    )
                    width_input = gr.Number(
                        label="Width", value=813, interactive=True, visible=False
                    )
                    height_input = gr.Number(
                        label="Height", value=1216, interactive=True, visible=False
                    )
                    # Solid color controls
                    with gr.Group(visible=True) as solid_controls:
                        hue = gr.Slider(0, 360, 0, label="Hue")
                        sat = gr.Slider(0, 100, 100, label="Saturation")
                        lum = gr.Slider(0, 100, 50, label="Luminosity")
                        color_preview = gr.HTML(
                            update_solid_preview(0, 100, 50), label="Preview"
                        )
                    # Gradient controls
                    with gr.Group(visible=False) as gradient_controls:
                        with gr.Row():
                            # Top color
                            with gr.Column():
                                gr.Markdown("**Top Color**")
                                t_hue = gr.Slider(0, 360, 0, label="Top Hue")
                                t_sat = gr.Slider(0, 100, 100, label="Top Saturation")
                                t_lum = gr.Slider(0, 100, 50, label="Top Luminosity")
                                top_preview = gr.HTML(
                                    update_solid_preview(0, 100, 50), label="Top Preview"
                                )
                            # Bottom color
                            with gr.Column():
                                gr.Markdown("**Bottom Color**")
                                b_hue = gr.Slider(0, 360, 120, label="Bottom Hue")
                                b_sat = gr.Slider(0, 100, 100, label="Bottom Saturation")
                                b_lum = gr.Slider(0, 100, 50, label="Bottom Luminosity")
                                bottom_preview = gr.HTML(
                                    update_solid_preview(120, 100, 50), label="Bottom Preview"
                                )
                with gr.Column():
                    output_img_color = gr.Image(type="pil", label="Result", height=550)
                    process_button_color = gr.Button("Process Image", variant="primary")

            # Show/hide input vs size fields based on generate_only
            generate_only.change(
                lambda gen: (
                    gr.update(visible=not gen),  # input image
                    gr.update(visible=gen),       # width input
                    gr.update(visible=gen)        # height input
                ),
                generate_only,
                [input_img_color, width_input, height_input]
            )

            # Toggle solid vs gradient controls
            bg_type.change(
                lambda x: (
                    gr.update(visible=x == "Solid Color"),
                    gr.update(visible=x == "Gradient Background")
                ),
                bg_type,
                [solid_controls, gradient_controls]
            )

            # Update previews
            for slider in (hue, sat, lum):
                slider.change(update_solid_preview, [hue, sat, lum], color_preview)
            for (s_grp, preview) in ([(t_hue, t_sat, t_lum), top_preview], [(b_hue, b_sat, b_lum), bottom_preview]):
                for s in s_grp:
                    s.change(update_solid_preview, list(s_grp), preview)

            # Final processing
            process_button_color.click(
                apply_background,
                inputs=[
                    input_img_color, bg_type,
                    hue, sat, lum,
                    t_hue, t_sat, t_lum,
                    b_hue, b_sat, b_lum,
                    generate_only, width_input, height_input
                ],
                outputs=output_img_color
            )

        ############################
        # last tab vignette
        ############################

        with gr.Tab("🎥 Vignette Generator"):
            with gr.Row():
                with gr.Column(scale=10):
                    input_img_vig = gr.Image(type="numpy", label="Input Image", height=500)
                with gr.Column(scale=10):
                    img_scale_slider = gr.Slider(0.1, 1.0, 1.0, step=0.01, label="Image Scale (10%–100%)")
                    exp_slider = gr.Slider(-2.5, 0.0, -1.7, step=0.01, label="Exposure (stops)")
                    hard_slider = gr.Slider(0.4, 1.0, 0.65, step=0.01, label="Hardness (0=blur,1=hard edge)")
                    scale_slider = gr.Slider(0.0, 1.0, 0.60, step=0.01, label="Vignette Scale")
                    shape_slider = gr.Slider(0.25, 0.75, 0.50, step=0.01, label="Shape (0=tall ellipse,0.5=circle,1=wide ellipse)")
                    fill_checkbox = gr.Checkbox(label="Fill with 50% grey", value=False)
                    process_btn_vig = gr.Button("Process Vignette", variant="primary")
                with gr.Column(scale=10):
                    output_img_vig = gr.Image(type="numpy", label="Vignette Result", height=500)

            process_btn_vig.click(
                fn=add_vignette_with_ui_params,
                inputs=[
                    input_img_vig,
                    img_scale_slider,
                    exp_slider,
                    hard_slider,
                    scale_slider,
                    shape_slider,
                    fill_checkbox
                ],
                outputs=[output_img_vig]
            )






if __name__ == "__main__":
    server_name = "127.0.0.1"
    app.launch(
        server_name=server_name,
        server_port=7861,
        share=False,
        inbrowser=True
    )
