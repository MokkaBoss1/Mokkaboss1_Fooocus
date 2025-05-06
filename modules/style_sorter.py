import os
import gradio as gr
import modules.localization as localization
import json
from modules.sdxl_styles import legal_style_names

all_styles = []


def try_load_sorted_styles(style_names, default_selected):
    global all_styles

    all_styles = style_names

    try:
        if os.path.exists('sorted_styles.json'):
            with open('sorted_styles.json', 'rt', encoding='utf-8') as fp:
                sorted_styles = []
                for x in json.load(fp):
                    if x in all_styles:
                        sorted_styles.append(x)
                for x in all_styles:
                    if x not in sorted_styles:
                        sorted_styles.append(x)
                all_styles = sorted_styles
    except Exception as e:
        print('Load style sorting failed.')
        print(e)

    unselected = [y for y in all_styles if y not in default_selected]
    all_styles = default_selected + unselected

    return


def sort_styles(selected):
    global all_styles
    unselected = [y for y in all_styles if y not in selected]
    sorted_styles = selected + unselected
    """
    try:
        with open('sorted_styles.json', 'wt', encoding='utf-8') as fp:
            json.dump(sorted_styles, fp, indent=4)
    except Exception as e:
        print('Write style sorting failed.')
        print(e)
    all_styles = sorted_styles
    """
    return gr.update(choices=sorted_styles)


def localization_key(x):
    return x + localization.current_translation.get(x, '')


# modules/style_sorter.py



def search_styles(current_choices, query):
    """
    Keep all selected styles at the top, then only filter
    the *unchecked* styles by the query substring.
    """
    # 1) Always preserve the checked ones:
    selected = current_choices

    # 2) Build list of unchecked styles:
    unchecked = [s for s in legal_style_names if s not in selected]

    # 3) If there’s a query, filter only the unchecked list:
    if query:
        filtered_unchecked = [s for s in unchecked if query.lower() in s.lower()]
    else:
        filtered_unchecked = unchecked

    # 4) Concatenate: checked up front, then filtered unchecked
    new_choices = selected + filtered_unchecked

    # 5) Return update: choices + keep the same checked value
    return gr.update(choices=new_choices, value=selected)

def reorder_on_selection(current_choices):
    """
    Whenever the user checks or unchecks a box, move
    all checked items to the front (in the order they
    appear in current_choices), and append the rest
    in the original master order.
    """
    rest = [s for s in legal_style_names if s not in current_choices]
    return gr.update(choices=current_choices + rest, value=current_choices)