###########################################################
#         1 Start of Imports and Model References         #
###########################################################
import pathlib, urllib
import gradio as gr
from pathlib import Path
import random
import os
import json
import time
import shared
import subprocess
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
from extras.inpaint_mask import SAMOptions
import re
from modules.sdxl_styles import legal_style_names
from modules.private_logger import get_current_html_path
from modules.ui_gradio_extensions import reload_javascript
from modules.auth import auth_enabled, check_auth
from modules.util import is_json
import math
from webui_functions import *

CONFIG_FILENAME = "theme_config.json"
CONFIG_PATH     = os.path.join(os.path.dirname(__file__), CONFIG_FILENAME)


#####################################################################
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

# ——— Persisted feature‐toggle state —————————————————————————————
ADD_FEATURES_FILE = os.path.join(os.path.dirname(__file__), "add_features.json")

try:
    with open(ADD_FEATURES_FILE, "r") as f:
        _saved = json.load(f)
    ip_toggle_default = _saved.get("ip_toggle", False)
    pg_toggle_default = _saved.get("pg_toggle", False)
    ro_toggle_default = _saved.get("ro_toggle", False)
    br_toggle_default = _saved.get("br_toggle", False)
except (FileNotFoundError, json.JSONDecodeError):
    # first run: create file with both off
    ip_toggle_default = False
    pg_toggle_default = False
    ro_toggle_default = False
    br_toggle_default = False
    with open(ADD_FEATURES_FILE, "w") as f:
        json.dump({"ip_toggle": ip_toggle_default, "pg_toggle": pg_toggle_default, "ro_toggle": ro_toggle_default, "br_toggle": br_toggle_default}, f)




###########################################################
#        2 Start of locally requried functions            #
###########################################################

def ip_advance_checked(x):
    return [gr.update(visible=x)] * len(ip_ad_cols) + \
        [flags.default_ip] * len(ip_types) + \
        [flags.default_parameters[flags.default_ip][0]] * len(ip_stops) + \
        [flags.default_parameters[flags.default_ip][1]] * len(ip_weights)

def trigger_metadata_import(file, state_is_generating):
    parameters, metadata_scheme = modules.meta_parser.read_info_from_image(file)
    if parameters is None:
        print('Could not find metadata in the image!')
        parsed_parameters = {}
    else:
        metadata_parser = modules.meta_parser.get_metadata_parser(metadata_scheme)
        parsed_parameters = metadata_parser.to_json(parameters)

    return modules.meta_parser.load_parameter_button_click(parsed_parameters, state_is_generating, inpaint_mode)

###########################################################
#           2 End of locally required functions           #
###########################################################

###########################################################
#           3 Start of generate_clicked callback          #
###########################################################

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
                yield gr.update(visible=True), \
                    gr.update(visible=True), \
                    gr.update(visible=True, value=product), \
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

###########################################################
#           3 End of generate_clicked callback            #
###########################################################

###########################################################
#           4 Start of sort_enhance_images helper         #
###########################################################

###########################################################
#           4 End of sort_enhance_images helper           #
###########################################################

###########################################################
#        5 Start of inpaint_mode_change function          #
###########################################################

    if inpaint_engine_version == 'empty':
        inpaint_engine_version = modules.config.default_inpaint_engine_version

    if mode == modules.flags.inpaint_option_modify:
        return [
            gr.update(visible=True), gr.update(visible=False, value=[]),
            gr.Examples.update(visible=False, samples=modules.config.example_inpaint_prompts),
            True, inpaint_engine_version, 1.0, 0.0
        ]

    return [
        gr.update(visible=False, value=''), gr.update(visible=True),
        gr.Examples.update(visible=False, samples=modules.config.example_inpaint_prompts),
        False, inpaint_engine_version, 1.0, 0.618
    ]

###########################################################
#         5 End of inpaint_mode_change function           #
###########################################################

###########################################################
#       6 Start of reload_javascript() call               #
###########################################################

reload_javascript()

###########################################################
#       6 End of reload_javascript() call                 #
###########################################################

###########################################################
#   7 Start of Title & Gradio root initialization         #
###########################################################

title = f'Fooocus {fooocus_version.version}'

if isinstance(args_manager.args.preset, str):
    title += ' ' + args_manager.args.preset


shared.gradio_root = gr.Blocks(theme=theme, title=title) .queue()


###########################################################
#    7 End of Title & Gradio root initialization          #
###########################################################

###########################################################
#  8 Start of UI Definition (with shared.gradio_root:)    #
###########################################################

    ###########################################################
    #      8.1 Start of State Declarations                    #
    ###########################################################

