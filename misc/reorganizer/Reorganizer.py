import gradio as gr
import os
import shutil
import subprocess
import time
from PIL import Image, UnidentifiedImageError, ImageFilter, ImageOps, ImageDraw
import sys
import re
import socket
import json  # Added for JSON support


if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

# Allow duplicate OpenMP runtimes. Use with caution.
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"

# -----------------------------------------------------------------------------
# Load Server Setting from JSON (reuse from previous programs)
# -----------------------------------------------------------------------------
REMOTE_JSON_PATH = "remote_open.json"

#####################################################################
CONFIG_FILENAME = "theme_config.json"
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', CONFIG_FILENAME))

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

def set_creation_time(path, ctime):
        timestamp = int(ctime * 10000000) + 116444736000000000
        ctime_ft = wintypes.FILETIME(timestamp & 0xFFFFFFFF, timestamp >> 32)
        handle = ctypes.windll.kernel32.CreateFileW(
            path, 0x100, 0, None, 3, 0x80, None)
        if handle != -1:
            ctypes.windll.kernel32.SetFileTime(
                handle, ctypes.byref(ctime_ft), None, None)
            ctypes.windll.kernel32.CloseHandle(handle)

def reorganize_files_stream(
    directory,
    subfolder_option,
    filetypes,
    rename_option,
    add_hex,
    add_parent_folder,
    add_dimensions,
    duplicate_handling,
    convert_to,
    resize_radio,
    resize_to,
    max_filesize
):
    """
    Streams log updates in real time while files are being processed.
    Each yield returns the entire log so far.
    """
    changes_log = ""

    # 1) Check if directory exists
    if not os.path.exists(directory):
        yield "Error: Specified directory does not exist."
        return

    filetypes = [ft.lower() for ft in filetypes]
    modified_files = 0
    skipped_files = 0

    changes_log += f"Starting reorganization in: {directory}\n"
    yield changes_log

    def get_unique_path(path, is_hex=False, leave_as_is=False):
        if leave_as_is:
            return path if not os.path.exists(path) else path

        base, ext = os.path.splitext(path)
        counter = 1
        original = path
        while os.path.exists(path):
            if is_hex:
                return path
            path = f"{base}_{counter}{ext}"
            counter += 1
        return path

    def remove_empty_folders(dir_path):
        for root, dirs, _ in os.walk(dir_path, topdown=False):
            for d in dirs:
                d_path = os.path.join(root, d)
                if not os.listdir(d_path):
                    os.rmdir(d_path)

    def build_new_filename(
        current_path,
        rename_option,
        add_hex,
        add_parent_folder,
        add_dimensions,
        width=None,
        height=None
    ):
        dirpath = os.path.dirname(current_path)
        filename = os.path.basename(current_path)
        base, ext = os.path.splitext(filename)

        if rename_option == "Leave as is":
            return current_path

        hex_key = os.urandom(3).hex() if add_hex else ""

        if rename_option == "Create new names":
            base = ""
            if add_parent_folder:
                parent_name = os.path.basename(os.path.dirname(current_path))
                base = f"{parent_name}"
            if add_dimensions and width and height:
                dims = f"({width}x{height})"
                base = f"{base}_{dims}" if base else dims
            if add_hex:
                base = f"{base}_{hex_key}" if base else hex_key

        elif rename_option == "Add before current name":
            additions = []
            if add_parent_folder:
                additions.append(os.path.basename(os.path.dirname(current_path)))
            if add_hex:
                additions.append(hex_key)
            if add_dimensions and width and height:
                additions.append(f"({width}x{height})")
            base = "_".join(additions + [base])

        elif rename_option == "Add after current name":
            additions = [base]
            if add_parent_folder:
                additions.append(os.path.basename(os.path.dirname(current_path)))
            if add_hex:
                additions.append(hex_key)
            if add_dimensions and width and height:
                additions.append(f"({width}x{height})")
            base = "_".join(additions)

        return os.path.join(dirpath, f"{base}{ext}")

    def get_target_subfolder(
        directory,
        subfolder_option,
        folder_time
    ):
        if subfolder_option == "Leave current subfolder structure":
            return None

        if subfolder_option == "Flatten files":
            return directory

        tstruct = time.localtime(folder_time)
        if subfolder_option == "Create subfolders by creation month/year":
            return os.path.join(directory, f"{time.strftime('%Y', tstruct)} M{time.strftime('%m', tstruct)}")

        if subfolder_option == "Create subfolders by creation week/month/year":
            week_num = time.strftime('%W', tstruct)
            return os.path.join(
                directory,
                f"{time.strftime('%Y', tstruct)} M{time.strftime('%m', tstruct)} W{week_num}"
            )
        return None

    # 2) Walk directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            try:
                current_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower().lstrip(".")
                if ext == "jpeg":
                    ext = "jpg"
                if ext == "tiff":
                    ext = "tif"

                if ext not in filetypes:
                    continue

                size_mb = os.path.getsize(current_path) / (1024 * 1024)
                if size_mb > max_filesize:
                    skipped_files += 1
                    changes_log += f"SKIPPED (>{max_filesize} MB): {current_path}\n"
                    yield changes_log
                    continue

                st = os.stat(current_path)
                original_ctime = st.st_ctime
                original_mtime = st.st_mtime
                original_atime = st.st_atime

                exif_data = None
                exif_datetime = None
                subfolder_needed = (subfolder_option != "Leave current subfolder structure")
                resizing_needed = (resize_radio == "Yes")
                conversion_needed = (convert_to != "None")
                folder_time = original_ctime

                read_image_metadata = (
                    subfolder_needed or
                    resizing_needed or
                    conversion_needed or
                    add_dimensions
                )

                width = None
                height = None

                if read_image_metadata:
                    try:
                        from PIL import Image
                        with Image.open(current_path) as im:
                            exif_data = im.info.get('exif')
                            exif_dict = im.getexif()
                            dt_tag = 36867
                            exif_datetime = exif_dict.get(dt_tag, None)
                            if not exif_datetime:
                                dt_tag = 306
                                exif_datetime = exif_dict.get(dt_tag, None)
                            width, height = im.size
                    except Exception:
                        skipped_files += 1
                        changes_log += f"SKIPPED (Unreadable Image): {current_path}\n"
                        yield changes_log
                        continue

                if exif_datetime:
                    try:
                        t_struct = time.strptime(exif_datetime, "%Y:%m:%d %H:%M:%S")
                        folder_time = time.mktime(t_struct)
                    except (ValueError, TypeError):
                        folder_time = original_ctime

                if sys.platform == 'win32' and exif_datetime:
                    if abs(folder_time - original_ctime) > 1:
                        set_creation_time(current_path, folder_time)
                        changes_log += (
                            f"Creation date updated from {time.ctime(original_ctime)} "
                            f"to EXIF date {exif_datetime} for {current_path}.\n"
                        )
                        yield changes_log
                        original_ctime = folder_time

                prospective_path = build_new_filename(
                    current_path,
                    rename_option,
                    add_hex,
                    add_parent_folder,
                    add_dimensions,
                    width, height
                )
                rename_needed = (prospective_path != current_path)

                convert_ext_map = {
                    "JPG":  ["jpg", "jpeg"],
                    "PNG":  ["png"],
                    "WEBP": ["webp"],
                    "BMP":  ["bmp"],
                    "TIFF": ["tif", "tiff"]
                }
                convert_needed = False
                if convert_to != "None":
                    target_ext = convert_to.lower()
                    if target_ext == "tiff":
                        target_ext = "tif"
                    if ext not in convert_ext_map.get(convert_to, []):
                        convert_needed = True

                do_resize = False
                if (resize_radio == "Yes" and width is not None and height is not None):
                    target_pixels = resize_to * 1_000_000
                    if (width * height) > target_pixels:
                        do_resize = True

                final_subfolder = get_target_subfolder(directory, subfolder_option, folder_time)
                move_needed = False
                if final_subfolder is not None:
                    if os.path.abspath(root) != os.path.abspath(final_subfolder):
                        move_needed = True

                if not rename_needed and not convert_needed and not do_resize and not move_needed:
                    skipped_files += 1
                    changes_log += f"SKIPPED (No change needed): {current_path}\n"
                    yield changes_log
                    continue

                if do_resize:
                    try:
                        with Image.open(current_path) as image:
                            old_w, old_h = image.size
                            scale_factor = (target_pixels / (old_w * old_h)) ** 0.5
                            new_w = int(old_w * scale_factor)
                            new_h = int(old_h * scale_factor)
                            save_kwargs = {}
                            if exif_data:
                                save_kwargs['exif'] = exif_data
                            image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                            image.save(current_path, **save_kwargs)
                        os.utime(current_path, (original_atime, original_mtime))
                        if sys.platform == 'win32':
                            set_creation_time(current_path, original_ctime)
                        changes_log += (
                            f"RESIZED: {current_path} from ({old_w}x{old_h}) to ({new_w}x{new_h})\n"
                        )
                        yield changes_log
                    except OSError as e:
                        skipped_files += 1
                        changes_log += f"SKIPPED (Resize Error: {str(e)}): {current_path}\n"
                        yield changes_log
                        continue

                if rename_needed:
                    unique_new_path = get_unique_path(
                        prospective_path,
                        is_hex=add_hex,
                        leave_as_is=(rename_option == "Leave as is")
                    )
                    if unique_new_path != current_path:
                        os.rename(current_path, unique_new_path)
                        changes_log += f"RENAMED: {current_path} → {unique_new_path}\n"
                        yield changes_log
                        current_path = unique_new_path

                if convert_needed:
                    try:
                        with Image.open(current_path) as image:
                            format_map = {
                                "JPG":  "JPEG",
                                "PNG":  "PNG",
                                "WEBP": "WEBP",
                                "BMP":  "BMP",
                                "TIFF": "TIFF"
                            }
                            target_format = format_map.get(convert_to, convert_to)
                            if target_format == "JPEG" and image.mode == "RGBA":
                                image = image.convert("RGB")
                            converted_path = get_unique_path(
                                os.path.splitext(current_path)[0] + f".{target_format.lower()}",
                                is_hex=add_hex
                            )
                            save_kwargs = {'format': target_format}
                            if exif_data and target_format in ['JPEG', 'WEBP', 'TIFF']:
                                save_kwargs['exif'] = exif_data
                            image.save(converted_path, **save_kwargs)
                            os.utime(converted_path, (original_atime, original_mtime))
                            if sys.platform == 'win32':
                                set_creation_time(converted_path, original_ctime)
                        changes_log += f"CONVERTED: {current_path} → {converted_path}\n"
                        yield changes_log
                        if converted_path != current_path:
                            os.remove(current_path)
                            current_path = converted_path
                    except Exception as e:
                        skipped_files += 1
                        changes_log += f"SKIPPED (Conversion Error: {str(e)}): {current_path}\n"
                        yield changes_log
                        continue

                if move_needed:
                    os.makedirs(final_subfolder, exist_ok=True)
                    target_path = get_unique_path(
                        os.path.join(final_subfolder, os.path.basename(current_path)),
                        leave_as_is=(rename_option == "Leave as is")
                    )
                    shutil.move(current_path, target_path)
                    changes_log += f"MOVED: {current_path} → {target_path}\n"
                    yield changes_log
                    os.utime(target_path, (original_atime, original_mtime))
                    if sys.platform == 'win32':
                        set_creation_time(target_path, original_ctime)

                modified_files += 1

            except (UnidentifiedImageError, OSError) as e:
                skipped_files += 1
                changes_log += f"SKIPPED (Error: {str(e)}): {os.path.join(root, file)}\n"
                yield changes_log
                continue

    remove_empty_folders(directory)
    summary = (
        f"\nDone!\nReorganized {modified_files} files in {directory}. "
        f"Skipped {skipped_files} files.\n"
    )
    changes_log += summary
    yield changes_log

