
#* scripts/locate_executables.py

#* ======= Libraries =======
# ------- Natives. -------
import os
import shutil

from pathlib import Path

#* ======= Iverilog Executable Location =======
def locate_iverilog_executable(hardcoded_iverilog_path: Path | None = None) -> Path:
    """
    Performs a multi-tier search to locate the Icarus Verilog ('iverilog') executable binary.

    The search hierarchy checks:
    1. System 'PATH' environment variable via shell lookup.
    2. The 'IVERILOG_HOME' environment variable.
    3. Standard operating system installation paths (Windows and Linux).
    4. An optional user-specified hardcoded fallback directory or binary path.

    Args:
        hardcoded_iverilog_path (Path | None): Optional filesystem path to an Icarus Verilog
            binary or installation directory to use as a final fallback. Defaults to None.

    Raises:
        FileNotFoundError: If the 'iverilog' executable cannot be resolved across any
            of the search tiers, with troubleshooting advice for Windows, Linux, and macOS.

    Returns:
        Path: Absolute filesystem path to the located 'iverilog' executable.
    """
    # ------- Layer-Wise Search of Iverilog Executable. -------
    # Finds out the OS.
    if (os.name == "nt"):
        iverilog_executable_relative_path = Path("bin/iverilog.exe")
    else:
        iverilog_executable_relative_path = Path("bin/iverilog")

    # Searches in system 'PATH'.
    iverilog_system_path: str | None = shutil.which(cmd = "iverilog")
    if iverilog_system_path:
        return Path(iverilog_system_path)

    # Searches in system environment variables.
    iverilog_env_dir: str | None = os.environ.get("IVERILOG_HOME", None)
    if iverilog_env_dir:
        # Combines the folder path with the executable path.
        iverilog_path: Path = Path(iverilog_env_dir) / iverilog_executable_relative_path

        if iverilog_path.is_file():
            return iverilog_path

    # Searches in common installation directories.
    iverilog_common_installation_dirs: list[Path] = [
        # Windows.
        Path("C:/iverilog"),
        Path("C:/Program Files/iverilog"),

        # Linux.
        Path("/usr"),
        Path("/usr/local"),
        Path("/opt/iverilog")  
    ]

    for dir in iverilog_common_installation_dirs:
        if (dir.exists() and dir.is_dir()):
            iverilog_path: Path = dir / iverilog_executable_relative_path

            if iverilog_path.is_file():
                return iverilog_path

    # Checks the user-passed harcoded path.
    if hardcoded_iverilog_path:
        if hardcoded_iverilog_path.is_file():
            return hardcoded_iverilog_path

    # IF none of the paths are valid, than raises an error.
    fallback_info = f"'{hardcoded_iverilog_path}'" if hardcoded_iverilog_path else "None provided"

    raise FileNotFoundError(
        "\n"
        "================================================================================\n"
        "ERROR: Icarus Verilog ('iverilog') executable could not be located.\n"
        "================================================================================\n"
        "The simulation runner requires 'iverilog' and 'vvp' to compile and execute RTL.\n\n"
        "Searched Locations:\n"
        "  1. System 'PATH' environment variable.\n"
        "  2. 'IVERILOG_HOME' environment variable.\n"
        "  3. Standard platform installation directories:\n"
        f"     - {[str(p) for p in iverilog_common_installation_dirs]}\n"
        f"  4. User fallback path: {fallback_info}\n\n"
        "Recommendations:\n"
        "  - Windows: Run 'winget install -e --id Icarus.Verilog'\n"
        "  - Linux (Ubuntu/Debian): Run 'sudo apt-get install iverilog'\n"
        "  - macOS: Run 'brew install icarus-verilog'\n"
        "  - Or set the 'IVERILOG_HOME' environment variable to your installation directory.\n"
        "================================================================================"
    )

#* ======= Verilator Executable Location =======
def locate_verilator_executable(hardcoded_verilator_path: Path | None = None) -> Path:
    """
    Performs a multi-tier search to locate the Verilator ('verilator') executable binary.

    The search hierarchy checks:
    1. System 'PATH' environment variable via shell lookup.
    2. The 'VERILATOR_ROOT' environment variable.
    3. Standard operating system installation paths (Windows and Linux).
    4. An optional user-specified hardcoded fallback directory or binary path.

    Args:
        hardcoded_verilator_path (Path | None): Optional filesystem path to a Verilator
            binary or installation directory to use as a final fallback. Defaults to None.

    Raises:
        FileNotFoundError: If the 'verilator' executable cannot be resolved across any
            of the search tiers, with troubleshooting advice for Windows, Linux, and macOS.

    Returns:
        Path: Absolute filesystem path to the located 'verilator' executable.
    """
    # ------- Layer-Wise Search of Verilator Executable. -------
    # Finds out the OS.
    if (os.name == "nt"):
        verilator_executable_relative_path = Path("bin/verilator_bin.exe")
        verilator_cmd_name: str = "verilator_bin"
    else:
        verilator_executable_relative_path = Path("bin/verilator")
        verilator_cmd_name: str = "verilator"

    # Searches in system 'PATH'.
    verilator_system_path: str | None = shutil.which(cmd = verilator_cmd_name)
    if verilator_system_path:
        return Path(verilator_system_path)

    # Searches in system environment variables.
    verilator_env_dir: str | None = os.environ.get("VERILATOR_ROOT", None)
    if verilator_env_dir:
        # Combines the folder path with the executable path.
        verilator_path: Path = Path(verilator_env_dir) / verilator_executable_relative_path

        if verilator_path.is_file():
            return verilator_path

    # Searches in common installation directories.
    verilator_common_installation_dirs: list[Path] = [
        # Windows.
        Path("C:/verilator"),
        Path("C:/Program Files/verilator"),
        Path("C:/tools/verilator"),
        Path("C:/tools/oss-cad-suite"),
        Path("C:/msys64/mingw64"),

        # Linux.
        Path("/usr"),
        Path("/usr/local"),
        Path("/opt/verilator")
    ]

    for dir in verilator_common_installation_dirs:
        if (dir.exists() and dir.is_dir()):
            verilator_path: Path = dir / verilator_executable_relative_path

            if verilator_path.is_file():
                return verilator_path

    # Checks the user-passed harcoded path.
    if hardcoded_verilator_path:
        if hardcoded_verilator_path.is_file():
            return hardcoded_verilator_path

    # IF none of the paths are valid, than raises an error.
    fallback_info = f"'{hardcoded_verilator_path}'" if hardcoded_verilator_path else "None provided"

    raise FileNotFoundError(
        "\n"
        "================================================================================\n"
        "ERROR: Verilator ('verilator') executable could not be located.\n"
        "================================================================================\n"
        "The static analysis runner requires 'verilator' to perform DO-254 semantic linting.\n\n"
        "Searched Locations:\n"
        "  1. System 'PATH' environment variable.\n"
        "  2. 'VERILATOR_ROOT' environment variable.\n"
        "  3. Standard platform installation directories:\n"
        f"     - {[str(p) for p in verilator_common_installation_dirs]}\n"
        f"  4. User fallback path: {fallback_info}\n\n"
        "Recommendations:\n"
        "  - Windows: Run 'choco install verilator' or 'scoop install verilator'\n"
        "  - Linux (Ubuntu/Debian): Run 'sudo apt-get install verilator'\n"
        "  - macOS: Run 'brew install verilator'\n"
        "  - Or set the 'VERILATOR_ROOT' environment variable to your installation directory.\n"
        "================================================================================"
    )