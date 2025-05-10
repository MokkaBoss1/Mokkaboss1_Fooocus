#!/usr/bin/env python
"""
Functions for Prompt Generator Program - Updated Version
----------------------------------------------------------
This module contains functions for generating prompts, updating dropdowns,
loading defaults, manipulating text, and communicating with external models.
It now includes support for an “Occasion” parameter and uses an external
JSON file (outfits.json) to select an outfit based on both Occasion and Shot Type.
"""

import os
import json
import re
import time
import random
import string
import logging
import subprocess
import requests
import pyperclip
from io import BytesIO
from PIL import Image
from typing import Optional, List, Any, Tuple, Union, Dict
from styles import defaults
from styles import (
    ethnicities, shottypes, haircolours, hairstyles, dress_styles as all_dress_styles,
    dress_colours, dress_materials, dress_patterns, color_textures, depthfocus_list, moods,
    lightings, adjectives, landscapes, close_up_dress_styles, half_body_dress_styles, full_body_dress_styles,
    oc_aspectratios, defaults  # Import defaults here
)
import gradio as gr

# Import styles from external module.
from styles import (
    ethnicities, shottypes, haircolours, hairstyles, dress_styles as all_dress_styles,
    dress_colours, dress_materials, dress_patterns, color_textures, depthfocus_list, moods,
    lightings, adjectives, landscapes, close_up_dress_styles, half_body_dress_styles,
    full_body_dress_styles, oc_aspectratios
)

# Global configuration variables.
# Unified JSON file name for saving/loading defaults.
DEFAULT_JSON_FILE = "defaults.json"
cn_switch = ["1", "2"]
ld_selections = ["1", "2"]

# Consolidated dress styles list (legacy or fallback).
dress_styles = close_up_dress_styles + half_body_dress_styles + full_body_dress_styles

# Configure logging once.
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


# -----------------------------
# Helper Functions
# -----------------------------
def resolve_random_or_none(value: str, options: List[str]) -> Optional[str]:
    """
    Resolve a value that might be 'Random' or 'None' by selecting a random option or empty string.

    Inputs:
        value (str): A string that may be 'Random', 'None', or a specific value.
        options (List[str]): A list of string options.

    Outputs:
        Optional[str]: A randomly chosen value (lowercased) from the options if 'Random' is provided,
                       an empty string if 'None' is provided, or the original value otherwise.
    """
    if value == "Random":
        if len(options) > 2:
            return random.choice(options[2:]).lower()
        else:
            return random.choice(options).lower()
    elif value == "None":
        return ""
    return value