def open_directory(directory):
    if os.path.exists(directory):
        subprocess.run(["explorer", directory], check=True)
        return "Directory opened in Windows Explorer."
    return "Error: Directory does not exist."

def interface():
    subfolder_options = [
        "Flatten files",
        "Create subfolders by creation month/year",
        "Create subfolders by creation week/month/year",
        "Leave current subfolder structure"
    ]
    filetype_options = ["PNG", "JPG", "WEBP", "BMP", "TIFF"]
    rename_options = [
        "Leave as is",
        "Create new names",
        "Add before current name",
        "Add after current name"
    ]
    convert_options = ["JPG", "PNG", "WEBP", "BMP", "TIFF", "None"]

    def toggle_resize(value):
        return gr.update(visible=(value == "Yes"))

    with gr.Blocks(title="Image Reorganizer",theme=theme) as app:
        with gr.Row():
            with gr.Column():
                directory = gr.Textbox(label="Enter Directory Path")
                subfolder_choice = gr.Dropdown(
                    label="Subfolder Handling",
                    choices=subfolder_options,
                    value="Leave current subfolder structure"
                )
                filetypes = gr.CheckboxGroup(
                    label="File Types to Reorganize",
                    choices=filetype_options,
                    value=["PNG", "JPG", "WEBP"]
                )
                convert_to = gr.Radio(
                    label="Convert Files To",
                    choices=convert_options,
                    value="None"
                )

            with gr.Column():
                rename_choice = gr.Radio(
                    label="Rename Options",
                    choices=rename_options,
                    value="Leave as is"
                )
                add_hex = gr.Checkbox(label="Add Random 6-digit Hexadecimal Key", value=True)
                add_parent_folder = gr.Checkbox(label="Add Immediate Parent Folder Name")
                add_dimensions = gr.Checkbox(label="Add Image Dimensions to Filename")
                duplicate_handling = gr.Checkbox(
                    label="Handle Duplicate Filenames (e.g., add _01, _02)",
                    value=True,
                    visible=False
                )
                with gr.Row():
                    resize_radio = gr.Radio(
                        label="Resize Files?",
                        choices=["Yes", "No"],
                        value="No"
                    )
                    resize_to = gr.Slider(
                        label="Cap filesize (Megapixels)",
                        minimum=0.1,
                        maximum=10.0,
                        step=0.1,
                        value=1.0,
                        interactive=True,
                        visible=False
                    )
                    max_filesize = gr.Slider(
                        label="Maximum File Size to Reorganize (MB)",
                        minimum=1,
                        maximum=100,
                        step=1,
                        value=10,
                        interactive=True
                    )
                resize_radio.change(
                    toggle_resize,
                    inputs=resize_radio,
                    outputs=resize_to
                )
        with gr.Row():
            execute_button = gr.Button("Execute")
            open_button = gr.Button("Open Target Directory")
        output = gr.Textbox(label="Output Log (Streamed in Real Time)", lines=8)

        execute_button.click(
            fn=reorganize_files_stream,
            inputs=[
                directory,
                subfolder_choice,
                filetypes,
                rename_choice,
                add_hex,
                add_parent_folder,
                add_dimensions,
                duplicate_handling,
                convert_to,
                resize_radio,
                resize_to,
                max_filesize
            ],
            outputs=output
        )
        open_button.click(
            open_directory,
            inputs=directory,
            outputs=output
        )
    return app

if __name__ == "__main__":
    app = interface()
    # Use the JSON setting to determine the server address.
    server_name = "127.0.0.1"
    print("Reorganize Files app will launch with server_name:", server_name)
    app.launch(server_name=server_name, server_port=7864, inbrowser=True)
