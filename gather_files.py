def extract_file_content_and_write(file_paths, output_file="file_contents.txt"):
    """
    Extracts the content of files specified by their paths and writes them to a text file.

    Args:
        file_paths: A list or iterable of file paths.
        output_file: The name of the output text file.
    """

    with open(output_file, "w") as outfile:
        for file_path in file_paths:
            try:
                with open(file_path, "r") as infile:
                    content = infile.read()
                    outfile.write(f"File Path: {file_path}\n")
                    outfile.write(content + "\n\n")
            except FileNotFoundError:
                print(f"Warning: File not found at {file_path}")


# Example Usage:
#  Define your list of file paths (can be a list, or a list of lists, etc.)
#  The order of files in the list will dictate their order in the output file
file_list = [
    # "backend/cli.py",
    # "backend/data_sources/yahoo.py",
    # "backend/data_sources/fantasypros.py",
    # "backend/pipelines/enrich.py",
    # "backend/pipelines/stats.py",
    # "backend/transforms/compute_ppg.py",
    # "backend/settings.py",
    # "backend/models.py",
    # "backend/pipelines/vor.py",
    "index.html",
    "index.tsx",
    "metadata.json",
    "package.json",
    "README.md",
    "tsconfig.json",
    "vite.config.ts",
]

#  Run the function to extract and write the contents
extract_file_content_and_write(file_list)
print("Done!  File contents written to file_contents.txt")