def generate_random_string(option: str, digits: int = 1, seed: Optional[int] = None) -> str:
    """
    Generate a random string using a specified character set.

    Inputs:
        option (str): A key indicating which character set to use.
        digits (int): Number of characters to generate (between 1 and 12).
        seed (Optional[int]): Optional seed for random number generation.

    Outputs:
        str: A randomly generated string of the specified length.
    """
    if not (1 <= digits <= 12):
        raise ValueError("Digits must be between 1 and 12")
    if seed is not None:
        random.seed(seed)

    char_sets = {
        "random number": '0123456789',
        "random hexadecimal": '0123456789abcdef',
        "random ascii code": 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
        "random ascii & number": '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    }
    chars = char_sets.get(option)
    if not chars:
        raise ValueError(f"Invalid option '{option}'. Valid options are: {list(char_sets.keys())}")
    return ''.join(random.SystemRandom().choices(chars, k=digits))


# -----------------------------
# Dropdown Update Functions
# -----------------------------
def update_dress_styles(shot_type: str) -> dict:
    """
    Update the Gradio dropdown for dress styles based on the shot type.

    Inputs:
        shot_type (str): A string indicating the shot type (e.g., "close-up", "half-body shot", "full-body shot").

    Outputs:
        dict: A Gradio update dictionary with the list of dress styles as choices and the first style selected.
    """
    dress_styles_map = {
        "close-up": close_up_dress_styles,
        "half-body shot": half_body_dress_styles,
        "full-body shot": full_body_dress_styles
    }
    styles = dress_styles_map.get(shot_type, [])
    return gr.update(choices=styles, value=styles[0] if styles else None)


def update_dropdown(shot_type: str) -> dict:
    """
    Update a generic Gradio dropdown by prepending 'Random' to the dress styles list for a given shot type.

    Inputs:
        shot_type (str): A string representing the shot type.

    Outputs:
        dict: A Gradio update dictionary with 'Random' as the first choice followed by the relevant dress styles.
    """
    dress_styles_map = {
        "close-up": close_up_dress_styles,
        "half-body shot": half_body_dress_styles,
        "full-body shot": full_body_dress_styles
    }
    styles = dress_styles_map.get(shot_type, [])
    options = ["Random"] + styles
    return gr.update(choices=options, value="Random")


def update_outfit_dropdown(occasion: str, shot_type: str, current_value: str) -> dict:
    """
    Update the outfit dropdown based on the selected occasion and shot type.

    Inputs:
        occasion (str): The selected occasion.
        shot_type (str): The selected shot type.
        current_value (str): The current dropdown value.

    Outputs:
        dict: A Gradio update dictionary containing the updated outfit choices and the appropriate default value.
    """
    try:
        with open("outfits.json", "r") as f:
            outfits = json.load(f)
    except Exception as e:
        logging.error(f"Error loading outfits.json: {e}")
        return gr.update(choices=["Random", "None"], value="Random")

    shot_mapping = {
        "close-up": "close_up",
        "half-body shot": "half_body",
        "full-body shot": "full_body"
    }
    key = shot_mapping.get(shot_type, "close_up")
    outfit_list = outfits.get(occasion, [])
    choices = ["Random", "None"] + [outfit[key] for outfit in outfit_list if outfit.get(key)]

    value = current_value if current_value in choices else "Random"
    return gr.update(choices=choices, value=value)


# -----------------------------
# Defaults Persistence Functions
# -----------------------------
def load_and_concatenate_json_files(directory_path: str) -> List[Union[Dict[str, Any], List[Any]]]:
    """
    Load and concatenate data from all JSON files in the given directory.

    Inputs:
        directory_path (str): Path to the directory containing JSON files.

    Outputs:
        List[Union[Dict[str, Any], List[Any]]]: A list containing all data loaded from the JSON files.
    """
    all_styles = []
    try:
        for filename in os.listdir(directory_path):
            if filename.endswith('.json'):
                file_path = os.path.join(directory_path, filename)
                if os.path.isfile(file_path):
                    with open(file_path, 'r') as file:
                        file_data = json.load(file)
                        if isinstance(file_data, list):
                            all_styles.extend(file_data)
                        elif isinstance(file_data, dict):
                            all_styles.append(file_data)
    except Exception as e:
        logging.error(f"Error loading JSON files from {directory_path}: {e}")
        raise ValueError(f"An error occurred while loading the JSON files: {e}")
    return all_styles


def manipulate_text(multiline_string: str, style1: str, style2: str, style3: str, directory_path: str) -> str:
    """
    Process a multiline string by applying style transformations loaded from JSON files.

    Inputs:
        multiline_string (str): The input text that may span multiple lines.
        style1 (str): Name of the first style transformation to apply.
        style2 (str): Name of the second style transformation.
        style3 (str): Name of the third style transformation.
        directory_path (str): Path to the directory containing style JSON files.

    Outputs:
        str: The transformed text after applying all specified style prompts.
    """
    try:
        styles_data = load_and_concatenate_json_files(directory_path)
    except ValueError as e:
        raise ValueError(f"Error loading styles data: {e}")

    selected_styles = [style1, style2, style3]
    processed_text = multiline_string
    style_map = {style['name']: style for style in styles_data if 'name' in style}
    for style_name in selected_styles:
        style_info = style_map.get(style_name)
        if style_info:
            processed_text = style_info['prompt'].format(prompt=processed_text)
        else:
            raise ValueError(f"Style '{style_name}' not found in JSON files.")
    return processed_text


# -----------------------------
# Subject and Landscape Prompt Generation
# -----------------------------
def generate_subject_prompt(
        pre_text: str, post_text: str, gender: str, ethnicity: str, shot_type: str,
        hair_colour: str, hair_style: str, dress_style: str, dress_colour: str,
        dress_material: str, dress_pattern: str, occasion: str
) -> str:
    """
    Generate a subject prompt based on various style and configuration inputs.

    Inputs:
        pre_text (str): Text to prepend to the prompt.
        post_text (str): Text to append to the prompt.
        gender (str): Gender descriptor.
        ethnicity (str): Ethnicity descriptor, which may be 'Random' or 'None'.
        shot_type (str): The type of shot (e.g., close-up, half-body shot).
        hair_colour (str): Hair colour descriptor.
        hair_style (str): Hair style descriptor.
        dress_style (str): Dress style descriptor, may be 'Random' or 'None' or specific style.
        dress_colour (str): Dress colour descriptor.
        dress_material (str): Dress material descriptor.
        dress_pattern (str): Dress pattern descriptor.
        occasion (str): The occasion which might influence outfit selection.

    Outputs:
        str: The generated subject prompt as a natural language description.
    """
    resolved_ethnicity = resolve_random_or_none(ethnicity, ethnicities)
    resolved_shot_type = resolve_random_or_none(shot_type, shottypes)
    resolved_hair_colour = resolve_random_or_none(hair_colour, haircolours)
    resolved_hair_style = resolve_random_or_none(hair_style, hairstyles)

    fallback_parts = [
        resolve_random_or_none(dress_colour, dress_colours),
        resolve_random_or_none(dress_material, dress_materials),
        resolve_random_or_none(dress_pattern, dress_patterns)
    ]
    fallback_parts = [p for p in fallback_parts if p and p.strip().lower() not in ["none", "random"]]
    fallback = " ".join(fallback_parts).strip()

    outfit_part = ""

    if dress_style.strip().lower() == "none":
        # Explicitly no outfit or occasion when 'None' selected
        outfit_part = ""
    elif dress_style.strip().lower() == "random":
        try:
            with open("outfits.json", "r") as f:
                outfits = json.load(f)
            shot_mapping = {
                "close-up": "close_up",
                "half-body shot": "half_body",
                "full-body shot": "full_body"
            }
            key = shot_mapping.get(resolved_shot_type, "close_up")
            outfit_list = outfits.get(occasion, [])
            valid_outfits = [entry.get(key) for entry in outfit_list if entry.get(key)]
            random_outfit = random.choice(valid_outfits) if valid_outfits else ""
            outfit_part = f"{occasion}, {fallback} {random_outfit}".strip()
        except Exception as e:
            logging.error(f"Error loading outfits.json: {e}")
            outfit_part = fallback
    else:
        specific_outfit = resolve_random_or_none(dress_style, all_dress_styles)
        outfit_part = f"{occasion}, {fallback} {specific_outfit}".strip()

    outfit_part = re.sub(r'\s{2,}', ' ', outfit_part).strip().rstrip(',')

    positive_prompt = f"{resolved_shot_type} {pre_text} {resolved_ethnicity} {gender} with {resolved_hair_colour} {resolved_hair_style}"
    if outfit_part:
        positive_prompt += f", wearing {outfit_part}"
    if post_text:
        positive_prompt += f", {post_text}"

    positive_prompt = re.sub(r'\s{2,}', ' ', positive_prompt).strip().rstrip(',')
    return positive_prompt


def update_background_dropdown(background_type: str, current_value: str, json_path: str = "backgrounds.json") -> dict:
    """
    Update the background dropdown based on a specified background type.

    Inputs:
        background_type (str): The type/category of backgrounds to load.
        current_value (str): The current selected value in the dropdown.
        json_path (str): Path to the JSON file containing background options (default is "backgrounds.json").

    Outputs:
        dict: A Gradio update dictionary with updated background choices and a default value.
    """
    try:
        with open(json_path, "r") as f:
            backgrounds = json.load(f)
    except Exception as e:
        logging.error(f"Error loading backgrounds.json: {e}")
        return gr.update(choices=["Random", "None"], value="Random")

    choices = ["Random", "None"] + backgrounds.get(background_type, [])
    value = current_value if current_value in choices else "Random"
    return gr.update(choices=choices, value=value)


def generate_landscape_prompt(
        pre_textl: str, post_textl: str, adjective: str, landscape: str, lighting: str, mood: str,
        depth_focus: str, color_texture: str
) -> str:
    """
    Generate a landscape prompt based on provided parameters.

    Inputs:
        pre_textl (str): Text to prepend to the landscape prompt.
        post_textl (str): Text to append to the prompt.
        adjective (str): An adjective descriptor which may be 'Random' or a specific adjective.
        landscape (str): A descriptor for the landscape.
        lighting (str): Lighting descriptor.
        mood (str): Mood descriptor.
        depth_focus (str): Descriptor for depth focus.
        color_texture (str): Descriptor for color texture.

    Outputs:
        str: A processed landscape prompt in lowercase.
    """
    landscape = resolve_random_or_none(landscape, landscapes)
    adjective = resolve_random_or_none(adjective, adjectives)
    lighting = resolve_random_or_none(lighting, lightings)
    mood = resolve_random_or_none(mood, moods)
    depth_focus = resolve_random_or_none(depth_focus, depthfocus_list)
    color_texture = resolve_random_or_none(color_texture, color_textures)
    positive_prompt = (
        f"{pre_textl} {adjective} {landscape} {lighting} {mood} {depth_focus} {color_texture}, {post_textl}"
    )
    positive_prompt = re.sub(r'\s{2,}', ' ', positive_prompt).strip().lower()
    return positive_prompt


def combine_prompts(subject_prompt: str, landscape_prompt: str) -> Optional[str]:
    """
    Combine subject and landscape prompts into a single prompt.

    Inputs:
        subject_prompt (str): The prompt describing the subject.
        landscape_prompt (str): The prompt describing the landscape.

    Outputs:
        Optional[str]: A combined prompt string if successful; otherwise, returns None.
    """
    try:
        combined_prompt = f"{subject_prompt} {landscape_prompt}".strip()
        combined_prompt = re.sub(r'\*.*?\*', '', combined_prompt)
        combined_prompt = re.sub(r'\s{2,}', ' ', combined_prompt).strip()
        if not combined_prompt:
            logging.warning("Combined prompt is empty.")
            return None
        return combined_prompt
    except Exception as e:
        logging.error(f"Error combining prompts: {e}")
        return None


# -----------------------------
# Ollama Management Functions
# -----------------------------
def check_and_start_ollama() -> bool:
    """
    Check if Ollama is running, and start it if necessary.

    Outputs:
        bool: True if Ollama is running or started successfully, False otherwise.
    """
    URL = "http://localhost:11434/"
    TIMEOUT = 5
    try:
        response = requests.get(URL, timeout=TIMEOUT)
        if response.status_code == 200:
            logging.info("Ollama is already running.")
            return True
    except requests.ConnectionError:
        logging.info("Ollama is not running. Attempting to start it...")
    except requests.Timeout:
        logging.error("Connection to Ollama timed out. Ensure the server is responsive.")
        return False
    except Exception as e:
        logging.error(f"Unexpected error while checking Ollama status: {e}")
        return False
    try:
        subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info("Starting Ollama with 'ollama serve'...")
        time.sleep(TIMEOUT)
        response = requests.get(URL, timeout=TIMEOUT)
        if response.status_code == 200:
            logging.info("Ollama started successfully.")
            return True
        else:
            logging.error("Ollama did not start successfully.")
            return False
    except FileNotFoundError:
        logging.error("The 'ollama' command was not found. Ensure Ollama is installed and in your PATH.")
        return False
    except Exception as e:
        logging.error(f"Failed to start Ollama: {e}")
        return False


def stop_ollama() -> None:
    """
    Stop the Ollama model to release resources.

    Outputs:
        None
    """
    try:
        subprocess.run(['ollama', 'stop', 'huihui_ai/llama3.2-abliterate:latest'], check=True)
        logging.info("Ollama model stopped successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error stopping Ollama model: {e}")
    except FileNotFoundError:
        logging.error("The 'ollama' command was not found. Ensure Ollama is installed and in your PATH.")
    except Exception as e:
        logging.error(f"Unexpected error while stopping Ollama model: {e}")


def strip_unwanted_chars(text: str) -> str:
    """
    Remove ANSI escape sequences and braille spinner characters from text.

    Inputs:
        text (str): The input string which may contain unwanted characters.

    Outputs:
        str: The cleaned text.
    """
    if not text:
        return ""
    # Remove ANSI escape sequences.
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    # Remove braille spinner characters (Unicode block U+2800 to U+28FF).
    text = re.sub(r'[\u2800-\u28FF]', '', text)
    return text.strip()


def ask_ollama(question: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Ask a question to Ollama and return its output.

    Inputs:
        question (str): The question to send to the Ollama model.

    Outputs:
        Tuple[Optional[str], Optional[str]]: A tuple containing the cleaned standard output and standard error.
    """
    try:
        command = ['ollama', 'run', 'huihui_ai/llama3.2-abliterate:latest']
        result = subprocess.run(
            command,
            input=question,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False
        )
        cleaned_output = strip_unwanted_chars(result.stdout)
        cleaned_error = strip_unwanted_chars(result.stderr)
        return cleaned_output, cleaned_error
    except FileNotFoundError:
        logging.error("The 'ollama' command was not found. Ensure Ollama is installed and in your PATH.")
        return None, None
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running Ollama model: {e}")
        return None, None
    except Exception as e:
        logging.error(f"Unexpected error while running Ollama model: {e}")
        return None, None


def query_ollama(user_question: str, max_tokens: int, min_percentage: int = 20) -> str:
    """
    Query the Ollama model while enforcing a minimum and maximum word count on the response.

    Inputs:
        user_question (str): The user's question or prompt to send to Ollama.
        max_tokens (int): Maximum token limit used to calculate a word limit.
        min_percentage (int): Minimum percentage of max word limit required in the response.

    Outputs:
        str: The final response from Ollama, or an error message if applicable.
    """
    if not (20 <= min_percentage <= 90):
        raise ValueError("min_percentage should be between 20 and 90.")

    max_word_limit = int(max_tokens * 0.75)
    min_word_limit = int(max_word_limit * (min_percentage / 100))
    full_question = (
        "Translate this AI image prompt into natural language. "
        "Never provide any explanation or description before the actual natural language prompt output. "
        "Never provide multiple options. Do not include headings or divide the prompt into chapters. "
        "This should read like a description of an existing image to a blind person. "
        f"Ensure the response is at least {min_word_limit} words and does not exceed {max_word_limit} words. "
        f"Start the natural language prompt with 'an image of a': {user_question}"
    )

    response, error = ask_ollama(full_question)
    stop_ollama()

    if response and response.strip():
        return response.strip()
    elif error and error.strip():
        logging.error(f"Error from Ollama: {error}")
        return error.strip()
    else:
        return "No response from Ollama."


# -----------------------------
# Image Processing Functions
# -----------------------------
def process_image(
        input_image: Image.Image, aspect_ratio: str, exact_aspect_ratio: float, zoom: float,
        x_offset: float, y_offset: float, megapixels: float, border: int, inside_border: int,
        border_color: Tuple[int, int, int]
) -> Image.Image:
    """
    Process the input image based on cropping, zooming, resizing, and border addition.

    Inputs:
        input_image (Image.Image): The original image to process.
        aspect_ratio (str): A string key for selecting an aspect ratio (or "unchanged").
        exact_aspect_ratio (float): A specific aspect ratio value; if non-zero, used to calculate dimensions.
        zoom (float): A zoom factor to apply to the cropped image.
        x_offset (float): Horizontal offset percentage (0-100) for cropping.
        y_offset (float): Vertical offset percentage (0-100) for cropping.
        megapixels (float): Target megapixels for resizing the image; if greater than 0, image is resized.
        border (int): Width of an external border to add around the image.
        inside_border (int): Width of an internal border to add within the image.
        border_color (Tuple[int, int, int]): RGB color for the border.

    Outputs:
        Image.Image: The processed image.
    """
    try:
        if exact_aspect_ratio != 0.0:
            width, height = calculate_exact_dimensions(exact_aspect_ratio)
        elif aspect_ratio != "unchanged":
            width, height = oc_aspectratios.get(aspect_ratio, input_image.size)
        else:
            width, height = input_image.size

        ratio = width / height
        input_width, input_height = input_image.size
        output_width = int(min(input_width, input_height * ratio))
        output_height = int(output_width / ratio)

        x_offset_normalized = x_offset / 100.0
        y_offset_normalized = y_offset / 100.0

        x_offset_aspect = int(
            (input_width - output_width) * 0.5 + (input_width - output_width) * x_offset_normalized * 0.5)
        y_offset_aspect = int(
            (input_height - output_height) * 0.5 + (input_height - output_height) * y_offset_normalized * 0.5)

        crop_x1_aspect = max(0, min(input_width - output_width, x_offset_aspect))
        crop_y1_aspect = max(0, min(input_height - output_height, y_offset_aspect))
        crop_x2_aspect = min(input_width, crop_x1_aspect + output_width)
        crop_y2_aspect = min(input_height, crop_y1_aspect + output_height)

        cropped_image_aspect = input_image.crop((crop_x1_aspect, crop_y1_aspect, crop_x2_aspect, crop_y2_aspect))
        cropped_width, cropped_height = cropped_image_aspect.size

        output_width_zoom = int(cropped_width / zoom)
        output_height_zoom = int(cropped_height / zoom)

        x = int(
            (cropped_width - output_width_zoom) * 0.5 + (cropped_width - output_width_zoom) * (x_offset / 100.0) * 0.5)
        y = int((cropped_height - output_height_zoom) * 0.5 + (cropped_height - output_height_zoom) * (
                y_offset / 100.0) * 0.5)

        crop_x1_zoom = max(0, min(cropped_width - output_width_zoom, x))
        crop_y1_zoom = max(0, min(cropped_height - output_height_zoom, y))
        crop_x2_zoom = min(cropped_width, crop_x1_zoom + output_width_zoom)
        crop_y2_zoom = min(cropped_height, crop_y1_zoom + output_height_zoom)

        crop_image = cropped_image_aspect.crop((crop_x1_zoom, crop_y1_zoom, crop_x2_zoom, crop_y2_zoom))

        if megapixels > 0.0:
            original_width, original_height = crop_image.size
            original_megapixels = (original_width * original_height) / 1048576
            scale_factor = (megapixels / original_megapixels) ** 0.5
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
            crop_image = crop_image.resize((new_width, new_height), Image.LANCZOS)

        if border > 0:
            crop_image = add_border(crop_image, border, border_color)

        if inside_border > 0:
            crop_image = add_inside_border(crop_image, inside_border, border_color)

        return crop_image
    except Exception as e:
        logging.error(f"Error processing image: {e}")
        return input_image


def add_border(image: Image.Image, border_width: int, border_color: Tuple[int, int, int]) -> Image.Image:
    """
    Add an external border around the image.

    Inputs:
        image (Image.Image): The image to which the border will be added.
        border_width (int): The width of the border.
        border_color (Tuple[int, int, int]): The RGB color of the border.

    Outputs:
        Image.Image: The image with the external border added.
    """
    try:
        new_width = image.width + 2 * border_width
        new_height = image.height + 2 * border_width
        new_image = Image.new("RGB", (new_width, new_height), border_color)
        new_image.paste(image, (border_width, border_width))
        return new_image
    except Exception as e:
        logging.error(f"Error adding border to image: {e}")
        return image


def add_inside_border(image: Image.Image, border_width: int, border_color: Tuple[int, int, int]) -> Image.Image:
    """
    Add an internal border within the image.

    Inputs:
        image (Image.Image): The image to process.
        border_width (int): The width of the internal border.
        border_color (Tuple[int, int, int]): The RGB color of the border.

    Outputs:
        Image.Image: The image with an inside border applied.
    """
    try:
        width, height = image.size
        new_image = Image.new("RGB", (width, height), border_color)
        cropped_image = image.crop((border_width, border_width, width - border_width, height - border_width))
        new_image.paste(cropped_image, (border_width, border_width))
        return new_image
    except Exception as e:
        logging.error(f"Error adding inside border to image: {e}")
        return image


def save_image(image: Image.Image, file_type: str, save_folder: str) -> Tuple[str, str]:
    """
    Save an image to a specified folder with a random filename.

    Inputs:
        image (Image.Image): The image to save.
        file_type (str): The file extension/type (e.g., ".jpg", ".png").
        save_folder (str): The folder path where the image will be saved.

    Outputs:
        Tuple[str, str]: A tuple containing the full save path and the generated filename.
    """
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    filename = ''.join(random.choices(string.ascii_letters + string.digits, k=8)) + file_type
    save_path = os.path.join(save_folder, filename)
    if file_type.lower() == ".jpg" and image.mode != "RGB":
        image = image.convert("RGB")
    if file_type.lower() == ".jpg":
        image.save(save_path, quality=95)
    else:
        image.save(save_path)
    return save_path, filename


def calculate_exact_dimensions(exact_aspect_ratio: float) -> Tuple[int, int]:
    """
    Calculate image dimensions based on a given aspect ratio.

    Inputs:
        exact_aspect_ratio (float): A positive number representing the desired aspect ratio.

    Outputs:
        Tuple[int, int]: A tuple (width, height) calculated based on the aspect ratio.
    """
    if exact_aspect_ratio <= 0:
        raise ValueError("The aspect ratio must be a positive number.")
    if exact_aspect_ratio >= 1:
        width = 1024
        height = int(width / exact_aspect_ratio)
    else:
        height = 1024
        width = int(height * exact_aspect_ratio)
    return width, height


def load_image_from_url(url: str) -> Optional[Image.Image]:
    """
    Load an image from a given URL.

    Inputs:
        url (str): The URL from which to download the image.

    Outputs:
        Optional[Image.Image]: The loaded image if successful; otherwise, None.
    """
    try:
        response = requests.get(url)
        if response.status_code != 200:
            logging.error(f"Failed to load image, status code: {response.status_code}")
            return None
        image = Image.open(BytesIO(response.content))
        return image
    except Exception as e:
        logging.error(f"Error loading image from URL: {e}")
        return None


def save_defaults(*values) -> None:
    """
    Save default configuration values to a JSON file.

    Inputs:
        *values: A variable number of configuration values in the order corresponding to the predefined keys.
    Outputs:
        None
    """
    # Now 24 keys; note that background type is added at index 15.
    keys = [
        "def_pre_text", "def_post_text", "def_gender", "def_ethnicity", "def_shottype",
        "def_haircolour", "def_hairstlye", "def_occasion",
        "def_dressstyle", "def_dresscolour", "def_material", "def_pattern",
        "def_pre_textl", "def_post_textl", "def_adjective", "def_background_type",
        "def_landscape", "def_lighting", "def_mood", "def_depthfocus", "def_color_texture",
        "def_style1", "def_style2", "def_style3"
    ]
    if len(values) < len(keys):
        values = list(values) + [""] * (len(keys) - len(values))
    data = {k: v for k, v in zip(keys, values)}
    try:
        with open(DEFAULT_JSON_FILE, "w") as file:
            json.dump(data, file)
    except Exception as e:
        logging.error(f"Error saving defaults: {e}")
        raise ValueError(f"An error occurred while saving the defaults: {e}")


def load_defaults() -> Tuple[str, ...]:
    """
    Load default configuration values from a JSON file.

    Inputs:
        None (uses the global DEFAULT_JSON_FILE and a predefined list of keys).

    Outputs:
        Tuple[str, ...]: A tuple containing the default values for each key.
    """
    json_file_path = DEFAULT_JSON_FILE
    keys = [
        "def_pre_text", "def_post_text", "def_gender", "def_ethnicity", "def_shottype",
        "def_haircolour", "def_hairstlye", "def_occasion",
        "def_dressstyle", "def_dresscolour", "def_material", "def_pattern",
        "def_pre_textl", "def_post_textl", "def_adjective", "def_background_type",
        "def_landscape", "def_lighting", "def_mood", "def_depthfocus", "def_color_texture",
        "def_style1", "def_style2", "def_style3"
    ]
    try:
        with open(json_file_path, "r") as file:
            data = json.load(file)
        results = []
        for key in keys:
            if key in data:
                value = data[key]
            else:
                value = defaults.get(key, "")
            results.append(value)
        return tuple(results)
    except Exception as e:
        logging.error(f"Error loading defaults: {e}")
        raise ValueError(f"An error occurred while loading the defaults: {e}")