with shared.gradio_root:
    currentTask = gr.State(worker.AsyncTask(args=[]))
    inpaint_engine_state = gr.State('empty')
    mode = gr.State(value=modules.config.default_selected_image_input_tab_id)
    
    # with gr.Row():
        # gr.Image(
            # value="logo1.png",            # path or URL to your logo
            # show_label=False,
            # interactive=False,
            # elem_id="app-logo",
            # height=64                  # adjust as needed
        # )

    ###########################################################
    #      8.1 End of State Declarations                      #
    ###########################################################

    ###########################################################
    #      8.2 Start of Main Layout (top-level Row)           #
    ###########################################################

        ###########################################################
        #         8.2.1 Start of Preview & Progress panels        #
        ###########################################################

    with gr.Row():
        with gr.Column(scale=2):
            # Inject CSS scoped only to the preview window
            gr.HTML(
                """
                <style>
                  /* Only affect the IMG inside the #preview-pane container */
                  #preview-pane img {
                    object-fit: contain !important;
                    height: 350px !important;
                    width: auto !important;
                  }
                </style>
                """
            )

            with gr.Row():
                progress_window = grh.Image(
                    label="Preview",
                    show_label=True,
                    visible=False,
                    elem_id="preview-pane",     # <-- unique ID
                    elem_classes=["main_view"]
                )

                progress_gallery = gr.Gallery(
                    label="Finished Images",
                    show_label=True,
                    object_fit="contain",
                    height=500,
                    visible=False,
                    elem_classes=["main_view", "image_gallery"]
                )

            progress_html = gr.HTML(
                value=modules.html.make_progress_html(32, "Progress 32%"),
                visible=False,
                container=True,           # <-- wrap in its own div
                elem_id="progress-bar",
                elem_classes="progress-bar"
            )


        ###########################################################
        #         8.2.2 Start of Finished-images Gallery          #
        ###########################################################

            with gr.Accordion("🖼️ Output Images"):
                gallery = gr.Gallery(label='Gallery', show_label=False, object_fit='contain', visible=True, height=500,
                                     elem_classes=['resizable_area', 'main_view', 'final_gallery', 'image_gallery'],
                                     elem_id='final_gallery')

        ###########################################################
        #         8.2.2 End of Finished-images Gallery            #
        ###########################################################  

    ###########################################################
    #      8.2 End of Main Layout (top-level Row)             #
    ###########################################################                               

    ###########################################################
    #          8.3 Start of Prompt input & buttons            #
    ###########################################################

        ###########################################################
        #     8.3.1 Start of Generate / Reset / Load / Skip       #
        ###########################################################

 
            with gr.Accordion("👩 Positive Prompt"):
                with gr.Column(scale=17):
                    prompt = gr.Textbox(show_label=False, placeholder="Type prompt here or paste parameters.", elem_id='positive_prompt',
                                        autofocus=True, lines=3)

                    default_prompt = modules.config.default_prompt
                    if isinstance(default_prompt, str) and default_prompt != '':
                        shared.gradio_root.load(lambda: default_prompt, outputs=prompt)
            with gr.Row():
                paste_clipboard_button = gr.Button("Paste Clipboard", elem_id="paste_clipboard_button", elem_classes="flex items-center justify-center h-6 px-3", visible=True)
                generate_button = gr.Button(value="fooocus", elem_classes="flex items-center justify-center h-6 px-3", variant="primary", elem_id='generate_button', visible=True)
                reset_button = gr.Button(value="Reconnect", elem_classes="flex items-center justify-center h-6 px-3", elem_id='reset_button', visible=False)
                load_parameter_button = gr.Button(value="Load Parameters", elem_classes="flex items-center justify-center h-6 px-3", elem_id='load_parameter_button', visible=False)
                skip_button = gr.Button(value="Skip", elem_classes="flex items-center justify-center h-6 px-3", elem_id='skip_button', visible=False)
                stop_button = gr.Button(value="Stop", elem_classes="flex items-center justify-center h-6 px-3", elem_id='stop_button', visible=False)

        ###########################################################
        #       8.3.1 End of Generate / Reset / Load / Skip       #
        ###########################################################

        ###########################################################
        #     8.3.2 Start of Stop / Skip click handlers           #
        ##########################################################
        
                paste_clipboard_button.click(fn=paste_clipboard, outputs=prompt)
                stop_button.click(stop_clicked, inputs=currentTask, outputs=currentTask, queue=False, show_progress=False, js='cancelGenerateForever')
                skip_button.click(skip_clicked, inputs=currentTask, outputs=currentTask, queue=False, show_progress=False)

        ###########################################################
        #         8.3.2 End of Stop / Skip click handlers         #
        ########################################################### 

    ###########################################################
    #            8.3 End of Prompt input & buttons            #
    ###########################################################

    ###########################################################
    #               8.4 Start of Advanced check row           #
    ###########################################################                   
                    
            with gr.Row(elem_classes='advanced_check_row'):
                input_image_checkbox = gr.Checkbox(label='Inputs', value=modules.config.default_image_prompt_checkbox, container=False, elem_classes=['min_check', 'whitespace-nowrap'])
                enhance_checkbox = gr.Checkbox(label='Enhanced', value=modules.config.default_enhance_checkbox, container=False, elem_classes='min_check')
                advanced_checkbox = gr.Checkbox(label='Advanced', value=True, container=False, elem_classes='min_check', visible=False)
                
    ###########################################################
    #               8.4 End of Advanced check row             #
    ###########################################################                 

    ###########################################################
    #               8.5 Start of Image input panel            #
    ###########################################################

        ###########################################################
        #          8.5.1 Start of Upscale or Variation tab        #
        ###########################################################
                
                
            with gr.Row(visible=modules.config.default_image_prompt_checkbox) as image_input_panel:
                with gr.Tabs(selected=modules.config.default_selected_image_input_tab_id, elem_id="image_input_tabs") as image_tabs:
                    
                    
                    # 8.5.1 Upscale or Variation tab
                    with gr.TabItem("Upscale or Variation", id="uov")as uov_tab:                                            
                        with gr.Row():
                            with gr.Column():
                                uov_input_image = grh.Image(
                                    label='Image',
                                    source='upload',
                                    type='filepath',
                                    height=350,
                                    show_label=False
                                )
                            with gr.Column():
                                uov_method = gr.Radio(
                                    label='Upscale or Variation:',
                                    choices=flags.uov_list,
                                    value=modules.config.default_uov_method
                                )
                                gr.HTML(
                                    '<a href="https://github.com/lllyasviel/Fooocus/discussions/390" '
                                    'target="_blank">📄 Documentation</a>'
                                )
                        uov_tab.select(lambda: "uov", inputs=[], outputs=[mode], queue=False)
                    
                    
                    # 8.5.2 Image Prompt tab
                    with gr.TabItem("Image Prompt", id="ip_tab") as ip_tab:
                        # prepare lists for downstream wiring
                        ip_images = []
                        ip_types  = []
                        ip_stops  = []
                        ip_weights = []
                        ip_ctrls  = []
                        ip_ad_cols = []

                        NUM = modules.config.default_controlnet_image_count  # e.g. 4
                        COLS = 2                                            # 2 per row
                        rows = math.ceil(NUM / COLS)

                        img_idx = 1
                        for _ in range(rows):
                            with gr.Row():
                                for _ in range(COLS):
                                    if img_idx > NUM:
                                        break
                                    with gr.Column():
                                        # fixed container size, keeps all 4 identical
                                        ip_image = grh.Image(
                                            label="Image",
                                            source="upload",
                                            type="filepath",
                                            show_label=False,
                                            height=350,
                                            width=650,
                                            value=modules.config.default_ip_images[img_idx]
                                        )
                                        ip_images.append(ip_image)
                                        ip_ctrls.append(ip_image)

                                        # advanced controls in a nested column
                                        with gr.Column(visible=modules.config.default_image_prompt_advanced_checkbox) as ad_col:
                                            with gr.Row():
                                                ip_stop = gr.Slider(
                                                    label="Stop At",
                                                    minimum=0.0,
                                                    maximum=1.0,
                                                    step=0.001,
                                                    value=modules.config.default_ip_stop_ats[img_idx]
                                                )
                                                ip_stops.append(ip_stop)
                                                ip_ctrls.append(ip_stop)

                                                ip_weight = gr.Slider(
                                                    label="Weight",
                                                    minimum=0.0,
                                                    maximum=2.0,
                                                    step=0.001,
                                                    value=modules.config.default_ip_weights[img_idx]
                                                )
                                                ip_weights.append(ip_weight)
                                                ip_ctrls.append(ip_weight)

                                            ip_type = gr.Radio(
                                                label="Type",
                                                choices=flags.ip_list,
                                                value=modules.config.default_ip_types[img_idx],
                                                container=False
                                            )
                                            ip_types.append(ip_type)
                                            ip_ctrls.append(ip_type)

                                            ip_type.change(
                                                lambda x: flags.default_parameters[x],
                                                inputs=[ip_type],
                                                outputs=[ip_stop, ip_weight],
                                                queue=False,
                                                show_progress=False
                                            )

                                        ip_ad_cols.append(ad_col)
                                    img_idx += 1

                        # wire up tab selection
                        ip_tab.select(lambda: "ip", inputs=[], outputs=[mode], queue=False)

                        # advanced toggle checkbox
                        ip_advanced = gr.Checkbox(
                            label="Advanced",
                            value=modules.config.default_image_prompt_advanced_checkbox,
                            container=False
                        )
                        gr.HTML(
                            '* "Image Prompt" is powered by Fooocus Image Mixture Engine (v1.0.1). '
                            '<a href="https://github.com/lllyasviel/Fooocus/discussions/557" '
                            'target="_blank">📄 Documentation</a>'
                        )
                        ip_advanced.change(
                            ip_advance_checked,
                            inputs=[ip_advanced],
                            outputs=ip_ad_cols + ip_types + ip_stops + ip_weights,
                            queue=False,
                            show_progress=False
                        )

         
                    # 8.5.3 Inpaint or Outpaint tab
                    with gr.TabItem("Inpaint or Outpaint", id="inpaint_tab")as inpaint_tab:
                        with gr.Row():
                            with gr.Column():
                                inpaint_input_image = gr.ImageEditor(
                                    label='Image',
                                    sources=['upload'],
                                    type='filepath',
                                    brush=gr.Brush(colors=["#FFFFFF"]),
                                    height=500,
                                    elem_id='inpaint_canvas',
                                    show_label=False
                                )
                                inpaint_advanced_masking_checkbox = gr.Checkbox(
                                    label='Enable Advanced Masking Features',
                                    value=modules.config.default_inpaint_advanced_masking_checkbox
                                )
                                inpaint_mode = gr.Dropdown(
                                    choices=modules.flags.inpaint_options,
                                    value=modules.config.default_inpaint_method,
                                    label='Method'
                                )
                                inpaint_additional_prompt = gr.Textbox(
                                    placeholder="Describe what you want to inpaint.",
                                    elem_id='inpaint_additional_prompt',
                                    label='Inpaint Additional Prompt',
                                    visible=False
                                )
                                outpaint_selections = gr.CheckboxGroup(
                                    choices=['Left', 'Right', 'Top', 'Bottom'],
                                    value=[],
                                    label='Outpaint Direction'
                                )
                                example_inpaint_prompts = gr.Examples(
                                    examples=modules.config.example_inpaint_prompts,
                                    label='Additional Prompt Quick List',
                                    inputs=[inpaint_additional_prompt],
                                    visible=False
                                )
                                gr.HTML(
                                    '* Powered by Fooocus Inpaint Engine '
                                    '<a href="https://github.com/lllyasviel/Fooocus/discussions/414" target="_blank">📄 Documentation</a>'
                                )

                            with gr.Column(visible=modules.config.default_inpaint_advanced_masking_checkbox) as inpaint_mask_generation_col:
                                inpaint_mask_image = gr.ImageEditor(
                                    label='Mask Upload',
                                    type='filepath',
                                    brush=gr.Brush(colors=["#FFFFFF"]),
                                    height=500,
                                    elem_id='inpaint_mask_canvas',
                                    show_label=False
                                )
                                invert_mask_checkbox = gr.Checkbox(
                                    label='Invert Mask When Generating',
                                    value=modules.config.default_invert_mask_checkbox
                                )
                                inpaint_mask_model = gr.Dropdown(
                                    label='Mask generation model',
                                    choices=flags.inpaint_mask_models,
                                    value=modules.config.default_inpaint_mask_model
                                )
                                inpaint_mask_cloth_category = gr.Dropdown(
                                    label='Cloth category',
                                    choices=flags.inpaint_mask_cloth_category,
                                    value=modules.config.default_inpaint_mask_cloth_category,
                                    visible=False
                                )
                                inpaint_mask_dino_prompt_text = gr.Textbox(
                                    label='Detection prompt',
                                    value='',
                                    visible=False,
                                    info='Use singular whenever possible',
                                    placeholder='Describe what you want to detect.'
                                )
                                example_inpaint_mask_dino_prompt_text = gr.Examples(
                                    examples=modules.config.example_enhance_detection_prompts,
                                    label='Detection Prompt Quick List',
                                    inputs=[inpaint_mask_dino_prompt_text],
                                    visible=modules.config.default_inpaint_mask_model == 'sam'
                                )
                                with gr.Accordion("Advanced options", visible=False, open=False) as inpaint_mask_advanced_options:
                                    inpaint_mask_sam_model = gr.Dropdown(
                                        label='SAM model',
                                        choices=flags.inpaint_mask_sam_model,
                                        value=modules.config.default_inpaint_mask_sam_model
                                    )
                                    inpaint_mask_box_threshold = gr.Slider(
                                        label="Box Threshold",
                                        minimum=0.0,
                                        maximum=1.0,
                                        value=0.3,
                                        step=0.05
                                    )
                                    inpaint_mask_text_threshold = gr.Slider(
                                        label="Text Threshold",
                                        minimum=0.0,
                                        maximum=1.0,
                                        value=0.25,
                                        step=0.05
                                    )
                                    inpaint_mask_sam_max_detections = gr.Slider(
                                        label="Maximum number of detections",
                                        info="Set to 0 to detect all",
                                        minimum=0,
                                        maximum=10,
                                        value=modules.config.default_sam_max_detections,
                                        step=1,
                                        interactive=True
                                    )
                                generate_mask_button = gr.Button(value='Generate mask from image')
                        inpaint_tab.select(lambda: "inpaint", inputs=[], outputs=[mode], queue=False)
                                    


                    # 8.5.4 Describe tab
                    with gr.TabItem("Describe", id="describe_tab")as describe_tab:
                        with gr.Row():
                            with gr.Column():
                                describe_input_image = grh.Image(
                                    label='Image',
                                    source='upload',
                                    type='filepath',
                                    height=350,
                                    show_label=False
                                )
                            with gr.Column():
                                describe_methods = gr.CheckboxGroup(
                                    label='Content Type',
                                    choices=flags.describe_types,
                                    value=modules.config.default_describe_content_type
                                )
                                describe_apply_styles = gr.Checkbox(
                                    label='Apply Styles',
                                    value=modules.config.default_describe_apply_prompts_checkbox
                                )
                                describe_btn = gr.Button(value='Describe this Image into Prompt')
                                describe_image_size = gr.Textbox(
                                    label='Image Size and Recommended Size',
                                    elem_id='describe_image_size',
                                    visible=False
                                )
                                gr.HTML(
                                    '<a href="https://github.com/lllyasviel/Fooocus/discussions/1363" target="_blank">📄 Documentation</a>'
                                )

                                describe_input_image.upload(
                                    trigger_show_image_properties,
                                    inputs=[describe_input_image],
                                    outputs=[describe_image_size],
                                    show_progress=False,
                                    queue=False
                                )
                        describe_tab.select(lambda: "desc", inputs=[], outputs=[mode], queue=False)

                    # 8.5.5 Enhance tab
                    with gr.TabItem("Enhance", id="enhance_tab")as enhance_tab:
                        with gr.Row():
                            with gr.Column():
                                enhance_input_image = grh.Image(
                                    label='Use with Enhance, skips image generation',
                                    source='upload',
                                    height=350,
                                    type='filepath'
                                )
                                gr.HTML(
                                    '<a href="https://github.com/lllyasviel/Fooocus/discussions/3281" target="_blank">📄 Documentation</a>'
                                )
                        enhance_tab.select(lambda: "enhance", inputs=[], outputs=[mode], queue=False)


                    # 8.5.6 Metadata tab
                    with gr.TabItem("Metadata", id="metadata_tab")as metadata_tab:
                        with gr.Column():
                            metadata_input_image = grh.Image(
                                label='For images created by Fooocus',
                                source='upload',
                                height=350,
                                type='pil'
                            )
                            metadata_json = gr.JSON(label='Metadata')
                            metadata_import_button = gr.Button(value='Apply Metadata')

                        metadata_input_image.upload(
                            trigger_metadata_preview,
                            inputs=[metadata_input_image],
                            outputs=[metadata_json],
                            queue=False,
                            show_progress=True
                        )
                        metadata_tab.select(lambda: "metadata", inputs=[], outputs=[mode], queue=False)
                        


    ###########################################################
    #  8.9 Start of Enhance Input Panel (when “Enhance” on)   #
    ###########################################################

        ###########################################################
        #      8.9.1 Start of Upscale or Variation sub-tab        #
        ###########################################################

            with gr.Row(visible=modules.config.default_enhance_checkbox) as enhance_input_panel:
                with gr.Tabs() as enhance_tabs:
                    # Upscale/Variation sub‐tab
                    with gr.Tab(label='Upscale or Variation', id='enhance_uov'):
                        with gr.Row():
                            with gr.Column():
                                enhance_uov_method = gr.Radio(
                                    label='Upscale or Variation:',
                                    choices=flags.uov_list,
                                    value=modules.config.default_enhance_uov_method
                                )
                                enhance_uov_processing_order = gr.Radio(
                                    label='Order of Processing',
                                    info='Use before to enhance small details and after large areas.',
                                    choices=flags.enhancement_uov_processing_order,
                                    value=modules.config.default_enhance_uov_processing_order
                                )
                                enhance_uov_prompt_type = gr.Radio(
                                    label='Prompt',
                                    info='Choose which prompt to use for Upscale or Variation.',
                                    choices=flags.enhancement_uov_prompt_types,
                                    value=modules.config.default_enhance_uov_prompt_type,
                                    visible=(modules.config.default_enhance_uov_processing_order == flags.enhancement_uov_after)
                                )
                                enhance_uov_processing_order.change(
                                    lambda x: gr.update(visible=x == flags.enhancement_uov_after),
                                    inputs=enhance_uov_processing_order,
                                    outputs=enhance_uov_prompt_type,
                                    queue=False,
                                    show_progress=False
                                )
                                gr.HTML(
                                    '<a href="https://github.com/lllyasviel/Fooocus/discussions/3281" '
                                    'target="_blank">📄 Documentation</a>'
                                )

        ###########################################################
        #      8.9.2 Start of Enhancement #1…#n sub-tabs          #
        ###########################################################


                    enhance_ctrls = []
                    enhance_inpaint_mode_ctrls = []
                    enhance_inpaint_engine_ctrls = []
                    enhance_inpaint_update_ctrls = []
                    for index in range(modules.config.default_enhance_tabs):
                        with gr.Tab(label=f'#{index + 1}', id=f'enhance_{index+1}') as enhance_tab_item:
                            enhance_enabled = gr.Checkbox(label='Enable', value=False, elem_classes='min_check',
                                                          container=False)

                            enhance_mask_dino_prompt_text = gr.Textbox(label='Detection prompt',
                                                                       info='Use singular whenever possible',
                                                                       placeholder='Describe what you want to detect.',
                                                                       interactive=True,
                                                                       visible=modules.config.default_enhance_inpaint_mask_model == 'sam')
                            example_enhance_mask_dino_prompt_text = gr.Examples(
                                examples=modules.config.example_enhance_detection_prompts,
                                label='Detection Prompt Quick List',
                                inputs=[enhance_mask_dino_prompt_text],
                                visible=modules.config.default_enhance_inpaint_mask_model == 'sam')
                            # example_enhance_mask_dino_prompt_text.click(lambda x: x[0],
                                                                        # inputs=example_enhance_mask_dino_prompt_text,
                                                                        # outputs=enhance_mask_dino_prompt_text,
                                                                        # show_progress=False, queue=False)

                            enhance_prompt = gr.Textbox(label="Enhancement positive prompt",
                                                        placeholder="Uses original prompt instead if empty.",
                                                        elem_id='enhance_prompt')
                            enhance_negative_prompt = gr.Textbox(label="Enhancement negative prompt",
                                                                 placeholder="Uses original negative prompt instead if empty.",
                                                                 elem_id='enhance_negative_prompt')

                            with gr.Accordion("Detection", open=False):
                                enhance_mask_model = gr.Dropdown(label='Mask generation model',
                                                                 choices=flags.inpaint_mask_models,
                                                                 value=modules.config.default_enhance_inpaint_mask_model)
                                enhance_mask_cloth_category = gr.Dropdown(label='Cloth category',
                                                                          choices=flags.inpaint_mask_cloth_category,
                                                                          value=modules.config.default_inpaint_mask_cloth_category,
                                                                          visible=modules.config.default_enhance_inpaint_mask_model == 'u2net_cloth_seg',
                                                                          interactive=True)

                                with gr.Accordion("SAM Options",
                                                  visible=modules.config.default_enhance_inpaint_mask_model == 'sam',
                                                  open=False) as sam_options:
                                    enhance_mask_sam_model = gr.Dropdown(label='SAM model',
                                                                         choices=flags.inpaint_mask_sam_model,
                                                                         value=modules.config.default_inpaint_mask_sam_model,
                                                                         interactive=True)
                                    enhance_mask_box_threshold = gr.Slider(label="Box Threshold", minimum=0.0,
                                                                           maximum=1.0, value=0.3, step=0.05,
                                                                           interactive=True)
                                    enhance_mask_text_threshold = gr.Slider(label="Text Threshold", minimum=0.0,
                                                                            maximum=1.0, value=0.25, step=0.05,
                                                                            interactive=True)
                                    enhance_mask_sam_max_detections = gr.Slider(label="Maximum number of detections",
                                                                                info="Set to 0 to detect all",
                                                                                minimum=0, maximum=10,
                                                                                value=modules.config.default_sam_max_detections,
                                                                                step=1, interactive=True)

                            with gr.Accordion("Inpaint", visible=True, open=False):
                                enhance_inpaint_mode = gr.Dropdown(choices=modules.flags.inpaint_options,
                                                                   value=modules.config.default_inpaint_method,
                                                                   label='Method', interactive=True)
                                enhance_inpaint_disable_initial_latent = gr.Checkbox(
                                    label='Disable initial latent in inpaint', value=False)
                                enhance_inpaint_engine = gr.Dropdown(label='Inpaint Engine',
                                                                     value=modules.config.default_inpaint_engine_version,
                                                                     choices=flags.inpaint_engine_versions,
                                                                     info='Version of Fooocus inpaint model. If set, use performance Quality or Speed (no performance LoRAs) for best results.')
                                enhance_inpaint_strength = gr.Slider(label='Inpaint Denoising Strength',
                                                                     minimum=0.0, maximum=1.0, step=0.001,
                                                                     value=1.0,
                                                                     info='Same as the denoising strength in A1111 inpaint. '
                                                                          'Only used in inpaint, not used in outpaint. '
                                                                          '(Outpaint always use 1.0)')
                                enhance_inpaint_respective_field = gr.Slider(label='Inpaint Respective Field',
                                                                             minimum=0.0, maximum=1.0, step=0.001,
                                                                             value=0.618,
                                                                             info='The area to inpaint. '
                                                                                  'Value 0 is same as "Only Masked" in A1111. '
                                                                                  'Value 1 is same as "Whole Image" in A1111. '
                                                                                  'Only used in inpaint, not used in outpaint. '
                                                                                  '(Outpaint always use 1.0)')
                                enhance_inpaint_erode_or_dilate = gr.Slider(label='Mask Erode or Dilate',
                                                                            minimum=-64, maximum=64, step=1, value=0,
                                                                            info='Positive value will make white area in the mask larger, '
                                                                                 'negative value will make white area smaller. '
                                                                                 '(default is 0, always processed before any mask invert)')
                                enhance_mask_invert = gr.Checkbox(label='Invert Mask', value=False)

                            gr.HTML('<a href="https://github.com/lllyasviel/Fooocus/discussions/3281" target="_blank">\U0001F4D4 Documentation</a>')

                        enhance_ctrls += [
                            enhance_enabled,
                            enhance_mask_dino_prompt_text,
                            enhance_prompt,
                            enhance_negative_prompt,
                            enhance_mask_model,
                            enhance_mask_cloth_category,
                            enhance_mask_sam_model,
                            enhance_mask_text_threshold,
                            enhance_mask_box_threshold,
                            enhance_mask_sam_max_detections,
                            enhance_inpaint_disable_initial_latent,
                            enhance_inpaint_engine,
                            enhance_inpaint_strength,
                            enhance_inpaint_respective_field,
                            enhance_inpaint_erode_or_dilate,
                            enhance_mask_invert
                        ]

                        enhance_inpaint_mode_ctrls += [enhance_inpaint_mode]
                        enhance_inpaint_engine_ctrls += [enhance_inpaint_engine]

                        enhance_inpaint_update_ctrls += [[
                            enhance_inpaint_mode, enhance_inpaint_disable_initial_latent, enhance_inpaint_engine,
                            enhance_inpaint_strength, enhance_inpaint_respective_field
                        ]]

                        # enhance_inpaint_mode.change(inpaint_mode_change, inputs=[enhance_inpaint_mode, inpaint_engine_state], outputs=[
                            # inpaint_additional_prompt, outpaint_selections, example_inpaint_prompts,
                            # enhance_inpaint_disable_initial_latent, enhance_inpaint_engine,
                            # enhance_inpaint_strength, enhance_inpaint_respective_field
                        # ], show_progress=False, queue=False)
                        enhance_inpaint_mode.change(
                            inpaint_mode_change,
                            inputs=[enhance_inpaint_mode, inpaint_engine_state],
                            outputs=[
                                inpaint_additional_prompt,
                                outpaint_selections,
                                example_inpaint_prompts.dataset,
                                enhance_inpaint_disable_initial_latent,
                                enhance_inpaint_engine,
                                enhance_inpaint_strength,
                                enhance_inpaint_respective_field
                            ],
                            show_progress=False,
                            queue=False
                        )                        

                        # enhance_mask_model.change(
                            # lambda x: [gr.update(visible=x == 'u2net_cloth_seg')] +
                                      # [gr.update(visible=x == 'sam')] * 2 +
                                      # [gr.Examples.update(visible=x == 'sam',
                                                         # samples=modules.config.example_enhance_detection_prompts)],
                            # inputs=enhance_mask_model,
                            # outputs=[enhance_mask_cloth_category, enhance_mask_dino_prompt_text, sam_options,
                                     # example_enhance_mask_dino_prompt_text],
                            # queue=False, show_progress=False)
                            
                        enhance_mask_model.change(
                            lambda x: [
                                gr.update(visible=x == 'u2net_cloth_seg'),
                                gr.update(visible=x == 'sam'),
                                gr.update(visible=x == 'sam'),
                                gr.Examples.update(
                                    visible=x == 'sam',
                                    examples=modules.config.example_enhance_detection_prompts
                                )
                            ],
                            inputs=[enhance_mask_model],
                            outputs=[
                                enhance_mask_cloth_category,
                                enhance_mask_dino_prompt_text,
                                sam_options,
                                example_enhance_mask_dino_prompt_text.dataset
                            ],
                            queue=False,
                            show_progress=False
                        )                            

            switch_js = "(x) => {if(x){viewer_to_bottom(100);viewer_to_bottom(500);}else{viewer_to_top();} return x;}"
            down_js = "() => {viewer_to_bottom();}"

            # input_image_checkbox.change(lambda x: gr.update(visible=x), inputs=input_image_checkbox,
                                        # outputs=image_input_panel, queue=False, show_progress=False, js=switch_js)
            # show/hide the "Image Input" panel
            input_image_checkbox.change(
                fn=lambda x: gr.update(visible=x),
                #fn=debug_toggle,
                inputs=[input_image_checkbox],
                outputs=[image_input_panel],
                queue=False,
                show_progress=False
            )                                            
                                            
                                         
            ip_advanced.change(lambda: None, queue=False, show_progress=False, js=down_js)

            uov_tab.select(lambda: 'uov',        outputs=mode, queue=False, js=down_js, show_progress=False)
            ip_tab.select(lambda: 'ip',          outputs=mode, queue=False, js=down_js, show_progress=False)
            inpaint_tab.select(lambda: 'inpaint',outputs=mode, queue=False, js=down_js, show_progress=False)
            describe_tab.select(lambda: 'desc',  outputs=mode, queue=False, js=down_js, show_progress=False)
            enhance_tab.select(lambda: 'enhance',outputs=mode, queue=False, js=down_js, show_progress=False)
            metadata_tab.select(lambda: 'metadata',outputs=mode,queue=False,js=down_js,show_progress=False)
            
            # show/hide the "Enhance" panel
            enhance_checkbox.change(
                fn=lambda x: gr.update(visible=x),
                #fn=debug_toggle,
                inputs=[enhance_checkbox],
                outputs=[enhance_input_panel],
                queue=False,
                show_progress=False
            )                                        

        ###########################################################
        #      8.9.2 End of Enhancement #1…#n sub-tabs            #
        ###########################################################

    ###########################################################
    #  8.9 End of Enhance Input Panel (when “Enhance” on)     #
    ###########################################################

