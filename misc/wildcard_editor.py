import os
import gradio as gr
import json

# Theme configuration
CONFIG_FILENAME = "theme_config.json"
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", CONFIG_FILENAME)

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

def get_wildcards_path():
    # One level up from this script, in "wildcards/"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wildcards_dir = os.path.abspath(os.path.join(script_dir, "..", "wildcards"))
    
    # Create the directory if it doesn't exist
    if not os.path.exists(wildcards_dir):
        try:
            os.makedirs(wildcards_dir, exist_ok=True)
        except Exception as e:
            print(f"Error creating wildcards directory: {e}")
    
    return wildcards_dir

def get_file_list(dir_path):
    """Return a sorted list of .txt filenames in dir_path, including subdirectories."""
    try:
        txt_files = []
        for root, _, files in os.walk(dir_path):
            for f in files:
                if f.lower().endswith(".txt"):
                    # Get relative path from the base dir
                    rel_path = os.path.relpath(os.path.join(root, f), dir_path)
                    # Convert Windows backslashes to forward slashes for consistency
                    rel_path = rel_path.replace('\\', '/')
                    txt_files.append(rel_path)
        return sorted(txt_files, key=str.lower)  # Case-insensitive sort
    except Exception:
        return []

def load_file_content(dir_path, filename):
    """Read and return the content of filename under dir_path as a list of rows."""
    # Only called on explicit user actionfilename is guaranteed a string
    if not filename:
        return [[""]]
    # First check if the file exists in the current file list
    all_files = get_file_list(dir_path)
    if filename not in all_files:
        return [["File no longer exists. Please select another file."]]
    # Use correct path joining for subdirectories
    full_path = os.path.join(dir_path, filename.replace('/', os.sep))
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            # Each line is a single cell now
            content = [[line] for line in lines]
            # If we have fewer than 15 lines, pad with empty lines
            while len(content) < 15:
                content.append([""])
            return content or [[""]]
    except Exception as e:
        return [[f"Error loading file: {e}"]]

def save_file_content(dir_path, filename, content_rows):
    """Overwrite filename under dir_path with content from rows, return status."""
    if not filename:
        return "No file selected."
    full_path = os.path.join(dir_path, filename.replace('/', os.sep))
    # Ensure directory exists for files in subdirectories
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    try:
        # Convert content rows to list if it's a DataFrame
        if hasattr(content_rows, 'values'):
            content_rows = content_rows.values.tolist()
        # Process each row and build content
        lines = []
        for row in content_rows:
            # Each row is now a single-element list
            if isinstance(row, (list, tuple)) and len(row) >= 1:
                line = str(row[0]).rstrip()
                # Only include non-empty lines
                if line:
                    lines.append(line)
        # Join all valid lines with newlines
        content = '\n'.join(lines)
        # Write to file
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
            # Add a final newline if there's content
            if content:
                f.write("\n")
        return "File saved successfully!"
    except Exception as e:
        return f"Error saving file: {e}"

def search_and_replace(content_rows, search_text, replace_text, case_sensitive=False):
    """Search and replace text in content rows."""
    if not search_text:
        return content_rows, "Search text is empty."
    
    total_count = 0
    new_content_rows = []
    for row in content_rows:
        # Each row is now a single-element list
        content = row[0] if len(row) > 0 else ""
        if not case_sensitive:
            import re
            pattern = re.compile(re.escape(search_text), re.IGNORECASE)
            new_content = pattern.sub(replace_text, content)
            count = len(pattern.findall(content))
        else:
            count = content.count(search_text)
            new_content = content.replace(search_text, replace_text)
        total_count += count
        new_content_rows.append([new_content])
    if total_count > 0:
        return new_content_rows, f"Replaced {total_count} occurrence{'s' if total_count > 1 else ''}."
    else:
        return content_rows, "No matches found."

def create_new_file(dir_path, new_filename, content=""):
    """Create a new text file with given name and optional content."""
    # Add .txt extension if not present
    if not new_filename:
        return "Filename cannot be empty.", None
    
    if not new_filename.lower().endswith(".txt"):
        new_filename += ".txt"
    
    full_path = os.path.join(dir_path, new_filename)
    
    # Check if file already exists
    if os.path.exists(full_path):
        return f"File '{new_filename}' already exists.", None
    
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Get updated file list
        files = get_file_list(dir_path)
        
        return f"File '{new_filename}' created successfully!", files
    except Exception as e:
        return f"Error creating file: {e}", None

