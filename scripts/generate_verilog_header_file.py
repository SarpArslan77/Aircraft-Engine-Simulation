
#* ======= Library =======
# ------- External. -------
from pathlib import Path

#* ======= Verilog Header File Generation =======
def generate_verilog_header_file(
        file_name: str,
        parameters: dict[str, int],
        verilog_header_file_dir_path: Path    
) -> None:
    """
    Generates an auto-generated synthesizable Verilog include header file (.vh).

    Translates a Python dictionary of quantized parameters and hardware constants into
    Verilog preprocessor macro definitions (`define <PARAM> <VALUE>). Constructs
    sanitized, uppercase include guards (`ifndef / `define / `endif) based on the filename
    to prevent multiple-inclusion collisions during RTL compilation and Vivado synthesis.

    Args:
        file_name (str): Target output filename including extension (e.g., 'top_module_params.vh').
        parameters (dict[str, int]): Dictionary mapping Verilog macro names to their integer
            values or quantized fixed-point representations.
        verilog_header_file_dir_path (Path): Filesystem directory path where the header file
            will be written.

    Returns:
        None
    """
    # Converts the filename into a standard uppercase guard without dots.
    guard_file_name: str = file_name.replace(".", "_").upper()

    #? `ifndef ... `endif: If Not Defined:
    #   -> NO: Continues compiling.
    #   -> YES: Skips everything between this line and the matching '`endif'.
    #? `define TOP_MODULE_PARAMS_VH (f.e.): Marks this as defined, works as a latch.
    lines: list[str] = [
        f"`ifndef {guard_file_name}",
        f"`define {guard_file_name}",
        "",
        "// Auto-generated header file",
        ""
    ]

    for parameter, value in parameters.items():
        # Defines verilog macros.
        lines.append(f"`define {parameter} {value}")

    lines.extend(
        [
            "",
            f"`endif // {guard_file_name}\n"
        ]    
    )

    # Saves the file.
    target_verilog_header_file_path: Path = verilog_header_file_dir_path / file_name

    try:
        # Ensures target directory exists.
        target_verilog_header_file_path.parent.mkdir(
            parents = True,
            exist_ok = True
        )

        with open(
            file = target_verilog_header_file_path,
            mode = "w",
            encoding = "utf-8"
        ) as f:
            f.write("\n".join(lines))
    except OSError as err:
        # Halts pipeline before Vivado or Icarus Verilog is invoked on a missing header.
        raise RuntimeError(
            f"Failed to write synthesizable Verilog header to '{target_verilog_header_file_path}': {err}"
        ) from err