###########################################################
#        9 Start of Advanced-column (right side)          #
###########################################################

    
        with gr.Column(scale=1, visible=True) as advanced_column:
            with gr.Tab(label='Settings'):

                # ── Preset ──────────────────────────────────────────
                if not args_manager.args.disable_preset_selection:
                    preset_selection = gr.Dropdown(
                        label='Preset',
                        choices=modules.config.available_presets,
                        value=args_manager.args.preset if args_manager.args.preset else "initial",
                        interactive=True
                    )

                # ── Performance Accordion ────────────────────────────
                clean_perf = clean_choices(modules.flags.performance_selections)
                with gr.Accordion(label="Performance", open=False):
                    performance_selection = gr.Radio(
                        choices=clean_perf,
                        value=clean_choices([modules.config.default_performance])[0],
                        info="* = restricted feature set, intermediate results disabled",
                        elem_classes="performance_selections",
                    )

                # ── Aspect Ratios Accordion ──────────────────────────
                clean_choices = [
                    strip_tags(label)
                    for label in modules.config.available_aspect_ratios_labels
                ]
                clean_default = strip_tags(modules.config.default_aspect_ratio)
                with gr.Accordion(
                    label='Aspect Ratios',
                    open=False,
                    elem_id='aspect_ratios_accordion'
                ):
                    aspect_ratios_selection = gr.Radio(
                        label='Aspect Ratios',
                        show_label=False,
                        choices=clean_choices,
                        value=clean_default,
                        info='width × height',
                        elem_classes='aspect_ratios'
                    )
                    aspect_ratios_selection.change(
                        lambda x: None,
                        inputs=[aspect_ratios_selection],
                        queue=False,
                        show_progress=False,
                        js='(x)=>{refresh_aspect_ratios_label(x);}'
                    )

                # dummy load so the Aspect Ratios label renders correctly on startup
                # ── Manual “Input Mode” Selector ─────────────────────
                mode_labels = {
                    "Upscale / Variation": "uov",
                    "Image Prompt":         "ip",
                    "Inpaint / Outpaint":   "inpaint",
                    "Describe":             "desc",
                    "Enhance":              "enhance",
                    "Metadata":             "metadata"
                }

                input_mode = gr.Radio(
                    label="Input Mode",
                    choices=list(mode_labels.keys()),   # show the nice labels
                    value=list(mode_labels.keys())[  # pick the default label
                        list(mode_labels.values()).index(
                            modules.config.default_selected_image_input_tab_id.removesuffix("_tab")
                        )
                    ],
                    interactive=True,
                    visible=modules.config.default_image_prompt_checkbox
                )

                # ── Link Input Mode radio to the image_tabs Tabs ─────────────────────
                tab_map = {
                    "Upscale / Variation": "uov",
                    "Image Prompt":         "ip_tab",
                    "Inpaint / Outpaint":   "inpaint_tab",
                    "Describe":             "describe_tab",
                    "Enhance":              "enhance_tab",
                    "Metadata":             "metadata_tab",
                }
                input_mode.change(
                    fn=lambda choice, m=tab_map: gr.update(selected=m[choice]),
                    inputs=[input_mode],
                    outputs=[image_tabs],
                    queue=False,
                    show_progress=False
                )
                
                input_mode.change(
                    fn=lambda choice, m=tab_map: gr.update(selected=m[choice]),
                    inputs=[input_mode],
                    outputs=[image_tabs],
                    queue=False,
                    show_progress=False
                )

                # ── Define Enhanced-Mode sub-radio (hidden by default) ─────────────────
                enhanced_mode = gr.Radio(
                    label="Enhanced Mode",
                    choices=["Upscale or Variation"] + [f"#{i+1}" for i in range(modules.config.default_enhance_tabs)],
                    value="Upscale or Variation",
                    interactive=True,
                    visible=modules.config.default_enhance_checkbox,
                )

                # ── Show/hide enhanced_mode when the “Enhanced” checkbox toggles ───────
                enhance_checkbox.change(
                    fn=lambda checked: gr.update(visible=checked),
                    inputs=[enhance_checkbox],
                    outputs=[enhanced_mode],
                    queue=False,
                    show_progress=False,
                )

                # ── Map enhanced_mode picks to your enhance_tabs IDs ─────────────────
                enhance_subtab_map = {
                    "Upscale or Variation": "enhance_uov",
                    **{f"#{i+1}": f"enhance_{i+1}" for i in range(modules.config.default_enhance_tabs)},
                }
                enhanced_mode.change(
                    fn=lambda sel, m=enhance_subtab_map: gr.update(selected=m[sel]),
                    inputs=[enhanced_mode],
                    outputs=[enhance_tabs],
                    queue=False,
                    show_progress=False,
                )

                # ── Show/hide whenever the “Inputs” checkbox toggles ─────────────────
                input_image_checkbox.change(
                    lambda show: gr.update(visible=show),
                    inputs=[input_image_checkbox],
                    outputs=[input_mode],
                    queue=False,
                    show_progress=False,
                )                

                # ── Rest of 9.1 (unchanged) ───────────────────────────
                image_number = gr.Slider(
                    label='Image Number',
                    minimum=1,
                    maximum=modules.config.default_max_image_number,
                    step=1,
                    value=modules.config.default_image_number
                )
                output_format = gr.Radio(
                    label='Output Format',
                    choices=flags.OutputFormat.list(),
                    value=modules.config.default_output_format
                )
                negative_prompt = gr.Textbox(
                    label='Negative Prompt',
                    show_label=True,
                    placeholder="Type prompt here.",
                    info='Describing what you do not want to see.',
                    lines=2,
                    elem_id='negative_prompt',
                    value=modules.config.default_prompt_negative
                )
                translate_prompts = gr.Checkbox(
                    label='Translate Prompts',
                    info='Uses the internet to translate prompts to English.',
                    value=False
                )
                seed_random = gr.Checkbox(label='Random', value=True)
                image_seed = gr.Textbox(
                    label='Seed',
                    value=0,
                    max_lines=1,
                    visible=False  # workaround for https://github.com/gradio-app/gradio/issues/5354
                )
                seed_random.change(
                    random_checked,
                    inputs=[seed_random],
                    outputs=[image_seed],
                    queue=False,
                    show_progress=False
                )

                # Precompute the history‐log URL once
                abs_html    = get_current_html_path(output_format)
                rel_html    = os.path.relpath(abs_html, start=modules.config.path_outputs).replace("\\", "/")
                history_url = f"/gradio_api/file=outputs/{rel_html}"

                def run_crop():
                    # this file is Fooocus/entry_with_update.py
                    here     = Path(__file__).resolve().parent          # …\Fooocus
                    project  = here.parent                              # …\Fooocus_win64_2-5-0\Fooocus_win64_2-5-0
                    bat_path = project / "crop.bat"
                    if not bat_path.exists():
                        raise FileNotFoundError(f"Could not find {bat_path}")
                    subprocess.Popen([str(bat_path)], cwd=str(project), shell=True)

                def run_prompt():
                    here     = Path(__file__).resolve().parent
                    project  = here.parent
                    bat_path = project / "prompt.bat"
                    if not bat_path.exists():
                        raise FileNotFoundError(f"Could not find {bat_path}")
                    subprocess.Popen([str(bat_path)], cwd=str(project), shell=True)
                    
                def run_reorganize():
                    here     = Path(__file__).resolve().parent
                    project  = here.parent
                    bat_path = project / "reorganize.bat"
                    if not bat_path.exists():
                        raise FileNotFoundError(f"Could not find {bat_path}")
                    subprocess.Popen([str(bat_path)], cwd=str(project), shell=True)

                def run_browse():
                    here     = Path(__file__).resolve().parent
                    project  = here.parent
                    bat_path = project / "browse.bat"
                    if not bat_path.exists():
                        raise FileNotFoundError(f"Could not find {bat_path}")
                    subprocess.Popen([str(bat_path)], cwd=str(project), shell=True)                    

                with gr.Blocks() as demo:
                    with gr.Row(): 
                        # start each button hidden or shown according to the saved state:
                        ip_btn = gr.Button(
                            "📷 Image Processing", 
                            scale=2, 
                            visible=ip_toggle_default    # ← use the loaded default
                        )
                        pg_btn = gr.Button(
                            "💬 Prompt Generator", 
                            scale=2, 
                            visible=pg_toggle_default    # ← use the loaded default
                        )
                        ro_btn = gr.Button(
                            "🔃 Image Reorganizer", 
                            scale=2, 
                            visible=ro_toggle_default    # ← use the loaded default
                        )                        
                        br_btn = gr.Button(
                            "📂 Image Browser", 
                            scale=2, 
                            visible=br_toggle_default    # ← use the loaded default
                        )                       

                        gr.Button("📚 Image History Log",        scale=2).click(
                            fn=None, inputs=[], outputs=[],
                            js=f"() => window.open('{history_url}', '_blank')"
                        )
                # tie your buttons to your Python helpers
                ip_btn.click(
                    fn=run_crop,      # Python function to run
                    inputs=[],        # no inputs
                    outputs=[],       # no outputs
                    queue=False       # run synchronously
                )
                pg_btn.click(
                    fn=run_prompt,    # Python function to run
                    inputs=[],
                    outputs=[],
                    queue=False
                )                            
                ro_btn.click(
                    fn=run_reorganize,    # Python function to run
                    inputs=[],
                    outputs=[],
                    queue=False
                )
                br_btn.click(
                    fn=run_browse,    # Python function to run
                    inputs=[],
                    outputs=[],
                    queue=False
                )
    ###########################################################
    #                9.2 Start of Styles tab n                #
    ###########################################################
            import copy
            from modules.sdxl_styles import legal_style_names
            import modules.style_sorter as style_sorter
            import modules.config

            with gr.Tab(label='Styles',
                        elem_classes=['style_selections_tab', 'style_scrollable_tab']):
                # Inject CSS that limits this tab‐panel (the element with class
                # 'style_scrollable_tab') to 900px and makes it scrollable.               
                
                gr.HTML("""
                <style>
                  /* Target the Styles panel itself */
                  .style_scrollable_tab {
                    max-height: 900px;
                    overflow-y: auto;
                    padding-right: 8px; /* avoid cutting off scroll bar */
                  }
                </style>
                """)

                # 1) Initialize master list & defaults
                style_sorter.try_load_sorted_styles(
                    style_names=legal_style_names,
                    default_selected=modules.config.default_styles
                )

                # 2) Search box
                style_search_bar = gr.Textbox(
                    placeholder="🔍 Type here to search styles …",
                    show_label=False,
                    value=""
                )

                # 3) CheckboxGroup pre‐populated with everything
                style_selections = gr.CheckboxGroup(
                    choices=copy.deepcopy(legal_style_names),
                    value=copy.deepcopy(modules.config.default_styles),
                    show_label=False
                )

                # 4) Hidden reset receiver (optional)
                reset_receiver = gr.Textbox(visible=False)

                # 5) Populate full list on load
                demo.load(
                    fn=lambda: gr.update(choices=copy.deepcopy(legal_style_names)),
                    outputs=[style_selections],
                    queue=False,
                    show_progress=False
                )

                # 6) Filter unchecked styles as the user types
                style_search_bar.change(
                    fn=style_sorter.search_styles,
                    inputs=[style_selections, style_search_bar],
                    outputs=[style_selections],
                    queue=False,
                    show_progress=False
                )

                # 7) Reorder checked items to the front
                style_selections.change(
                    fn=style_sorter.reorder_on_selection,
                    inputs=[style_selections],
                    outputs=[style_selections],
                    queue=False,
                    show_progress=False
                )

                # 8) External reset back to master list (optional)
                reset_receiver.change(
                    fn=style_sorter.sort_styles,
                    inputs=[style_selections],
                    outputs=[style_selections],
                    queue=False,
                    show_progress=False
                )
    ###########################################################
    #                9.3 Start of Models tab                  #
    ###########################################################

            with gr.Tab(label='Models'):
                with gr.Group():
                    with gr.Row():
                        base_model = gr.Dropdown(label='Base Model (SDXL only)', choices=modules.config.model_filenames, value=modules.config.default_base_model_name, show_label=True)
                        refiner_model = gr.Dropdown(label='Refiner (SDXL or SD 1.5)', choices=['None'] + modules.config.model_filenames, value=modules.config.default_refiner_model_name, show_label=True)

                    refiner_switch = gr.Slider(label='Refiner Switch At', minimum=0.1, maximum=1.0, step=0.0001,
                                               info='Use 0.4 for SD1.5 realistic models; '
                                                    'or 0.667 for SD1.5 anime models; '
                                                    'or 0.8 for XL-refiners; '
                                                    'or any value for switching two SDXL models.',
                                               value=modules.config.default_refiner_switch,
                                               visible=modules.config.default_refiner_model_name != 'None')

                    refiner_model.change(lambda x: gr.update(visible=x != 'None'),
                                         inputs=refiner_model, outputs=refiner_switch, show_progress=False, queue=False)

                with gr.Group():
                    lora_ctrls = []

                    for i, (enabled, filename, weight) in enumerate(modules.config.default_loras):
                        with gr.Row():
                            lora_enabled = gr.Checkbox(label='Enable', value=enabled,
                                                       elem_classes=['lora_enable', 'min_check'], scale=1)
                            lora_model = gr.Dropdown(label=f'LoRA {i + 1}',
                                                     choices=['None'] + modules.config.lora_filenames, value=filename,
                                                     elem_classes='lora_model', scale=5)
                            lora_weight = gr.Slider(label='Weight', minimum=modules.config.default_loras_min_weight,
                                                    maximum=modules.config.default_loras_max_weight, step=0.01, value=weight,
                                                    elem_classes='lora_weight', scale=5)
                            lora_ctrls += [lora_enabled, lora_model, lora_weight]

                with gr.Row():
                    refresh_files = gr.Button(value='\U0001f504 Refresh All Files', variant='secondary', elem_classes='refresh_button')
 
    ###########################################################
    #                9.3 End of Models tab                    #
    ###########################################################

    ###########################################################
    #                9.4 Start of Advanced tab                #
    ###########################################################

            with gr.Tab(label='Advanced'):
                guidance_scale = gr.Slider(label='Guidance Scale', minimum=1.0, maximum=30.0, step=0.01,
                                           value=modules.config.default_cfg_scale,
                                           info='Higher value means style is cleaner, vivider, and more artistic.')
                sharpness = gr.Slider(label='Image Sharpness', minimum=0.0, maximum=30.0, step=0.001,
                                      value=modules.config.default_sample_sharpness,
                                      info='Higher value means image and texture are sharper.')
                gr.HTML('<a href="https://github.com/lllyasviel/Fooocus/discussions/117" target="_blank">\U0001F4D4 Documentation</a>')
                dev_mode = gr.Checkbox(label='Developer Debug Mode', value=modules.config.default_developer_debug_mode_checkbox, container=False)

                with gr.Column(visible=modules.config.default_developer_debug_mode_checkbox) as dev_tools:
                    with gr.Tab(label='Debug Tools'):
                        adm_scaler_positive = gr.Slider(label='Positive ADM Guidance Scaler', minimum=0.1, maximum=3.0,
                                                        step=0.001, value=1.5, info='The scaler multiplied to positive ADM (use 1.0 to disable). ')
                        adm_scaler_negative = gr.Slider(label='Negative ADM Guidance Scaler', minimum=0.1, maximum=3.0,
                                                        step=0.001, value=0.8, info='The scaler multiplied to negative ADM (use 1.0 to disable). ')
                        adm_scaler_end = gr.Slider(label='ADM Guidance End At Step', minimum=0.0, maximum=1.0,
                                                   step=0.001, value=0.3,
                                                   info='When to end the guidance from positive/negative ADM. ')

                        refiner_swap_method = gr.Dropdown(label='Refiner swap method', value=flags.refiner_swap_method,
                                                          choices=['joint', 'separate', 'vae'])

                        adaptive_cfg = gr.Slider(label='CFG Mimicking from TSNR', minimum=1.0, maximum=30.0, step=0.01,
                                                 value=modules.config.default_cfg_tsnr,
                                                 info='Enabling Fooocus\'s implementation of CFG mimicking for TSNR '
                                                      '(effective when real CFG > mimicked CFG).')
                        clip_skip = gr.Slider(label='CLIP Skip', minimum=1, maximum=flags.clip_skip_max, step=1,
                                                 value=modules.config.default_clip_skip,
                                                 info='Bypass CLIP layers to avoid overfitting (use 1 to not skip any layers, 2 is recommended).')
                        sampler_name = gr.Dropdown(label='Sampler', choices=flags.sampler_list,
                                                   value=modules.config.default_sampler)
                        scheduler_name = gr.Dropdown(label='Scheduler', choices=flags.scheduler_list,
                                                     value=modules.config.default_scheduler)
                        vae_name = gr.Dropdown(label='VAE', choices=[modules.flags.default_vae] + modules.config.vae_filenames,
                                                     value=modules.config.default_vae, show_label=True)

                        generate_image_grid = gr.Checkbox(label='Generate Image Grid for Each Batch',
                                                          info='(Experimental) This may cause performance problems on some computers and certain internet conditions.',
                                                          value=False)

                        overwrite_step = gr.Slider(label='Forced Overwrite of Sampling Step',
                                                   minimum=-1, maximum=200, step=1,
                                                   value=modules.config.default_overwrite_step,
                                                   info='Set as -1 to disable. For developer debugging.')
                        overwrite_switch = gr.Slider(label='Forced Overwrite of Refiner Switch Step',
                                                     minimum=-1, maximum=200, step=1,
                                                     value=modules.config.default_overwrite_switch,
                                                     info='Set as -1 to disable. For developer debugging.')
                        overwrite_width = gr.Slider(label='Forced Overwrite of Generating Width',
                                                    minimum=-1, maximum=2048, step=1, value=-1,
                                                    info='Set as -1 to disable. For developer debugging. '
                                                         'Results will be worse for non-standard numbers that SDXL is not trained on.')
                        overwrite_height = gr.Slider(label='Forced Overwrite of Generating Height',
                                                     minimum=-1, maximum=2048, step=1, value=-1,
                                                     info='Set as -1 to disable. For developer debugging. '
                                                          'Results will be worse for non-standard numbers that SDXL is not trained on.')
                        overwrite_vary_strength = gr.Slider(label='Forced Overwrite of Denoising Strength of "Vary"',
                                                            minimum=-1, maximum=1.0, step=0.001, value=-1,
                                                            info='Set as negative number to disable. For developer debugging.')
                        overwrite_upscale_strength = gr.Slider(label='Forced Overwrite of Denoising Strength of "Upscale"',
                                                               minimum=-1, maximum=1.0, step=0.001,
                                                               value=modules.config.default_overwrite_upscale,
                                                               info='Set as negative number to disable. For developer debugging.')

                        disable_preview = gr.Checkbox(label='Disable Preview', value=modules.config.default_black_out_nsfw,
                                                      interactive=not modules.config.default_black_out_nsfw,
                                                      info='Disable preview during generation.')
                        disable_intermediate_results = gr.Checkbox(label='Disable Intermediate Results',
                                                      value=flags.Performance.has_restricted_features(modules.config.default_performance),
                                                      info='Disable intermediate results during generation, only show final gallery.')

                        disable_seed_increment = gr.Checkbox(label='Disable seed increment',
                                                             info='Disable automatic seed increment when image number is > 1.',
                                                             value=False)
                        read_wildcards_in_order = gr.Checkbox(label="Read wildcards in order", value=False)

                        black_out_nsfw = gr.Checkbox(label='Black Out NSFW', value=modules.config.default_black_out_nsfw,
                                                     interactive=not modules.config.default_black_out_nsfw,
                                                     info='Use black image if NSFW is detected.')

                        black_out_nsfw.change(lambda x: gr.update(value=x, interactive=not x),
                                              inputs=black_out_nsfw, outputs=disable_preview, queue=False,
                                              show_progress=False)

                        if not args_manager.args.disable_image_log:
                            save_final_enhanced_image_only = gr.Checkbox(label='Save only final enhanced image',
                                                                         value=modules.config.default_save_only_final_enhanced_image)

                        if not args_manager.args.disable_metadata:
                            save_metadata_to_images = gr.Checkbox(label='Save Metadata to Images', value=modules.config.default_save_metadata_to_images,
                                                                  info='Adds parameters to generated images allowing manual regeneration.')
                            metadata_scheme = gr.Radio(label='Metadata Scheme', choices=flags.metadata_scheme, value=modules.config.default_metadata_scheme,
                                                       info='Image Prompt parameters are not included. Use png and a1111 for compatibility with Civitai.',
                                                       visible=modules.config.default_save_metadata_to_images)

                            save_metadata_to_images.change(lambda x: gr.update(visible=x), inputs=[save_metadata_to_images], outputs=[metadata_scheme],
                                                           queue=False, show_progress=False)

    ###########################################################
    #                9.4 End of Advanced tab                  #
    ###########################################################

    ###########################################################
    #              9.5 Start of Control tab                   #
    ###########################################################


                    with gr.Tab(label='Control'):
                        debugging_cn_preprocessor = gr.Checkbox(label='Debug Preprocessors', value=False,
                                                                info='See the results from preprocessors.')
                        skipping_cn_preprocessor = gr.Checkbox(label='Skip Preprocessors', value=False,
                                                               info='Do not preprocess images. (Inputs are already canny/depth/cropped-face/etc.)')

                        mixing_image_prompt_and_vary_upscale = gr.Checkbox(label='Mixing Image Prompt and Vary/Upscale',
                                                                           value=False)
                        mixing_image_prompt_and_inpaint = gr.Checkbox(label='Mixing Image Prompt and Inpaint',
                                                                      value=False)

                        controlnet_softness = gr.Slider(label='Softness of ControlNet', minimum=0.0, maximum=1.0,
                                                        step=0.001, value=0.25,
                                                        info='Similar to the Control Mode in A1111 (use 0.0 to disable). ')

                        with gr.Tab(label='Canny'):
                            canny_low_threshold = gr.Slider(label='Canny Low Threshold', minimum=1, maximum=255,
                                                            step=1, value=64)
                            canny_high_threshold = gr.Slider(label='Canny High Threshold', minimum=1, maximum=255,
                                                             step=1, value=128)
                                                             
    ###########################################################
    #                9.5 End of Control tab                   #
    ###########################################################

    ###########################################################
    #              9.6 Start of Inpaint tab                   #
    ###########################################################


                    with gr.Tab(label='Inpaint'):
                        debugging_inpaint_preprocessor = gr.Checkbox(label='Debug Inpaint Preprocessing', value=False)
                        debugging_enhance_masks_checkbox = gr.Checkbox(label='Debug Enhance Masks', value=False,
                                                                       info='Show enhance masks in preview and final results')
                        debugging_dino = gr.Checkbox(label='Debug GroundingDINO', value=False,
                                                     info='Use GroundingDINO boxes instead of more detailed SAM masks')
                        inpaint_disable_initial_latent = gr.Checkbox(label='Disable initial latent in inpaint', value=False)
                        inpaint_engine = gr.Dropdown(label='Inpaint Engine',
                                                     value=modules.config.default_inpaint_engine_version,
                                                     choices=flags.inpaint_engine_versions,
                                                     info='Version of Fooocus inpaint model. If set, use performance Quality or Speed (no performance LoRAs) for best results.')
                        inpaint_strength = gr.Slider(label='Inpaint Denoising Strength',
                                                     minimum=0.0, maximum=1.0, step=0.001, value=1.0,
                                                     info='Same as the denoising strength in A1111 inpaint. '
                                                          'Only used in inpaint, not used in outpaint. '
                                                          '(Outpaint always use 1.0)')
                        inpaint_respective_field = gr.Slider(label='Inpaint Respective Field',
                                                             minimum=0.0, maximum=1.0, step=0.001, value=0.618,
                                                             info='The area to inpaint. '
                                                                  'Value 0 is same as "Only Masked" in A1111. '
                                                                  'Value 1 is same as "Whole Image" in A1111. '
                                                                  'Only used in inpaint, not used in outpaint. '
                                                                  '(Outpaint always use 1.0)')
                        inpaint_erode_or_dilate = gr.Slider(label='Mask Erode or Dilate',
                                                            minimum=-64, maximum=64, step=1, value=0,
                                                            info='Positive value will make white area in the mask larger, '
                                                                 'negative value will make white area smaller. '
                                                                 '(default is 0, always processed before any mask invert)')
                        dino_erode_or_dilate = gr.Slider(label='GroundingDINO Box Erode or Dilate',
                                                         minimum=-64, maximum=64, step=1, value=0,
                                                         info='Positive value will make white area in the mask larger, '
                                                              'negative value will make white area smaller. '
                                                              '(default is 0, processed before SAM)')

                        inpaint_mask_color = gr.ColorPicker(label='Inpaint brush color', value='#FFFFFF', elem_id='inpaint_brush_color')

                        inpaint_ctrls = [debugging_inpaint_preprocessor, inpaint_disable_initial_latent, inpaint_engine,
                                         inpaint_strength, inpaint_respective_field,
                                         inpaint_advanced_masking_checkbox, invert_mask_checkbox, inpaint_erode_or_dilate]

                        inpaint_advanced_masking_checkbox.change(lambda x: [gr.update(visible=x)] * 2,
                                                                 inputs=inpaint_advanced_masking_checkbox,
                                                                 outputs=[inpaint_mask_image, inpaint_mask_generation_col],
                                                                 queue=False, show_progress=False)

                        inpaint_mask_color.change(lambda x: gr.update(brush_color=x), inputs=inpaint_mask_color,
                                                  outputs=inpaint_input_image,
                                                  queue=False, show_progress=False)

    ###########################################################
    #              9.6 End of Inpaint tab                     #
    ###########################################################

    ###########################################################
    #              9.7 Start of FreeU tab                     #
    ###########################################################

                    with gr.Tab(label='FreeU'):
                        freeu_enabled = gr.Checkbox(label='Enabled', value=False)
                        freeu_b1 = gr.Slider(label='B1', minimum=0, maximum=2, step=0.01, value=1.01)
                        freeu_b2 = gr.Slider(label='B2', minimum=0, maximum=2, step=0.01, value=1.02)
                        freeu_s1 = gr.Slider(label='S1', minimum=0, maximum=4, step=0.01, value=0.99)
                        freeu_s2 = gr.Slider(label='S2', minimum=0, maximum=4, step=0.01, value=0.95)
                        freeu_ctrls = [freeu_enabled, freeu_b1, freeu_b2, freeu_s1, freeu_s2]

                dev_mode.change(dev_mode_checked, inputs=[dev_mode], outputs=[dev_tools],
                                queue=False, show_progress=False)

                refresh_files_output = [base_model, refiner_model, vae_name]
                if not args_manager.args.disable_preset_selection:
                    refresh_files_output += [preset_selection]
                refresh_files.click(refresh_files_clicked, [], refresh_files_output + lora_ctrls,
                                    queue=False, show_progress=False)
                                    
    ###########################################################
    #                9.7 End of FreeU tab                     #
    ###########################################################

    ###########################################################
    #                9.8 Start of Extras tab                   #
    ###########################################################

            with gr.Tab(label='Extras'):
                play_notification = gr.Checkbox(label='Play notification after rendering', value=False)
                notification_file = 'notification.mp3'
                if os.path.exists(notification_file):
                    notification = gr.State(value=notification_file)
                    notification_input = gr.Audio(label='Notification', interactive=True, elem_id='audio_notification', visible=False, show_edit_button=False)

                    play_notification.change(fn=play_notification_checked, inputs=[play_notification, notification], outputs=[notification_input], queue=False)
                    notification_input.change(fn=notification_input_changed, inputs=[notification_input, notification], outputs=[notification], queue=False)
                    
                with gr.Row(): theme_dd = gr.Dropdown(choices=THEME_NAMES, value=theme_name, label="Select Theme") 
                info = gr.Markdown("")
                theme_dd.change(fn=change_theme, inputs=theme_dd, outputs=info, js=None)
                
                gr.Markdown("🧩 Additional Features in settings tab")
                with gr.Row():
                    

                    # … inside with gr.Row():  in your Extras tab …
                    ip_toggle = gr.Checkbox(
                        label='Image Processing Features',
                        value=ip_toggle_default  # ← use loaded default
                    )
                    pg_toggle = gr.Checkbox(
                        label='Prompt Generation Features',
                        value=pg_toggle_default  # ← use loaded default
                    )
                    ro_toggle = gr.Checkbox(
                        label='Image Reorganizer',
                        value=ro_toggle_default  # ← use loaded default
                    )                    
                    br_toggle = gr.Checkbox(
                        label='Image Browser',
                        value=br_toggle_default  # ← use loaded default
                    )                    
                    
                    
                    
                    
                    

                    def _save_add_features(ip_val, pg_val, ro_val, br_val):
                        with open(ADD_FEATURES_FILE, "w") as f:
                            json.dump({"ip_toggle": ip_val, "pg_toggle": pg_val, "ro_toggle": ro_val, "br_toggle": br_val}, f)

                    ip_toggle.change(
                        fn=on_feature_toggle,
                        inputs=[ip_toggle, pg_toggle, ro_toggle, br_toggle],
                        outputs=[ip_btn, pg_btn, ro_btn, br_btn],
                        queue=False,
                    )
                    pg_toggle.change(
                        fn=on_feature_toggle,
                        inputs=[ip_toggle, pg_toggle, ro_toggle, br_toggle],
                        outputs=[ip_btn, pg_btn, ro_btn, br_btn],
                        queue=False,
                    )                                    
                    ro_toggle.change(
                        fn=on_feature_toggle,
                        inputs=[ip_toggle, pg_toggle, ro_toggle, br_toggle],
                        outputs=[ip_btn, pg_btn, ro_btn, br_btn],
                        queue=False,
                    )                     
                    br_toggle.change(
                        fn=on_feature_toggle,
                        inputs=[ip_toggle, pg_toggle, ro_toggle, br_toggle],
                        outputs=[ip_btn, pg_btn, ro_btn, br_btn],
                        queue=False,
                    )                   

    ###########################################################
    #                9.8 End of Audio tab                     #
    ###########################################################

