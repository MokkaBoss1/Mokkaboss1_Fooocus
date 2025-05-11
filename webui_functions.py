###########################################################
#             Fooocus webui_functions                     #
#             extracted by Michael Bayes 18th April 2025  #
###########################################################

import gradio as gr
import random
import os
import json
import time
import shared
import modules.config
import fooocus_version
import modules.html
import modules.async_worker as worker
import modules.constants as constants
import modules.flags as flags
import modules.gradio_hijack as grh
import modules.style_sorter as style_sorter
import modules.meta_parser
import args_manager
import copy
import launch
import pyperclip
import numpy as np
import args_manager
from modules.private_logger import get_current_html_path
from PIL import Image
from extras.inpaint_mask import SAMOptions
from modules.sdxl_styles import legal_style_names
from modules.private_logger import get_current_html_path
from modules.ui_gradio_extensions import reload_javascript
from modules.auth import auth_enabled, check_auth
from modules.util import is_json
import urllib.parse
import re

CONFIG_FILENAME = "theme_config.json"
CONFIG_PATH     = os.path.join(os.path.dirname(__file__), CONFIG_FILENAME)
ADD_FEATURES_FILE = os.path.join(os.path.dirname(__file__), "add_features.json")


def on_feature_toggle(ip_val, pg_val, ro_val, br_val):
    print(f"[DEBUG] on_feature_toggle called with ip_val={ip_val}, pg_val={pg_val}, ro_val={ro_val}, br_val={br_val}")  
    try:
        with open(ADD_FEATURES_FILE, "w") as f:
            json.dump({"ip_toggle": ip_val, "pg_toggle": pg_val, "ro_toggle": ro_val, "br_toggle": br_val}, f)
        print(f"[DEBUG] Wrote to {ADD_FEATURES_FILE}")
    except Exception as e:
        print(f"[ERROR] Writing JSON failed: {e}")
    return gr.update(visible=ip_val), gr.update(visible=pg_val), gr.update(visible=ro_val), gr.update(visible=br_val)




def change_theme(selected):
        # Save new selection (will create or overwrite the JSON)
        with open(CONFIG_PATH, "w") as f:
            json.dump({"theme": selected}, f, indent=2)
        # Return the info message
        return "✅ Saved! Please **restart** the application to apply the new theme."


def clean_choices(raw_choices):
    """
    Turn a list of either:
      - HTML‑wrapped strings, or
      - (raw_label, raw_value) tuples
    into a clean Gradio choices list:
      - If input is str -> returns cleaned str
      - If input is (label, value) -> returns (cleaned_label, value)
    """
    def strip_tags(s):
        return re.sub(r"<[^>]+>", "", str(s)).strip()

    cleaned = []
    for item in raw_choices:
        if isinstance(item, tuple) and len(item) == 2:
            raw_label, raw_value = item
            clean_label = strip_tags(raw_label)
            cleaned.append((clean_label, raw_value))
        else:
            cleaned.append(strip_tags(item))

    return cleaned	
  
def strip_tags(x):
    s = str(x)                             # ← coerce to string
    return re.sub(r'<[^>]+>', '', s)    

# def get_task(*args):
    # # 1) Pull off the placeholder AsyncTask
    # params = list(args)
    # params.pop(0)

    # # 2) Define your mapping from displayed label → internal key
    # label_to_key = {
        # "Upscale / Variation": "uov",
        # "Image Prompt":         "ip",
        # "Inpaint / Outpaint":   "inpaint",
        # "Describe":             "desc",
        # "Enhance":              "enhance",
        # "Metadata":             "metadata"
    # }

    # # 3) Read the raw label in slot 32
    # raw_label = params[32]
    # print(f"[get_task] raw input_mode label at slot 32 = {raw_label!r}", flush=True)

    # # 4) Convert to your internal key
    # key = label_to_key.get(raw_label)
    # if key is None:
        # # Safety fallback
        # print(f"[get_task] WARNING: unrecognized label {raw_label!r}, defaulting to 'uov'", flush=True)
        # key = "uov"

    # # 5) Overwrite slot 32 with the short key
    # print(f"[get_task] overwriting slot 32: {params[32]!r} → {key!r}", flush=True)
    # params[32] = key

    # # 6) (Optional) Log the rest of your parameters
    # print("\n>>> [get_task] Comprehensive parameter dump", flush=True)
    # print(f"    total params after pop = {len(params)}\n", flush=True)
    # for idx, p in enumerate(params):
        # t = type(p).__name__
        # # collapse common types
        # if isinstance(p, (str, bool, int, float)):
            # print(f"[{idx:02d}] {t}: {p!r}", flush=True)
        # elif isinstance(p, (list, tuple)):
            # types = {type(el).__name__: p.count(el) for el in p}
            # print(f"[{idx:02d}] {t} (len={len(p)}): {types}", flush=True)
        # elif hasattr(p, "shape") and hasattr(p, "dtype"):
            # print(f"[{idx:02d}] ndarray shape={p.shape}, dtype={p.dtype}", flush=True)
        # elif hasattr(p, "size") and hasattr(p, "mode"):
            # print(f"[{idx:02d}] PIL.Image size={p.size}, mode={p.mode}", flush=True)
        # elif isinstance(p, dict):
            # print(f"[{idx:02d}] dict keys={list(p.keys())}", flush=True)
        # else:
            # print(f"[{idx:02d}] {t}", flush=True)
    # print(">>> End of parameter dump\n", flush=True)

    # # 7) Hand off to AsyncTask
    # return worker.AsyncTask(args=params)


