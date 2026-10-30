
#* scripts/locate_iverilog_executable.py

#* ======= Libraries =======
# ------- Natives. -------
import os
import shutil

from pathlib import Path

def locate_iverilog_executable(hardcoded_iverilog_path: Path | None = None) -> Path:
    # ------- Layer-wise Search of Iverilog Executable. -------
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