def delete_file(dir_path, filename):
    """Delete the specified file from the directory."""
    if not filename:
        return "No file selected.", None
    
    full_path = os.path.join(dir_path, filename)
    
    # Check if file exists
    if not os.path.exists(full_path):
        return f"File '{filename}' does not exist.", None
    
    try:
        os.remove(full_path)
        
        # Get updated file list
        files = get_file_list(dir_path)
        
        return f"File '{filename}' deleted successfully!", files
    except Exception as e:
        return f"Error deleting file: {e}", None

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Wildcards Editor")
    parser.add_argument("--port", type=int, default=7862, help="Port to run the server on")
    args = parser.parse_args()
    
    # 
    # ⅰ) Startup: compute everything before building the UI
    # 
    wildcards_dir   = get_wildcards_path()
    initial_files   = get_file_list(wildcards_dir)
    
    # Make sure we have at least one file, or create a default one
    if not initial_files:
        default_filename = "example.txt"
        default_content = "# This is an example wildcard file\n# Add your wildcards below, one per line"
        full_path = os.path.join(wildcards_dir, default_filename)
        
        # Create the wildcards directory if it doesn't exist
        if not os.path.exists(wildcards_dir):
            os.makedirs(wildcards_dir, exist_ok=True)
            
        # Create a default file
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(default_content)
            initial_files = get_file_list(wildcards_dir)
        except Exception:
            # If we can't create a file, just continue with empty list
            pass
    
    initial_file    = initial_files[0] if initial_files else None
    initial_content = load_file_content(wildcards_dir, initial_file) if initial_file else [[1, ""]]

    # Add custom CSS for the table and delete button
    custom_css = """
    /* Title styling */
    .prose h1, .prose p {
        font-size: 2rem !important;
        margin-bottom: 0.5em !important;
        font-weight: bold !important;
    }
    
    .wildcard-table {
        min-height: 450px !important;
        height: calc(100vh - 70px) !important;
        overflow-y: auto !important;
    }
    
    .delete-btn button {
        background-color: #d32f2f !important;
        color: white !important;
    }
    
    .delete-btn button:hover {
        background-color: #b71c1c !important;
    }

    /* Make the line number column narrower */
    .wildcard-table table td:first-child,
    .wildcard-table table th:first-child {
        width: 80px !important;
    }
    """

    # 
    # ⅱ) Build the Gradio UI exactly once, statically
    # 
    with gr.Blocks(title=u"🎲 Wildcards Editor", theme=theme, css=custom_css) as demo:
        gr.Markdown("🎲 Fooocus Wildcards Text Editor")

        # Directory input (hidden but still accessible to the code)
        dir_input = gr.Textbox(
            label="Directory Path",
            value=wildcards_dir,
            interactive=True,
            visible=False
        )

        # Hidden reload button (needed for functionality)
        reload_btn = gr.Button("Reload Files", visible=False)

        # Create a two-column layout with table and controls
        with gr.Row():
            # Left column: File content (3/5 width)
            with gr.Column(scale=3):
                # 5) Table showing the file contents (line numbers now only via show_row_numbers)
                # Defensive: support both [[content], ...] and [[idx, content], ...] for legacy/empty/error
                def _extract_content_rows(rows):
                    result = []
                    for row in rows:
                        if isinstance(row, (list, tuple)):
                            if len(row) == 1:
                                result.append([row[0]])
                            elif len(row) > 1:
                                result.append([row[1]])
                            else:
                                result.append([""])
                        else:
                            result.append([str(row)])
                    return result

                text_area = gr.Dataframe(
                    label="File Content",
                    headers=["Content"],
                    col_count=(1, "fixed"),
                    datatype=["str"],
                    value=_extract_content_rows(initial_content),
                    row_count=30,
                    wrap=True,
                    interactive=True,
                    elem_classes="wildcard-table",
                    show_fullscreen_button=True,
                    max_height=700,
                    show_row_numbers=True,
                    show_search=["Filter"],
                    column_widths=["auto"]
                )

                def handle_dataframe_edit(df):
                    import pandas as pd
                    # Make sure we have a DataFrame
                    if not isinstance(df, pd.DataFrame):
                        return [[""]]
                    # Convert DataFrame to list for processing
                    rows = df.values.tolist() if not df.empty else []
                    # If there are no rows or last row has content, add a new row
                    if not rows or (len(rows) > 0 and str(rows[-1][0]).strip()):
                        rows.append([""])
                    return rows

                text_area.change(
                    fn=handle_dataframe_edit,
                    inputs=[text_area],
                    outputs=[text_area]
                )

                def remove_empty_rows(df):
                    import pandas as pd
                    if not isinstance(df, pd.DataFrame) or df.empty:
                        return [[""]]
                    # Convert to list and filter out empty rows
                    rows = df.values.tolist()
                    non_empty_rows = [row for row in rows if str(row[0]).strip()]
                    # If all rows were empty, return a single empty row
                    if not non_empty_rows:
                        return [[""]]
                    # Ensure we have at least 15 rows
                    while len(non_empty_rows) < 15:
                        non_empty_rows.append([""])
                    return non_empty_rows
            
            # Right column: All controls (2/5 width)
            with gr.Column(scale=2):
                # File management section
                gr.Markdown("### File Management")
                with gr.Row():
                    file_dropdown = gr.Dropdown(
                        label="Select Text File",
                        choices=initial_files,
                        value=initial_file,
                        allow_custom_value=False,
                        interactive=True,
                        scale=2
                    )
                    new_filename = gr.Textbox(
                        label="New File Name",
                        placeholder="Enter name...",
                        interactive=True,
                        scale=1
                    )
                    create_btn = gr.Button("Create", variant="primary", scale=1)
                
                # Row resequencing section
                gr.Markdown("### Change Row Sequence")
                with gr.Row():
                    row_number = gr.Number(
                        label="Row No.",
                        minimum=1,
                        precision=0,
                        scale=1,
                        interactive=True
                    )
                    move_to_top_btn = gr.Button("Move to Top", variant="secondary", scale=2)
                
                # Search and Replace section
                gr.Markdown("### Search and Replace (Ctrl+F for quick search)")
                with gr.Row():
                    search_text = gr.Textbox(label="Search", placeholder="Text to find...", scale=2)
                    replace_text = gr.Textbox(label="Replace", placeholder="Replace with...", scale=2)
                    search_btn = gr.Button("Find & Replace", variant="secondary", scale=1)
                case_sensitive = gr.Checkbox(label="Case Sensitive", value=True, scale=1, visible=False)
                
                # 7) Buttons section
                gr.Markdown("### Actions")
                with gr.Row():
                    save_btn = gr.Button("Save Selected File", variant="primary", scale=1)
                    delete_btn = gr.Button("Delete Selected File", variant="secondary", elem_classes="delete-btn", scale=1)
                    remove_empty_btn = gr.Button("Remove Empty Rows", variant="secondary", scale=1)
                
                # Delete confirmation buttons (initially hidden)
                with gr.Row(visible=False) as delete_confirm_row:
                    confirm_delete_btn = gr.Button("Yes, Delete", variant="stop", scale=1)
                    cancel_delete_btn = gr.Button("Cancel", variant="secondary", scale=1)
                
                # Status textbox - defined here before it's referenced
                # Used for both status messages and delete confirmations
                status = gr.Textbox(
                    label="Status / Confirmation",
                    interactive=False
                )

                # Add a button to open the wildcards folder (below status)
                open_folder_btn = gr.Button("Open wildcards folder in Explorer", elem_id="open-folder-btn")

                def open_wildcards_folder():
                    import subprocess, sys
                    folder = wildcards_dir
                    try:
                        if sys.platform.startswith('win'):
                            subprocess.Popen(['explorer', folder])
                        elif sys.platform.startswith('darwin'):
                            subprocess.Popen(['open', folder])
                        else:
                            subprocess.Popen(['xdg-open', folder])
                        return "Opened wildcards folder."
                    except Exception as e:
                        return f"Error opening folder: {e}"

                open_folder_btn.click(
                    fn=open_wildcards_folder,
                    inputs=[],
                    outputs=[status]
                )
                
                # Add click handler for remove empty rows button
                remove_empty_btn.click(
                    fn=remove_empty_rows,
                    inputs=[text_area],
                    outputs=[text_area]
                )
                
                def move_row_to_top(df, target_row):
                    import pandas as pd
                    if not isinstance(df, pd.DataFrame) or df.empty:
                        return [[""]], "Invalid input"
                    # Convert to list for processing
                    rows = df.values.tolist()
                    # Validate row number
                    if not target_row or target_row < 1 or target_row > len(rows):
                        return rows, "Invalid row number"
                    # Find the target row (1-based index)
                    target_idx = int(target_row) - 1
                    # Defensive: support both [[content], ...] and [[idx, content], ...]
                    row = rows[target_idx]
                    if isinstance(row, (list, tuple)):
                        if len(row) == 1:
                            target_content = row[0]
                        elif len(row) > 1:
                            target_content = row[1]
                        else:
                            target_content = ""
                    else:
                        target_content = str(row)
                    # Remove the target row and reinsert at top
                    rows.pop(target_idx)
                    rows.insert(0, [target_content])
                    # Ensure all rows are single-element lists
                    numbered_rows = [[r[0] if isinstance(r, (list, tuple)) and len(r) > 0 else str(r)] for r in rows]
                    return numbered_rows, f"Moved row {target_row} to top"
                
                # Add click handler for move to top button
                move_to_top_btn.click(
                    fn=move_row_to_top,
                    inputs=[text_area, row_number],
                    outputs=[text_area, status]
                )

        # 
        # Handlers
        # 
        # Reload: re-scan directory & refresh dropdown & textarea
        def reload(dir_path):
            files = get_file_list(dir_path)
            first = files[0] if files else None
            content = load_file_content(dir_path, first) if first else ""
            
            # Use gr.update to ensure dropdown is correctly updated
            return (
                gr.update(choices=files, value=first),  # New dropdown choices with selected value
                content,  # New content for the text area
            )
        reload_btn.click(
            fn=reload,
            inputs=[dir_input],
            outputs=[file_dropdown, text_area],
        )

        # Create new file handler
        def create_file_handler(dir_path, filename, current_dropdown):
            # Ensure filename has .txt extension for creation
            if not filename.lower().endswith('.txt'):
                filename_with_ext = filename + '.txt'
            else:
                filename_with_ext = filename
                
            # Create initial content with 15 empty lines
            initial_content = "\n" * 14  # 14 newlines creates 15 empty lines
            message, new_files = create_new_file(dir_path, filename, initial_content)
            
            if new_files:
                # Find the exact filename as it appears in the file list
                selected_file = None
                for file in new_files:
                    if file.lower() == filename_with_ext.lower():
                        selected_file = file
                        break
                
                if not selected_file and new_files:
                    # Fallback to the first file if somehow we can't find the new file
                    selected_file = new_files[0]
                
                # Load the content of the newly created file
                # Initialize with 15 empty numbered lines
                content = [[i+1, ""] for i in range(15)]
                
                return (
                    message,                    # Status message
                    gr.update(choices=new_files, value=selected_file),  # Update dropdown with new files list and select the new file
                    selected_file,              # Set the selected file using exact format from the list
                    "",                         # Clear the new filename input
                    content                     # Show the new file content (empty)
                )
            else:
                # Just show the error message
                return message, current_dropdown, None, "", None
            
        create_btn.click(
            fn=create_file_handler,
            inputs=[dir_input, new_filename, file_dropdown],
            outputs=[status, file_dropdown, file_dropdown, new_filename, text_area]
        )

        # When the user explicitly picks a file, load _that_ file
        # Define a safer file change handler that handles errors gracefully
        def on_file_change(dir_path, filename):
            content = load_file_content(dir_path, filename)
            return content
            
        file_dropdown.change(
            fn=on_file_change,
            inputs=[dir_input, file_dropdown],
            outputs=[text_area],
        )

        # Save edits
        save_btn.click(
            fn=save_file_content,
            inputs=[dir_input, file_dropdown, text_area],
            outputs=[status],
        )
        
        # Search and replace handler
        def search_and_replace_handler(content, search, replace, case_sensitive):
            new_content, result_msg = search_and_replace(content, search, replace, case_sensitive)
            return new_content, result_msg
            
        search_btn.click(
            fn=search_and_replace_handler,
            inputs=[text_area, search_text, replace_text, case_sensitive],
            outputs=[text_area, status],
        )
        
        # Delete file handler
        def delete_file_handler(dir_path, filename):
            if not filename:
                return "No file selected for deletion.", None, None, ""
                
            message, new_files = delete_file(dir_path, filename)
            
            # Select a new file after deletion
            new_selected_file = None
            content = ""
            
            if new_files and len(new_files) > 0:
                new_selected_file = new_files[0]  # Select the first file
                content = load_file_content(dir_path, new_selected_file)
            
            # Return updated dropdown with proper choices and value
            return message, gr.update(choices=new_files, value=new_selected_file), new_selected_file, content
            
        # Function to handle delete confirmation
        def show_delete_confirmation(filename):
            if not filename:
                return "Please select a file to delete.", gr.update(visible=False)
            return f"CONFIRMATION: Are you sure you want to delete '{filename}'?", gr.update(visible=True)
            
        # Function to hide confirmation buttons and clear status
        def hide_confirmation_elements():
            return "Ready", gr.update(visible=False)
            
        # First click shows confirmation
        delete_btn.click(
            fn=show_delete_confirmation,
            inputs=[file_dropdown],
            outputs=[status, delete_confirm_row]
        )
        
        # Confirm button actually deletes
        confirm_delete_btn.click(
            fn=delete_file_handler,
            inputs=[dir_input, file_dropdown],
            outputs=[status, file_dropdown, file_dropdown, text_area]
        ).then(
            fn=lambda: gr.update(visible=False),
            outputs=[delete_confirm_row]
        )
        
        # Cancel button just hides the confirmation
        cancel_delete_btn.click(
            fn=lambda: ("Delete cancelled", gr.update(visible=False)),
            outputs=[status, delete_confirm_row]
        )
        
        # Cancel deletion if user selects a different file
        file_dropdown.change(
            fn=lambda: gr.update(visible=False),
            outputs=[delete_confirm_row]
        )

    demo.launch(server_port=args.port, inbrowser=True, share=False)