def get_task(*args):
    # 1) Pull off the placeholder AsyncTask
    params = list(args)
    params.pop(0)

    # 2) Define your mapping from displayed label → internal key
    label_to_key = {
        "Upscale / Variation": "uov",
        "Image Prompt":         "ip",
        "Inpaint / Outpaint":   "inpaint",
        "Describe":             "desc",
        "Enhance":              "enhance",
        "Metadata":             "metadata"
    }

    # 3) Read the raw label in slot 32
    raw_label = params[32]

    # 4) Convert to your internal key
    key = label_to_key.get(raw_label)
    if key is None:
        # Safety fallback
        key = "uov"

    # 5) Overwrite slot 32 with the short key
    params[32] = key

    # 7) Hand off to AsyncTask
    return worker.AsyncTask(args=params)



def generate_clicked(task: worker.AsyncTask):
    import ldm_patched.modules.model_management as model_management

    with model_management.interrupt_processing_mutex:
        model_management.interrupt_processing = False
    # outputs=[progress_html, progress_window, progress_gallery, gallery]

    if len(task.args) == 0:
        return

    execution_start_time = time.perf_counter()
    finished = False

    yield gr.update(visible=True, value=modules.html.make_progress_html(1, 'Waiting for task to start ...')), \
        gr.update(visible=True, value=None), \
        gr.update(visible=False, value=None), \
        gr.update(visible=False)

    worker.async_tasks.append(task)

    while not finished:
        time.sleep(0.01)
        if len(task.yields) > 0:
            flag, product = task.yields.pop(0)
            if flag == 'preview':

                # help bad internet connection by skipping duplicated preview
                if len(task.yields) > 0:  # if we have the next item
                    if task.yields[0][0] == 'preview':   # if the next item is also a preview
                        # print('Skipped one preview for better internet connection.')
                        continue

                percentage, title, image = product
                yield gr.update(visible=True, value=modules.html.make_progress_html(percentage, title)), \
                    gr.update(visible=True, value=image) if image is not None else gr.update(), \
                    gr.update(), \
                    gr.update(visible=False)
            if flag == 'results':
                finished_images = product
                yield gr.update(visible=True), \
                    gr.update(visible=True, value=finished_images[0]), \
                    gr.update(visible=True, value=finished_images), \
                    gr.update(visible=False)
            if flag == 'finish':
                if not args_manager.args.disable_enhance_output_sorting:
                    product = sort_enhance_images(product, task)

                yield gr.update(visible=False), \
                    gr.update(visible=False), \
                    gr.update(visible=False), \
                    gr.update(visible=True, value=product)
                finished = True

                # delete Fooocus temp images, only keep gradio temp images
                if args_manager.args.disable_image_log:
                    for filepath in product:
                        if isinstance(filepath, str) and os.path.exists(filepath):
                            os.remove(filepath)

    execution_time = time.perf_counter() - execution_start_time
    print(f'Total time: {execution_time:.2f} seconds')
    return