###########################################################
#       9. End of Advanced-column (right side)            #
###########################################################

###########################################################
#       10. Start of Callback & interaction wiring        #
###########################################################

    ###########################################################
    #    10.1 Start of Building load_data_outputs list        #
    ###########################################################

        state_is_generating = gr.State(False)

        load_data_outputs = [advanced_checkbox, image_number, prompt, negative_prompt, style_selections,
                             performance_selection, overwrite_step, overwrite_switch, aspect_ratios_selection,
                             overwrite_width, overwrite_height, guidance_scale, sharpness, adm_scaler_positive,
                             adm_scaler_negative, adm_scaler_end, refiner_swap_method, adaptive_cfg, clip_skip,
                             base_model, refiner_model, refiner_switch, sampler_name, scheduler_name, vae_name,
                             seed_random, image_seed, inpaint_engine, inpaint_engine_state,
                             inpaint_mode] + enhance_inpaint_mode_ctrls + [generate_button,
                             load_parameter_button] + freeu_ctrls + lora_ctrls

    ###########################################################
    #    10.1 End of Building load_data_outputs list          #
    ###########################################################

    ###########################################################
    #    10.2 Start of preset_selection.change handler        #
    ###########################################################

        if not args_manager.args.disable_preset_selection:

            preset_selection.change(preset_selection_change, inputs=[preset_selection, state_is_generating, inpaint_mode], outputs=load_data_outputs, queue=False, show_progress=True) \
                .then(fn=style_sorter.sort_styles, inputs=style_selections, outputs=style_selections, queue=False, show_progress=False) \
                .then(lambda: None, js='()=>{refresh_style_localization();}') \
                .then(inpaint_engine_state_change, inputs=[inpaint_engine_state] + enhance_inpaint_mode_ctrls, outputs=enhance_inpaint_engine_ctrls, queue=False, show_progress=False)

    ###########################################################
    #    10.2 End of preset_selection.change handler          #
    ###########################################################

    ###########################################################
    #    10.3 Start of performance_selection.change handler   #
    ###########################################################

        performance_selection.change(lambda x: [gr.update(interactive=not flags.Performance.has_restricted_features(x))] * 11 +
                                               [gr.update(visible=not flags.Performance.has_restricted_features(x))] * 1 +
                                               [gr.update(value=flags.Performance.has_restricted_features(x))] * 1,
                                     inputs=performance_selection,
                                     outputs=[
                                         guidance_scale, sharpness, adm_scaler_end, adm_scaler_positive,
                                         adm_scaler_negative, refiner_switch, refiner_model, sampler_name,
                                         scheduler_name, adaptive_cfg, refiner_swap_method, negative_prompt, disable_intermediate_results
                                     ], queue=False, show_progress=False)

        output_format.input(lambda x: gr.update(output_format=x), inputs=output_format)

        advanced_checkbox.change(lambda x: gr.update(visible=x), advanced_checkbox, advanced_column,
                                 queue=False, show_progress=False) \
            .then(fn=lambda: None, js='refresh_grid_delayed', queue=False, show_progress=False)

        # inpaint_mode.change(inpaint_mode_change, inputs=[inpaint_mode, inpaint_engine_state], outputs=[
            # inpaint_additional_prompt, outpaint_selections, example_inpaint_prompts,
            # inpaint_disable_initial_latent, inpaint_engine,
            # inpaint_strength, inpaint_respective_field
        # ], show_progress=False, queue=False)
        
        inpaint_mode.change(
            inpaint_mode_change,
            inputs=[inpaint_mode, inpaint_engine_state],
            outputs=[
                inpaint_additional_prompt,
                outpaint_selections,
                example_inpaint_prompts.dataset,
                inpaint_disable_initial_latent,
                inpaint_engine,
                inpaint_strength,
                inpaint_respective_field
            ],
            show_progress=False,
            queue=False
)
        

    ###########################################################
    #     10.3 End of performance_selection.change handler    #
    ###########################################################

    ###########################################################
    #     10.4 Start of Other control-updates & .load calls   #
    ###########################################################

        # load configured default_inpaint_method
        default_inpaint_ctrls = [inpaint_mode, inpaint_disable_initial_latent, inpaint_engine, inpaint_strength, inpaint_respective_field]
        for mode, disable_initial_latent, engine, strength, respective_field in [default_inpaint_ctrls] + enhance_inpaint_update_ctrls:
            # shared.gradio_root.load(inpaint_mode_change, inputs=[mode, inpaint_engine_state], outputs=[
                # inpaint_additional_prompt, outpaint_selections, example_inpaint_prompts, disable_initial_latent,
                # engine, strength, respective_field
            # ], show_progress=False, queue=False)
            
            shared.gradio_root.load(
                inpaint_mode_change,
                inputs=[mode, inpaint_engine_state],
                outputs=[
                    inpaint_additional_prompt,
                    outpaint_selections,
                    example_inpaint_prompts.dataset,
                    disable_initial_latent,
                    engine,
                    strength,
                    respective_field
                ],
                show_progress=False,
                queue=False
            )            

        generate_mask_button.click(fn=generate_mask,
                                   inputs=[inpaint_input_image, inpaint_mask_model, inpaint_mask_cloth_category,
                                           inpaint_mask_dino_prompt_text, inpaint_mask_sam_model,
                                           inpaint_mask_box_threshold, inpaint_mask_text_threshold,
                                           inpaint_mask_sam_max_detections, dino_erode_or_dilate, debugging_dino],
                                   outputs=inpaint_mask_image, show_progress=True, queue=True)

        # 10.4 Build the list of inputs to get_task
        ctrls = [
            currentTask,                               # [--] this one is popped out (deleted in get_task)
            generate_image_grid,                       # [00]

            # Text inputs & sliders
            prompt,                                    # [01]
            negative_prompt,                           # [02]
            translate_prompts,                         # [03]
            style_selections,                          # [04]
            performance_selection,                     # [05]
            aspect_ratios_selection,                   # [06]
            image_number,                              # [07]
            output_format,                             # [08]
            image_seed,                                # [09]
            read_wildcards_in_order,                   # [10]
            sharpness,                                 # [11]
            guidance_scale,                            # [12]

            # Model selection & LoRAs
            base_model,                                # [13]
            refiner_model,                             # [14]
            refiner_switch,                            # [15]
        ] + lora_ctrls                                 # [16...N]   (fills out after [16])

        # “Inputs” toggle checkbox
        ctrls += [input_image_checkbox]                # [31]
        
        # ── Hidden `mode` State goes here, making it slot 32
        ctrls += [input_mode]                          # [32]

        # Upscale / Variation controls
        ctrls += [
            uov_method,                                # [33]
            uov_input_image,                           # [34]
        ]

        # Inpaint / Outpaint controls
        ctrls += [
            outpaint_selections,                       # [35]
            inpaint_input_image,                       # [36]
            inpaint_additional_prompt,                 # [37]
            inpaint_mask_image,                        # [38]
        ]

        # Preview toggles
        ctrls += [
            disable_preview,                           # [39]
            disable_intermediate_results,              # [40]
            disable_seed_increment,                    # [41]
            black_out_nsfw,                            # [42]
        ]

        # Fooocus‑specific parameters
        ctrls += [
            adm_scaler_positive,                       # [43]
            adm_scaler_negative,                       # [44]
            adm_scaler_end,                            # [45]
            adaptive_cfg,                              # [46]
            clip_skip,                                 # [47]
        ]

        # Sampling settings
        ctrls += [
            sampler_name,                              # [48]
            scheduler_name,                            # [49]
            vae_name,                                  # [50]
        ]

        # Overwrite / mixing settings
        ctrls += [
            overwrite_step,                            # [51]
            overwrite_switch,                          # [52]
            overwrite_width,                           # [53]
            overwrite_height,                          # [54]
            overwrite_vary_strength,                   # [55]
            overwrite_upscale_strength,                # [56]
            mixing_image_prompt_and_vary_upscale,      # [57]
            mixing_image_prompt_and_inpaint,           # [58]
        ]

        # ControlNet toggles & thresholds
        ctrls += [
            debugging_cn_preprocessor,                 # [59]
            skipping_cn_preprocessor,                  # [60]
            canny_low_threshold,                       # [61]
            canny_high_threshold,                      # [62]
            refiner_swap_method,                       # [63]
            controlnet_softness,                       # [64]
        ]

        # Any free‑form ControlNet custom controls
        ctrls += freeu_ctrls                           # [65...M]

        # Inpaint controls group (if you maintain a separate list)
        ctrls += inpaint_ctrls                          # [M+1...K]

        # Metadata / logging toggles
        if not args_manager.args.disable_image_log:
            ctrls += [save_final_enhanced_image_only]   # [K+1]
        if not args_manager.args.disable_metadata:
            ctrls += [save_metadata_to_images, metadata_scheme]  # [K+2], [K+3]

        # Finally, all Image‑Prompt inputs (collected earlier in ip_ctrls)
        ctrls += ip_ctrls                               # [K+4...P]

        # Enhance‑mode controls
        ctrls += [
            debugging_dino,                            # [P+1]
            dino_erode_or_dilate,                      # [P+2]
            debugging_enhance_masks_checkbox,          # [P+3]
            enhance_input_image,                       # [P+4]
            enhance_checkbox,                          # [P+5]
            enhance_uov_method,                        # [P+6]
            enhance_uov_processing_order,              # [P+7]
            enhance_uov_prompt_type,                   # [P+8]
        ]
        ctrls += enhance_ctrls                          # [P+9...Q]




        prompt.input(parse_meta, inputs=[prompt, state_is_generating], outputs=[prompt, generate_button, load_parameter_button], queue=False, show_progress=False)

        load_parameter_button.click(modules.meta_parser.load_parameter_button_click, inputs=[prompt, state_is_generating, inpaint_mode], outputs=load_data_outputs, queue=False, show_progress=False)


        metadata_import_button.click(trigger_metadata_import, inputs=[metadata_input_image, state_is_generating], outputs=load_data_outputs, queue=False, show_progress=True) \
            .then(style_sorter.sort_styles, inputs=style_selections, outputs=style_selections, queue=False, show_progress=False)

        generate_button.click(
            lambda: (
                gr.update(visible=True, interactive=True),
                gr.update(visible=True, interactive=True),
                gr.update(visible=False, interactive=False),
                [],
                True
            ),
            outputs=[stop_button, skip_button, generate_button, gallery, state_is_generating]
        ) \
        .then(fn=refresh_seed, inputs=[seed_random, image_seed], outputs=[image_seed]) \
        .then(fn=get_task, inputs=ctrls, outputs=[currentTask]) \
        .then(
            fn=generate_clicked,
            inputs=[currentTask],
            outputs=[progress_html, progress_window, progress_gallery, gallery]
        ) \
        .then(
            lambda: (
                gr.update(visible=True, interactive=True),
                gr.update(visible=False, interactive=False),
                gr.update(visible=False, interactive=False),
                False
            ),
            outputs=[generate_button, stop_button, skip_button, state_is_generating]
        ) \
        #.then(fn=update_history_link, outputs=[history_link]) \
        #.then(fn=lambda: None, js='playNotification') \
        #.then(fn=lambda: None, js='refresh_grid_delayed')

        reset_button.click(lambda: [worker.AsyncTask(args=[]), False, gr.update(visible=True, interactive=True)] +
                                   [gr.update(visible=False)] * 6 +
                                   [gr.update(visible=True, value=[])],
                           outputs=[currentTask, state_is_generating, generate_button,
                                    reset_button, stop_button, skip_button,
                                    progress_html, progress_window, progress_gallery, gallery],
                           queue=False)


    ###########################################################
    #       10.4 End of Other control-updates & .load calls   #
    ###########################################################

    ###########################################################
    #       10.5 Start of generate_button → task chain        #
    ###########################################################

        describe_btn.click(trigger_describe, inputs=[describe_methods, describe_input_image, describe_apply_styles],
                           outputs=[prompt, style_selections], show_progress=True, queue=True) \
            .then(fn=style_sorter.sort_styles, inputs=style_selections, outputs=style_selections, queue=False, show_progress=False) \
            .then(lambda: None, js='()=>{refresh_style_localization();}')

        if args_manager.args.enable_auto_describe_image:

            uov_input_image.upload(trigger_auto_describe, inputs=[describe_methods, uov_input_image, prompt, describe_apply_styles],
                                   outputs=[prompt, style_selections], show_progress=True, queue=True) \
                .then(fn=style_sorter.sort_styles, inputs=style_selections, outputs=style_selections, queue=False, show_progress=False) \
                .then(lambda: None, js='()=>{refresh_style_localization();}')

            enhance_input_image.upload(lambda: gr.update(value=True), outputs=enhance_checkbox, queue=False, show_progress=False) \
                .then(trigger_auto_describe, inputs=[describe_methods, enhance_input_image, prompt, describe_apply_styles],
                      outputs=[prompt, style_selections], show_progress=True, queue=True) \
                .then(fn=style_sorter.sort_styles, inputs=style_selections, outputs=style_selections, queue=False, show_progress=False) \
                .then(lambda: None, js='()=>{refresh_style_localization();}')

    ###########################################################
    #       10.5 End of generate_button → task chain          #
    ###########################################################

###########################################################
#       10. End of Callback & interaction wiring          #
###########################################################

###########################################################
#    11 Start of dump_default_english_config (unused)     #
###########################################################

# dump_default_english_config()

###########################################################
#    11 End of dump_default_english_config (unused)       #
###########################################################

###########################################################
#             12 Start of App Launch                      #
###########################################################

shared.gradio_root.launch(
    inbrowser=args_manager.args.in_browser,
    server_name=args_manager.args.listen,
    server_port=args_manager.args.port,
    share=args_manager.args.share,
    auth=check_auth if (args_manager.args.share or args_manager.args.listen) and auth_enabled else None,
    allowed_paths=[modules.config.path_outputs],
    blocked_paths=[constants.AUTH_FILENAME]
)

###########################################################
#             12 End of App Launch                        #
###########################################################