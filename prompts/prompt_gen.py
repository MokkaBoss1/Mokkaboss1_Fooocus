#!/usr/bin/env python
"""
Prompt Generator Application with Revision Support and Background Type Integration
------------------------------------------------------------------------------------

This module creates a Gradio interface for generating prompts.
It uses separated functions for handling prompt updates and user actions,
includes buttons to save and load default values, and supports a dynamic background type that updates available landscape choices.
"""
import sys
import os
import json
import re
import random
import logging
import pyperclip
import gradio as gr
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
base_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(base_dir))

# =============================================================================
# Imports for styles and prompt functions
# =============================================================================

from styles import (
    genders, ethnicities, shottypes, haircolours, hairstyles, dress_colours,
    dress_materials, dress_patterns, color_textures, depthfocus_list, moods,
    lightings, adjectives, defaults, styles_marc_k3nt3l, styles_mre, styles_sai,
    styles_000, styles_diva, styles_twri, styles_main
)

from prompt_functions import (
    update_outfit_dropdown, update_background_dropdown,
    save_defaults, load_defaults, manipulate_text,
    generate_subject_prompt, generate_landscape_prompt, combine_prompts
)

#####################################################################
CONFIG_FILENAME = "theme_config.json"
# start in the same folder as this script...
current_dir = os.path.dirname(__file__)
# ...then go up one level
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
# try parent first, then fallback to current
CONFIG_PATHS = [
    os.path.join(parent_dir, CONFIG_FILENAME),
    os.path.join(current_dir, CONFIG_FILENAME),
]

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
theme_name = DEFAULT_THEME

# attempt to load from parent, then current
for path in CONFIG_PATHS:
    try:
        with open(path, "r") as f:
            cfg = json.load(f)
            theme_name = cfg.get("theme", DEFAULT_THEME)
        break
    except (FileNotFoundError, json.JSONDecodeError):
        continue

# Instantiate theme object
theme = getattr(gr.themes, theme_name, gr.themes.Base)()
###############################################################





# =============================================================================
# Prepare combined and sorted styles
# =============================================================================

combined_styles = (
    styles_main + styles_twri + styles_marc_k3nt3l +
    styles_diva + styles_000 + styles_sai + styles_mre
)
sorted_combined_styles = sorted(set(combined_styles))

# =============================================================================
# Load additional JSON data for occasions and backgrounds
# =============================================================================

# at top of prompt_gen.py
base_dir = Path(__file__).resolve().parent

# make the script’s folder your working directory
os.chdir(base_dir)

try:
    with open("outfits.json", "r") as f:
        outfits_data = json.load(f)
    occasion_choices = list(outfits_data.keys())
except Exception as e:
    logging.error(f"Error loading occasions from outfits.json: {e}")
    occasion_choices = []

with open("backgrounds.json", "r") as f:
    backgrounds_data = json.load(f)
background_type_choices = list(backgrounds_data.keys())

# =============================================================================
# Helpers for defaults and prompt cleaning
# =============================================================================

DEFAULT_JSON_FILE = "defaults.json"

def fallback(default_value: str, choices: list) -> str:
    return default_value if default_value and default_value in choices else choices[0]

def clean_prompt(prompt: str) -> str:
    prompt = re.sub(r'([,.;:!?]){2,}', r'\1', prompt)
    return prompt.strip(" ,.;:!?")

# =============================================================================
# Core generation logic
# =============================================================================

def on_generate_all(
        pre_text, post_text, gender, ethnicity, shot_type, hair_colour, hair_style,
        occasion, dress_style, dress_colour, dress_material, dress_pattern,
        pre_textl, post_textl, adjective, background_type, landscape, lighting, mood,
        depth_focus, color_texture, style1, style2, style3
):
    subject_prompt = generate_subject_prompt(
        pre_text, post_text, gender, ethnicity, shot_type,
        hair_colour, hair_style, dress_style, dress_colour,
        dress_material, dress_pattern, occasion
    )
    landscape_prompt = generate_landscape_prompt(
        pre_textl, post_textl, adjective, landscape,
        lighting, mood, depth_focus, color_texture
    )
    combined = clean_prompt(combine_prompts(subject_prompt, landscape_prompt))
    styled = manipulate_text(combined, style1, style2, style3, str(base_dir / "styles"))
    pyperclip.copy(styled)
    return subject_prompt, landscape_prompt, styled

# =============================================================================
# Gradio Interface Definition
# =============================================================================

