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
def apply_background(image_path, background_type, hue, saturation, luminosity,
                     top_hue, top_sat, top_lum, bottom_hue, bottom_sat, bottom_lum):
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    alpha = img.split()[-1]

    if background_type == "Solid Color":
        h = hue / 360.0
        s = saturation / 100.0
        l = luminosity / 100.0
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        r, g, b = int(r * 255), int(g * 255), int(b * 255)
        background = Image.new("RGBA", (width, height), (r, g, b, 255))
    else:
        def hsl_to_rgb(h, s, l):
            h /= 360.0
            s /= 100.0
            l /= 100.0
            return tuple(int(255 * x) for x in colorsys.hls_to_rgb(h, l, s))

        top_rgb = hsl_to_rgb(top_hue, top_sat, top_lum)
        bottom_rgb = hsl_to_rgb(bottom_hue, bottom_sat, bottom_lum)
        y = np.linspace(0, 1, height)
        gradient = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(3):
            gradient[:, :, i] = np.outer((1 - y) * top_rgb[i] + y * bottom_rgb[i],
                                         np.ones(width))
        background = Image.fromarray(gradient, 'RGB').convert('RGBA')

    return Image.composite(img, background, alpha)

# --------------------------
# Gradio App UI
# --------------------------
with gr.Blocks(title="Ultimate Image Processor", css=".gradio-container {max-width: 1400px}") as app:
    with gr.Tabs():
        # ---------------------------------------------------
        # Tab 1: Image Crop & Zoom
        # ---------------------------------------------------
        with gr.Tab("🖼️ Image Crop & Zoom"):
            gr.Markdown("# 🖼️ Image Crop, Zoom and Resize App")
            with gr.Row():
                with gr.Column(scale=10):
                    input_image = gr.Image(type="pil", label="Input Image", width=500, height=440)
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
                    process_button_crop = gr.Button("Process Image")
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
        # Tab 2: Image Composition
        # ---------------------------------------------------
        with gr.Tab("✂️ Image Composition"):
            gr.Markdown("# ✂️ Image Composition")
            with gr.Row():
                with gr.Column():
                    input_image_comp = gr.Image(type="pil", label="Input Image", width=725, height=250)
                    shrink_factor = gr.Slider(0, 50, step=1, value=5, label="Shrink Factor (%)")
                    horizontal_position = gr.Slider(0, 100, step=1, value=50,
                                                    label="Horizontal Position (0=Left, 50=Center, 100=Right)")
                    vertical_position = gr.Slider(0, 100, step=1, value=50,
                                                  label="Vertical Position (0=Bottom, 50=Center, 100=Top)")
                    with gr.Row():
                        aspect_ratio_options_comp = [
                            "1:1", "2:3", "3:2", "4:3", "3:4", "16:9",
                            "9:16", "5:4", "4:5", "7:5", "5:7", "21:9", "unchanged"
                        ]
                        aspect_ratio_str_comp = gr.Dropdown(aspect_ratio_options_comp, value="3:2", label="Aspect Ratio")
                        megapixels_comp = gr.Slider(0, 8.0, step=0.1, value=2.0, label="Megapixels (0 for natural size)")
                    process_button_comp = gr.Button("Process Image")
                with gr.Column():
                    shrink_output = gr.Image(type="pil", label="Composed Output Image", width=725, height=250)
                    with gr.Row():
                        save_dir_comp = gr.Textbox(label="Save Directory", value="D:\\imagecropandzoominterface", interactive=True)
                        file_type_comp = gr.Dropdown([".jpg", ".png", ".webp"], value=".jpg", label="File Type")
                    save_button_comp = gr.Button("Save Composed Image")
                    filename_display_comp = gr.Textbox(label="Filename", interactive=False)
            process_button_comp.click(
                process_image,
                inputs=[input_image_comp, shrink_factor, horizontal_position, vertical_position, aspect_ratio_str_comp, megapixels_comp],
                outputs=shrink_output
            )
            save_button_comp.click(
                save_composition_action,
                inputs=[shrink_output, file_type_comp, save_dir_comp],
                outputs=filename_display_comp
            )

        # ---------------------------------------------------
        # Tab 3: Background Removal
        # ---------------------------------------------------
        with gr.Tab("🔮 Background Removal"):
            gr.Markdown("# 🔮 Background Removal\nUse the image from the 'Image Composition' tab as input.")
            with gr.Row():
                with gr.Column():
                    bg_torchscript_mode = gr.Dropdown(
                        choices=["default", "on"],
                        value="on",
                        label="TorchScript JIT Mode (for BG Removal)",
                        info="Use 'on' for TorchScript JIT optimization"
                    )
                    bg_threshold = gr.Slider(
                        0.0, 1.0, step=0.01, value=0.5,
                        label="Background Removal Threshold",
                        info="Adjust sensitivity of background detection"
                    )
                    remove_bg_button = gr.Button("Process Image")
                with gr.Column():
                    bg_removed_output = gr.Image(type="pil", label="Background Removed Image", width=725, height=300)
                    mask_output = gr.Image(type="pil", label="Mask", width=725, height=300)
            remove_bg_button.click(
                remove_bg_from_image,
                inputs=[shrink_output, bg_torchscript_mode, bg_threshold],
                outputs=[bg_removed_output, mask_output]
            )

        # ---------------------------------------------------
        # Tab 4: Overlay Background
        # ---------------------------------------------------
        with gr.Tab("🌆 Overlay Background"):
            gr.Markdown("# 🌆 Overlay Background for Transparent Image")
            with gr.Row():
                with gr.Column():
                    subject_img = gr.Image(type="filepath", label="Subject Image", image_mode="RGBA", height=300)
                    background_img = gr.Image(type="filepath", label="Background Image", image_mode="RGB", height=300)
                with gr.Column():
                    compositor_output = gr.Image(type="pil", label="Result", height=460)
                    with gr.Row():
                        position_slider = gr.Slider(0, 100, 50, label="Background Position")
                        show_bg_toggle = gr.Checkbox(label="Show Background Preview")
                        blur_toggle = gr.Checkbox(label="Enable Blur")
                        blur_strength = gr.Slider(0, 8, 0, step=0.1, visible=False)
            blur_toggle.change(lambda x: gr.update(visible=x), blur_toggle, blur_strength)
            components_overlay = [subject_img, background_img, show_bg_toggle, position_slider, blur_toggle, blur_strength]
            process_button_overlay = gr.Button("Process Image")
            process_button_overlay.click(
                process_images,
                inputs=components_overlay,
                outputs=compositor_output
            )

        # ---------------------------------------------------
        # Tab 5: Colour Background
        # ---------------------------------------------------
        with gr.Tab("🎨 Colour Background"):
            gr.Markdown("# 🎨 Colour Background for Transparent Image")
            with gr.Row():
                bg_type = gr.Radio(["Solid Color", "Gradient Background"], value="Solid Color")
            with gr.Row():
                with gr.Column():
                    input_img_color = gr.Image(type="filepath", label="Input Image", image_mode="RGBA", width=720, height=300)
                    with gr.Group(visible=True) as solid_controls:
                        hue = gr.Slider(0, 360, 0, label="Hue")
                        sat = gr.Slider(0, 100, 100, label="Saturation")
                        lum = gr.Slider(0, 100, 50, label="Luminosity")
                    with gr.Group(visible=False) as gradient_controls:
                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("**Top Color**")
                                t_hue = gr.Slider(0, 360, 0, label="Top Hue")
                                t_sat = gr.Slider(0, 100, 100, label="Top Saturation")
                                t_lum = gr.Slider(0, 100, 50, label="Top Luminosity")
                            with gr.Column():
                                gr.Markdown("**Bottom Color**")
                                b_hue = gr.Slider(0, 360, 120, label="Bottom Hue")
                                b_sat = gr.Slider(0, 100, 100, label="Bottom Saturation")
                                b_lum = gr.Slider(0, 100, 50, label="Bottom Luminosity")
                with gr.Column():
                    output_img_color = gr.Image(type="pil", label="Result", width=720, height=430)
                    process_button_color = gr.Button("Process Image")
            bg_type.change(
                lambda x: (gr.update(visible=x == "Solid Color"), gr.update(visible=x == "Gradient Background")),
                bg_type,
                [solid_controls, gradient_controls]
            )
            process_button_color.click(
                apply_background,
                inputs=[input_img_color, bg_type, hue, sat, lum, t_hue, t_sat, t_lum, b_hue, b_sat, b_lum],
                outputs=output_img_color
            )

if __name__ == "__main__":
    server_name = "127.0.0.1"
    app.launch(
        server_name=server_name,
        server_port=7861,
        share=False,
        inbrowser=True
    )
