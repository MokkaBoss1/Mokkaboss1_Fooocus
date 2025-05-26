import gradio as gr

# Define the number of columns and rows for the table
num_columns = 27
num_rows = 10

# Labeling the columns from the second to the twenty-seventh as "Wk 1", "Wk 2", "Wk 3", etc.
columns = [""] + [f"Wk {i}" for i in range(1, 27)]

# Define row labels
row_labels = ["Demand", "Supply", "Projected Balance", "Total Safety", "Days Supply"]

# Create an empty table with the specified dimensions and set row labels for the first 5 rows
table_data = [[""] * num_columns for _ in range(num_rows)]
for i, label in enumerate(row_labels):
    table_data[i][0] = label

# Define a function to update the table data (this is just a placeholder)
def update_table(new_data):
    return new_data

# Create Gradio interface components
with gr.Blocks() as demo:
    # Create an input component for updating the table
    text_input = gr.Textbox(label="Enter new data")

    # Create a button to trigger the table update
    update_button = gr.Button("Update Table")

    # Create the table component with the specified dimensions
    table = gr.Dataframe(
        headers=columns,
        value=table_data,
        interactive=True
    )

    # Define the function to be called when the button is clicked
    update_button.click(update_table, inputs=text_input, outputs=table)

# Launch the Gradio interface
demo.launch()