def create_gradio_interface() -> gr.Blocks:
    with gr.Blocks(theme=theme, title="Prompt Generator") as demo1:
        default_values = load_defaults()

        with gr.Accordion("👩 Subject Prompt", open=True):
            with gr.Row():
                pre_text = gr.Textbox(label="Pre Text", lines=2, value=default_values[0])
                post_text = gr.Textbox(label="Post Text", lines=2, value=default_values[1])
                gender = gr.Dropdown(label="Gender", choices=["Random"] + genders,
                                     visible=False, value=fallback(default_values[2], ["Random"] + genders))
                ethnicity = gr.Dropdown(label="Ethnicity", choices=ethnicities,
                                        value=fallback(default_values[3], ethnicities))
            with gr.Row():
                shot_type = gr.Dropdown(label="Shot Type", choices=shottypes,
                                        value=fallback(default_values[4], shottypes))
                hair_colour = gr.Dropdown(label="Hair Colour", choices=haircolours,
                                          value=fallback(default_values[5], haircolours))
                hair_style = gr.Dropdown(label="Hair Style", choices=hairstyles,
                                         value=fallback(default_values[6], hairstyles))
                occasion = gr.Dropdown(label="Occasion", choices=occasion_choices,
                                       value=fallback(default_values[7], occasion_choices))
            with gr.Row():
                initial = update_outfit_dropdown(
                    fallback(default_values[7], occasion_choices),
                    fallback(default_values[4], shottypes), default_values[8]
                )
                dress_style = gr.Dropdown(label="Outfit", choices=initial["choices"],
                                          value=fallback(initial["value"], initial["choices"]),
                                          allow_custom_value=True)
                dress_colour = gr.Dropdown(label="Dress Colour", choices=dress_colours,
                                           value=fallback(default_values[9], dress_colours))
                dress_material = gr.Dropdown(label="Dress Material", choices=dress_materials,
                                             value=fallback(default_values[10], dress_materials))
                dress_pattern = gr.Dropdown(label="Dress Pattern", choices=dress_patterns,
                                            value=fallback(default_values[11], dress_patterns))

        with gr.Accordion("🖼️ Landscape Prompt", open=False):
            with gr.Row():
                pre_textl = gr.Textbox(label="Pre Text", lines=2, value=default_values[12])
                post_textl = gr.Textbox(label="Post Text", lines=2, value=default_values[13])
                adjective = gr.Dropdown(choices=["Random", "None"] + adjectives,
                                        label="Adjective",
                                        value=fallback(default_values[14], ["Random", "None"] + adjectives),
                                        allow_custom_value=True)
                background_type = gr.Dropdown(choices=background_type_choices,
                                              label="Background Type",
                                              value=fallback(default_values[15], background_type_choices),
                                              allow_custom_value=True)
            with gr.Row():
                landscape = gr.Dropdown(
                    choices=["Random", "None"] + backgrounds_data[background_type_choices[0]],
                    label="Landscape",
                    value=fallback(default_values[16], ["Random", "None"] + backgrounds_data[background_type_choices[0]]),
                    allow_custom_value=True
                )
                lighting = gr.Dropdown(choices=["Random", "None"] + lightings,
                                       label="Lighting",
                                       value=fallback(default_values[17], ["Random", "None"] + lightings),
                                       allow_custom_value=True)
                mood = gr.Dropdown(choices=moods, label="Mood",
                                   value=fallback(default_values[18], moods))
                depth_focus = gr.Dropdown(choices=["Random", "None"] + depthfocus_list,
                                          label="Depth Focus",
                                          value=fallback(default_values[19], ["Random", "None"] + depthfocus_list),
                                          allow_custom_value=True)
                color_texture = gr.Dropdown(choices=["Random", "None"] + color_textures,
                                            label="Color Texture",
                                            value=fallback(default_values[20], ["Random", "None"] + color_textures),
                                            allow_custom_value=True)
            with gr.Row():
                style1 = gr.Dropdown(choices=sorted_combined_styles, label="Style1",
                                     value=fallback(default_values[21], sorted_combined_styles))
                style2 = gr.Dropdown(choices=sorted_combined_styles, label="Style2",
                                     value=fallback(default_values[22], sorted_combined_styles))
                style3 = gr.Dropdown(choices=sorted_combined_styles, label="Style3",
                                     value=fallback(default_values[23], sorted_combined_styles))

        subject_prompt_output   = gr.Textbox(label="Generated Subject Prompt", visible=False)
        landscape_prompt_output = gr.Textbox(label="Generated Landscape Prompt", visible=False)
        combined_prompt_output  = gr.Textbox(label="✨ Combined Generated Prompt", lines=4)

        with gr.Row():
            generate_btn = gr.Button("Generate Prompt", variant="primary")
            save_button = gr.Button("Save Default Values")
            load_button = gr.Button("Load Default Values")

        inputs = [
            pre_text, post_text, gender, ethnicity, shot_type, hair_colour, hair_style,
            occasion, dress_style, dress_colour, dress_material, dress_pattern,
            pre_textl, post_textl, adjective, background_type, landscape,
            lighting, mood, depth_focus, color_texture, style1, style2, style3
        ]
        generate_btn.click(fn=on_generate_all, inputs=inputs,
                           outputs=[subject_prompt_output, landscape_prompt_output, combined_prompt_output])
        save_button.click(fn=save_defaults, inputs=inputs, outputs=[])
        load_button.click(fn=load_defaults, inputs=[], outputs=inputs)

        occasion.change(fn=update_outfit_dropdown,
                        inputs=[occasion, shot_type, dress_style], outputs=dress_style)
        shot_type.change(fn=update_outfit_dropdown,
                         inputs=[occasion, shot_type, dress_style], outputs=dress_style)
        demo1.load(fn=update_outfit_dropdown,
                  inputs=[occasion, shot_type, dress_style], outputs=dress_style)

        background_type.change(
            fn=lambda bg, curr: update_background_dropdown(bg, curr, "backgrounds.json"),
            inputs=[background_type, landscape], outputs=landscape
        )

    return demo1

demo1 = create_gradio_interface()

if __name__ == "__main__":
    demo1.launch(
        server_name="127.0.0.1",
        share=False,
        inbrowser=True
    )