def sort_enhance_images(images, task):
    if not task.should_enhance or len(images) <= task.images_to_enhance_count:
        return images

    sorted_images = []
    walk_index = task.images_to_enhance_count

    for index, enhanced_img in enumerate(images[:task.images_to_enhance_count]):
        sorted_images.append(enhanced_img)
        if index not in task.enhance_stats:
            continue
        target_index = walk_index + task.enhance_stats[index]
        if walk_index < len(images) and target_index <= len(images):
            sorted_images += images[walk_index:target_index]
        walk_index += task.enhance_stats[index]

    return sorted_images

def inpaint_mode_change(mode, inpaint_engine_version):
    assert mode in modules.flags.inpaint_options

    # Returns map to:
    # [0] inpaint_additional_prompt,
    # [1] outpaint_selections,
    # [2] example_inpaint_prompts (Examples),
    # [3] inpaint_disable_initial_latent,
    # [4] inpaint_engine,
    # [5] inpaint_strength,
    # [6] inpaint_respective_field

    # DETAIL mode: show the prompt box & examples
    if mode == modules.flags.inpaint_option_detail:
        return [
            gr.update(visible=True),    # show additional prompt
            gr.update(visible=False),   # hide outpaint checkboxes
            gr.update(visible=True),    # show examples
            False,                      # initial_latent disabled
            "None",                     # placeholder engine
            0.5,                        # strength
            0.0                         # respective field
        ]

    if inpaint_engine_version == "empty":
        inpaint_engine_version = modules.config.default_inpaint_engine_version

    # MODIFY mode: show prompt, hide examples
    if mode == modules.flags.inpaint_option_modify:
        return [
            gr.update(visible=True),    # show additional prompt
            gr.update(visible=False),   # hide outpaint checkboxes
            gr.update(visible=False),   # hide examples
            True,                       # initial_latent enabled
            inpaint_engine_version,     # engine
            1.0,                        # strength
            0.0                         # respective field
        ]

    # OUTPAINT (fallback): hide prompt, hide examples, show outpaint
    return [
        gr.update(visible=False),      # hide additional prompt
        gr.update(visible=True),       # show outpaint checkboxes
        gr.update(visible=False),      # hide examples
        False,                         # initial_latent disabled
        inpaint_engine_version,        # engine
        1.0,                           # strength
        0.618                          # respective field
    ]




def stop_clicked(currentTask):
    import ldm_patched.modules.model_management as model_management
    currentTask.last_stop = 'stop'
    if (currentTask.processing):
        model_management.interrupt_current_processing()
    return currentTask

def skip_clicked(currentTask):
    import ldm_patched.modules.model_management as model_management
    currentTask.last_stop = 'skip'
    if (currentTask.processing):
        model_management.interrupt_current_processing()
    return currentTask

def debug_toggle(x):
    print(f"🛠️ toggle called, value = {x!r}")
    return gr.update(visible=x)

def generate_mask(image, mask_model, cloth_category, dino_prompt_text, sam_model, box_threshold, text_threshold, sam_max_detections, dino_erode_or_dilate, dino_debug):
    from extras.inpaint_mask import generate_mask_from_image

    extras = {}
    sam_options = None
    if mask_model == 'u2net_cloth_seg':
        extras['cloth_category'] = cloth_category
    elif mask_model == 'sam':
        sam_options = SAMOptions(
            dino_prompt=dino_prompt_text,
            dino_box_threshold=box_threshold,
            dino_text_threshold=text_threshold,
            dino_erode_or_dilate=dino_erode_or_dilate,
            dino_debug=dino_debug,
            max_detections=sam_max_detections,
            model_type=sam_model
        )

    mask, _, _, _ = generate_mask_from_image(image, mask_model, extras, sam_options)

    return mask

def trigger_show_image_properties(image):
    value = modules.util.get_image_size_info(image, modules.flags.sdxl_aspect_ratios)
    return gr.update(value=value, visible=True)

def trigger_metadata_preview(file):
    parameters, metadata_scheme = modules.meta_parser.read_info_from_image(file)

    results = {}
    if parameters is not None:
        results['parameters'] = parameters

    if isinstance(metadata_scheme, flags.MetadataScheme):
        results['metadata_scheme'] = metadata_scheme.value

    return results

def random_checked(r):
    return gr.update(visible=not r)

def refresh_seed(r, seed_string):
    if r:
        return random.randint(constants.MIN_SEED, constants.MAX_SEED)
    else:
        try:
            seed_value = int(seed_string)
            if constants.MIN_SEED <= seed_value <= constants.MAX_SEED:
                return seed_value
        except ValueError:
            pass
        return random.randint(constants.MIN_SEED, constants.MAX_SEED)

