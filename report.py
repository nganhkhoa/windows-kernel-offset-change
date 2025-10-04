import os
from pathlib import Path
from typing import Dict, List, Any, Optional

def parse_info_file(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Parses an info.txt file according to the specified format.

    Args:
        filepath: The Path object for the info.txt file.

    Returns:
        A dictionary containing the version prefix and the parsed data,
        or None if the file could not be read or the format is invalid.
    """
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
    except IOError as e:
        print(f"Error reading file {filepath}: {e}")
        return None

    if not lines:
        return None

    # 1. Parse the first line for the version
    first_line = lines[0].strip()
    # Expected format: "Some text - some-version"
    try:
        # Split by " - " to isolate the version part
        version_part = first_line.split(" - ", 1)[-1]
        # Split version by dot and exclude the last item
        version_parts = version_part.split('.')
        version_prefix = ".".join(version_parts[:-1])
        os = first_line.split(" - ", 1)[0]
        build = version_parts[-1]
    except IndexError:
        print(f"Skipping {filepath}: First line format is incorrect.")
        return None

    data: Dict[str, Dict[str, Any]] = {
        "symbols": {},
        "structs": {}
    }

    # Process the remaining lines
    content_lines = [line.strip() for line in lines[1:] if line.strip()]

    # 2. Next 7 lines are "some-hex-number some-symbol-name" (Symbols)
    symbols_lines = content_lines[:7]
    for line in symbols_lines:
        try:
            # Split by space, expecting exactly two parts
            hex_value, symbol_name = line.split()
            # Ensure hex value is stored as a string or convert to int/bytes if needed
            # Storing as string of hex for flexibility

            # The structure is: "symbols" -> "some-symbol-name" -> list of its-hex-value
            if symbol_name not in data["symbols"]:
                data["symbols"][symbol_name] = []
            data["symbols"][symbol_name].append(hex_value)
        except ValueError:
            print(f"Warning: Skipping malformed symbol line in {filepath}: '{line}'")
            continue

    # 3. The rests are "some-hex-number some-text some-member-name" (Structs/Members)
    structs_lines = content_lines[7:]
    for line in structs_lines:
        try:
            # Split by space, expecting at least three parts
            parts = line.split()
            if len(parts) < 3:
                raise ValueError("Not enough parts")

            # The first part is hex, the last is member name
            hex_value = parts[0]
            member_name = parts[-1]

            # The structure is: "structs" -> "some-member-name" -> list of its-hex-value
            if member_name not in data["structs"]:
                data["structs"][member_name] = []
            data["structs"][member_name].append(hex_value)
        except ValueError:
            print(f"Warning: Skipping malformed struct/member line in {filepath}: '{line}'")
            continue

    return {
        "version_prefix": version_prefix,
        "build": build,
        "os": os,
        "data": data
    }


def process_root_directory(root_dir: str = "root/") -> Dict[str, Dict[str, Any]]:
    """
    Loops through all nested folders, finds info.txt, parses it, and aggregates the data.

    Args:
        root_dir: The root directory to start the search from.

    Returns:
        The final aggregated hash map.
    """
    root_path = Path(root_dir)
    # The final aggregated data structure
    aggregated_data: Dict[str, Dict[str, Any]] = {}

    print(f"Starting search in: {root_path.resolve()}")

    # Use rglob to recursively find all 'info.txt' files in all subdirectories
    for info_file_path in root_path.rglob("info.txt"):
        print(f"\nProcessing file: {info_file_path}")

        parsed_result = parse_info_file(info_file_path)

        if parsed_result is None:
            continue

        version_prefix = parsed_result["version_prefix"]
        file_data = parsed_result["data"]

        print(f"  -> Version Prefix: {version_prefix}")

        # Initialize the version_prefix entry if it doesn't exist
        if version_prefix not in aggregated_data:
            aggregated_data[version_prefix] = {
                "builds": [parsed_result["build"]],
                "os": parsed_result["os"],
                "symbols": {},
                "structs": {}
            }
        else:
            aggregated_data[version_prefix]["builds"] += [parsed_result["build"]]

        # Merge the parsed data into the aggregated structure

        # Merge Symbols
        for symbol_name, hex_values in file_data["symbols"].items():
            if symbol_name not in aggregated_data[version_prefix]["symbols"]:
                aggregated_data[version_prefix]["symbols"][symbol_name] = []

            # Use a set temporarily to ensure uniqueness of hex values across different info.txt files
            # for the same version prefix, then convert back to a list.
            existing_hexes = set(aggregated_data[version_prefix]["symbols"][symbol_name])
            new_hexes = [h for h in hex_values if h not in existing_hexes]
            aggregated_data[version_prefix]["symbols"][symbol_name].extend(new_hexes)

        # Merge Structs
        for member_name, hex_values in file_data["structs"].items():
            if member_name not in aggregated_data[version_prefix]["structs"]:
                aggregated_data[version_prefix]["structs"][member_name] = []

            # Ensure uniqueness for struct/member hex values as well
            existing_hexes = set(aggregated_data[version_prefix]["structs"][member_name])
            new_hexes = [h for h in hex_values if h not in existing_hexes]
            aggregated_data[version_prefix]["structs"][member_name].extend(new_hexes)

    return aggregated_data

# --- Script Execution ---
if __name__ == "__main__":
    # Define the root directory
    ROOT_DIRECTORY = "files/"

    # --- IMPORTANT SETUP: Create Dummy Folders/Files for Testing ---
    # You MUST create the 'root/' directory and some nested structure
    # and 'info.txt' files to run this successfully.
    # The following block is an example of how you can set it up:

    print("Setting up dummy structure for testing...")

    # Define dummy file paths and content
    # DUMMY_FILES = {
    #     "root/v1/info.txt": [
    #         "Program Info - 1.2.345",
    #         "0xFEEDFACE Some_Global_Symbol",
    #         "0xDEADBEEF Another_Symbol",
    #         "0x00000000 Symbol_Three",
    #         "0x11111111 Symbol_Four",
    #         "0x22222222 Symbol_Five",
    #         "0x33333333 Symbol_Six",
    #         "0x44444444 Symbol_Seven",
    #         "0x00000004 StructName member_one",
    #         "0x00000008 OtherStruct member_two",
    #         "0x0000000C StructName member_three",
    #     ],
    #     "root/sub/v2/info.txt": [
    #         "Project Beta - 4.5.678",
    #         "0xAB00AB00 Sym_One",
    #         "0xCD00CD00 Sym_Two",
    #         "0x10001000 Sym_Three",
    #         "0x20002000 Sym_Four",
    #         "0x30003000 Sym_Five",
    #         "0x40004000 Sym_Six",
    #         "0x50005000 Sym_Seven",
    #         "0x00000010 DataBlock member_a",
    #         "0x00000014 DataBlock member_b",
    #     ],
    #     # A file with the same version prefix to test merging
    #     "root/another_v1/info.txt": [
    #         "Program Patch - 1.2.999",
    #         "0xCAFECAFE Some_Global_Symbol", # Duplicate symbol name, will merge hex values
    #         "0x66666666 New_Symbol",
    #         "0x77777777 S3",
    #         "0x88888888 S4",
    #         "0x99999999 S5",
    #         "0xAAAAABAB S6",
    #         "0xBBBBBCBC S7",
    #         "0x00000010 OtherStruct member_two", # Duplicate member name, will merge hex values
    #         "0x00000020 DifferentStruct member_z",
    #     ],
    # }

    # Clean up and create dummy files
    # if Path(ROOT_DIRECTORY).exists():
    #     import shutil
    #     shutil.rmtree(ROOT_DIRECTORY)

    # for file_path_str, content_lines in DUMMY_FILES.items():
    #     file_path = Path(file_path_str)
    #     file_path.parent.mkdir(parents=True, exist_ok=True)
    #     with open(file_path, 'w') as f:
    #         f.write('\n'.join(content_lines) + '\n')

    # print("Dummy structure created successfully.")
    # --- END OF SETUP BLOCK ---


    # Run the main function
    result_map = process_root_directory(ROOT_DIRECTORY)

    # Output the final result
    import json
    print("\n" + "="*50)
    print("FINAL AGGREGATED HASH MAP:")
    print("="*50)
    # Use json.dumps for pretty printing the final dictionary
    json.dump(result_map, open("symbols.json", "w"), indent=4)
    print(json.dumps(result_map, indent=4))
    print("="*50)

    # Optional: Clean up the dummy directory
    # import shutil
    # shutil.rmtree(ROOT_DIRECTORY)
