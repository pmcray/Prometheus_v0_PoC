import json
import os

notebook_path = os.path.join("notebooks", "good_notebook_6_game_learning_comparison.ipynb")

if not os.path.exists(notebook_path):
    print(f"Error: Notebook not found at {notebook_path}")
    exit(1)

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Find the cell that writes the output json file
modified = False
for cell in nb.get("cells", []):
    if cell.get("cell_type") == "code":
        source = cell.get("source", [])
        source_str = "".join(source)
        if "out_path = 'go_game_learning_results.json'" in source_str and "export_output_file" not in source_str:
            new_source = []
            for line in source:
                new_source.append(line)
                if "json.dump(output, f, indent=2)" in line:
                    new_source.append("\n")
                    new_source.append("from prometheus.utils.colab_sync import export_output_file\n")
                    new_source.append("export_output_file('go_game_learning_results.json')\n")
                    new_source.append("export_output_file('go_accuracy_comparison.png')\n")
                    new_source.append("export_output_file('prometheus_synaptic_mutation.png')\n")
                    new_source.append("export_output_file('prometheus_strange_loop.png')\n")
                    new_source.append("export_output_file('architecture_comparison_table.png')\n")
            cell["source"] = new_source
            modified = True
            print("Successfully updated the final cell of the notebook with export_output_file calls.")
            break

if modified:
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
else:
    print("Notebook was already updated or target cell was not found.")