def dev_mode_checked(r):
    return gr.update(visible=r)

def refresh_files_clicked():
    modules.config.update_files()
    results = [gr.update(choices=modules.config.model_filenames)]
    results += [gr.update(choices=['None'] + modules.config.model_filenames)]
    results += [gr.update(choices=[flags.default_vae] + modules.config.vae_filenames)]
    if not args_manager.args.disable_preset_selection:
        results += [gr.update(choices=modules.config.available_presets)]
    for i in range(modules.config.default_max_lora_number):
        results += [gr.update(interactive=True),
                    gr.update(choices=['None'] + modules.config.lora_filenames), gr.update()]
    return results

def play_notification_checked(r, notification):
    return gr.update(visible=r, value=notification if r else None)

def notification_input_changed(notification_input, notification):
    if notification_input:
        notification = notification_input
    return notification

def preset_selection_change(preset, is_generating, inpaint_mode):
    preset_content = modules.config.try_get_preset_content(preset) if preset != 'initial' else {}
    preset_prepared = modules.meta_parser.parse_meta_from_preset(preset_content)

    default_model = preset_prepared.get('base_model')
    previous_default_models = preset_prepared.get('previous_default_models', [])
    checkpoint_downloads = preset_prepared.get('checkpoint_downloads', {})
    embeddings_downloads = preset_prepared.get('embeddings_downloads', {})
    lora_downloads = preset_prepared.get('lora_downloads', {})
    vae_downloads = preset_prepared.get('vae_downloads', {})

    preset_prepared['base_model'], preset_prepared['checkpoint_downloads'] = launch.download_models(
        default_model, previous_default_models, checkpoint_downloads, embeddings_downloads, lora_downloads,
        vae_downloads)

    if 'prompt' in preset_prepared and preset_prepared.get('prompt') == '':
        del preset_prepared['prompt']

    return modules.meta_parser.load_parameter_button_click(json.dumps(preset_prepared), is_generating, inpaint_mode)

def inpaint_engine_state_change(inpaint_engine_version, *args):
    if inpaint_engine_version == 'empty':
        inpaint_engine_version = modules.config.default_inpaint_engine_version

    result = []
    for inpaint_mode in args:
        if inpaint_mode != modules.flags.inpaint_option_detail:
            result.append(gr.update(value=inpaint_engine_version))
        else:
            result.append(gr.update())

    return result

def parse_meta(raw_prompt_txt, is_generating):
    loaded_json = None
    if is_json(raw_prompt_txt):
        loaded_json = json.loads(raw_prompt_txt)

    if loaded_json is None:
        if is_generating:
            return gr.update(), gr.update(), gr.update()
        else:
            return gr.update(), gr.update(visible=True), gr.update(visible=False)

    return json.dumps(loaded_json), gr.update(visible=False), gr.update(visible=True)




def trigger_describe(modes, img, apply_styles):
    describe_prompts = []
    styles = set()

    if flags.describe_type_photo in modes:
        from extras.interrogate import default_interrogator as default_interrogator_photo
        describe_prompts.append(default_interrogator_photo(img))
        styles.update(["Fooocus V2", "Fooocus Enhance", "Fooocus Sharp"])

    if flags.describe_type_anime in modes:
        from extras.wd14tagger import default_interrogator as default_interrogator_anime
        describe_prompts.append(default_interrogator_anime(img))
        styles.update(["Fooocus V2", "Fooocus Masterpiece"])

    if len(styles) == 0 or not apply_styles:
        styles = gr.update()
    else:
        styles = list(styles)

    if len(describe_prompts) == 0:
        describe_prompt = gr.update()
    else:
        describe_prompt = ', '.join(describe_prompts)

    return describe_prompt, styles    
    
def trigger_auto_describe(mode, img, prompt, apply_styles):
    # keep prompt if not empty
    if prompt == '':
        return trigger_describe(mode, img, apply_styles)
    return gr.update(), gr.update()

def dump_default_english_config():
    from modules.localization import dump_english_config
    dump_english_config(grh.all_components)

def paste_clipboard():
    try:
        return pyperclip.paste()
    except Exception as e:
        return f"Clipboard error: {str(e)}"    