
#* scripts/locate_executables.py

#* ======= Libraries =======
# ------- Natives. -------
import os
import shutil

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

#* ======= Executable Locater Config Dataclass =======
@dataclass(frozen = True, slots = True)
class ConfigExecutableLocater:
    """
    Configuration dataclass storing fallback executable filesystem paths.

    Holds user-configured or hardcoded fallback filesystem locations for
    EDA binary dependencies (Icarus Verilog and Verilator) when automated
    system PATH resolution and environment variable sweeps fail.

    Attributes:
        hardcoded_iverilog_path (Path | None): Optional filesystem path to an
            Icarus Verilog binary or installation root directory. Defaults to None.
        hardcoded_verilator_path (Path | None): Optional filesystem path to a
            Verilator binary or installation root directory. Defaults to None.
        hardcoded_vivado_path (Path | None): Optional filesystem path to a
            Vivado binary or installation root directory. Defaults to None.
    """
    # Hardcoded Paths.
    hardcoded_iverilog_path: Path | None = None
    hardcoded_verilator_path: Path | None = None
    hardcoded_vivado_path: Path | None = None

#* ======= Executable Locater Class =======
class ExecutableLocater:
    """
    Multi-tier filesystem search agent for EDA compiler and linter binaries.

    Coordinates layered, prioritized resolution strategies to locate target
    simulation and verification executables (Icarus Verilog and Verilator).
    Evaluates system PATH environments, dedicated vendor environment variables,
    standard platform directories, and hardcoded fallback configurations
    in non-blocking sequence to guarantee toolchain availability.
    """
    def __init__(
            self,
            config_executable_locater: ConfigExecutableLocater
    ) -> None:
        """
        Initializes the ExecutableLocater instance with locator configurations.

        Args:
            config_executable_locater (ConfigExecutableLocater): Dataclass holding
                configured user fallback filesystem paths for EDA binaries.

        Returns:
            None
        """
        self._cfg: ConfigExecutableLocater = config_executable_locater

    def _get_binary_name(
            self,
            windows_binary_name: str,
            linux_binary_name: str
    ) -> Path:
        """
        Resolves the platform-specific relative binary path based on host operating system.

        Selects between Windows and POSIX executable naming conventions (accounting
        for file extensions such as '.exe') based on the underlying runtime environment.

        Args:
            windows_binary_name (str): Relative binary path formatted for Windows (e.g., 'bin/iverilog.exe').
            linux_binary_name (str): Relative binary path formatted for Linux/POSIX (e.g., 'bin/iverilog').

        Returns:
            Path: Platform-appropriate relative executable filesystem path.
        """
        # Finds out the binary name from the OS.
        if (os.name == "nt"):
            return Path(windows_binary_name)
        else:
            return Path(linux_binary_name)

    def _search_in_system_path(
            self,
            system_cmds: str | tuple[str, ...]
    ) -> Path | None:
        """
        Scans directories registered in the system PATH environment variable for executable commands.

        Accepts a single command name or a priority-ordered collection of candidate
        binary aliases, resolving against the active system PATH shell lookup.

        Args:
            system_cmds (str | tuple[str, ...]): Target executable command name or tuple of
                alternative command identifiers to search sequentially.

        Returns:
            Path | None: Absolute filesystem path to the first resolved binary, or None if not found.
        """
        # Searches in system 'PATH'.
        #? tuple[str, ...]: A tuple containing any number of items, where every item is a 'str'
        #? (system_cmds,): Creates a 1-element tuple from a single string.
        cmds: tuple[str, ...] = (system_cmds,) if isinstance(system_cmds, str) else system_cmds 
        for cmd in cmds:
            executable_relative_path_str: str | None = shutil.which(cmd = cmd)
            if executable_relative_path_str is not None:
                return Path(executable_relative_path_str)

        return None

    def _search_in_common_installation_directories(
            self,
            executable_common_installation_directories: list[Path],
            executable_relative_path: Path
    ) -> Path | None:
        """
        Searches standard platform-specific default installation root directories.

        Traverses an ordered list of standard operating system installation roots
        (e.g., 'C:/Program Files', '/usr/local') testing for the presence of the
        specified relative binary executable.

        Args:
            executable_common_installation_directories (list[Path]): List of directory roots
                known to host the target software package.
            executable_relative_path (Path): Relative path from the root directory to the binary.

        Returns:
            Path | None: Absolute filesystem path to the discovered executable, or None if missing.
        """
        # Searches in common installation directories.
        for directory in executable_common_installation_directories:
            if (directory.exists() and directory.is_dir()):
                executable_path = directory / executable_relative_path
                if executable_path.is_file():
                    return executable_path

        return None

    def _check_hardcoded_path(
            self,
            hardcoded_executable_path: Path | None
    ) -> Path | None:
        """
        Validates the accessibility and file status of a user-supplied hardcoded path.

        Confirms whether an optional fallback configuration points to an existing,
        valid executable file on the local filesystem.

        Args:
            hardcoded_executable_path (Path | None): User-provided candidate path to test.

        Returns:
            Path | None: The validated filesystem path if it represents an existing file,
                otherwise None.
        """
        # Checks the user-passed hardcoded path.
        if hardcoded_executable_path is not None:
            if hardcoded_executable_path.is_file():
                return hardcoded_executable_path

        return None

    def _search_in_system_environment(
            self,
            environment_variable_name: str,
            executable_relative_path: Path
    ) -> Path | None:
        """
        Queries an environment variable for a root directory holding the target binary.

        Inspects the system environment for a dedicated package variable (e.g., 'VERILATOR_ROOT'
        or 'IVERILOG_HOME'), joining it with the relative binary path to verify presence.

        Args:
            environment_variable_name (str): Name of the environment variable containing the base directory.
            executable_relative_path (Path): Relative path from the environment directory to the binary.

        Returns:
            Path | None: Absolute path to the resolved executable if verified, otherwise None.
        """
        # Searches in system environment variables.
        executable_env_dir: str | None = os.environ.get(environment_variable_name, None)
        if executable_env_dir:
            # Combines the folder path with the executable path.
            executable_path = Path(executable_env_dir) / executable_relative_path
            if executable_path.is_file():
                return executable_path

        return None

    #* ======= Iverilog Executable Locater =======
    def locate_iverilog_executable(self) -> Path:
        """
        Performs a multi-tier search to locate the Icarus Verilog ('iverilog') executable binary.

        The search hierarchy evaluates:
        1. System 'PATH' environment variable via shell lookup.
        2. The 'IVERILOG_HOME' environment variable.
        3. Standard platform installation directories (Windows and Linux).
        4. Optional hardcoded fallback configuration.

        Raises:
            FileNotFoundError: If the 'iverilog' executable cannot be resolved across any
                of the search tiers, with troubleshooting advice for Windows, Linux, and macOS.

        Returns:
            Path: Absolute filesystem path to the located 'iverilog' executable.
        """
        # ------- Layer-Wise Search of Iverilog Executable. -------
        # Finds out the binary name from the OS.
        relative_path: Path = self._get_binary_name(
            windows_binary_name = "bin/iverilog.exe",
            linux_binary_name = "bin/iverilog"
        )

        # Defines common installation paths.
        common_installation_dirs: list[Path] = [
            # Windows.
            Path("C:/iverilog"),
            Path("C:/Program Files/iverilog"),

            # Linux.
            Path("/usr"),
            Path("/usr/local"),
            Path("/opt/iverilog")  
        ]

        # List of all search functions, executed one-by-one in strict priority order.
        search_operations: list[Callable[[], Path | None]] = [ #TODO AC
            lambda: self._search_in_system_path(system_cmds = "iverilog"),
            lambda: self._search_in_system_environment(
                environment_variable_name = "IVERILOG_HOME",
                executable_relative_path = relative_path
            ),
            lambda: self._search_in_common_installation_directories(
                executable_common_installation_directories = common_installation_dirs,
                executable_relative_path = relative_path
            ),
            lambda: self._check_hardcoded_path(hardcoded_executable_path = self._cfg.hardcoded_iverilog_path)
        ]

        for search_operation in search_operations:
            path: Path | None = search_operation()
            if path is not None:
                return path

        # IF none of the paths are valid, than raises an error.
        fallback_info = f"'{self._cfg.hardcoded_iverilog_path}'" if self._cfg.hardcoded_iverilog_path else "None provided"

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
            f"     - {[str(p) for p in common_installation_dirs]}\n"
            f"  4. User fallback path: {fallback_info}\n\n"
            "Recommendations:\n"
            "  - Windows: Run 'winget install -e --id Icarus.Verilog'\n"
            "  - Linux (Ubuntu/Debian): Run 'sudo apt-get install iverilog'\n"
            "  - macOS: Run 'brew install icarus-verilog'\n"
            "  - Or set the 'IVERILOG_HOME' environment variable to your installation directory.\n"
            "================================================================================"
        )

    #* ======= Verilator Executable Location =======
    def locate_verilator_executable(self) -> Path:
        """
        Performs a multi-tier search to locate the Verilator ('verilator') executable binary.

        The search hierarchy evaluates:
        1. System 'PATH' environment variable via shell lookup ('verilator_bin' and 'verilator').
        2. The 'VERILATOR_ROOT' environment variable.
        3. Standard platform installation directories (Windows, Linux, OSS CAD Suite).
        4. Optional hardcoded fallback configuration.

        Raises:
            FileNotFoundError: If the 'verilator' executable cannot be resolved across any
                of the search tiers, with troubleshooting advice for Windows, Linux, and macOS.

        Returns:
            Path: Absolute filesystem path to the located 'verilator' executable.
        """
        # ------- Layer-Wise Search of Verilator Executable. -------
        # Finds out the binary name from the OS.
        relative_path: Path = self._get_binary_name(
            windows_binary_name = "bin/verilator_bin.exe",
            linux_binary_name = "bin/verilator"
        )
        
        # Defines common installation paths.
        common_installation_dirs: list[Path] = [
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
        
        # List of all search functions, executed one-by-one in strict priority order.
        search_operations: list[Callable[[], Path | None]] = [
            lambda: self._search_in_system_path(system_cmds = ("verilator_bin", "verilator")),
            lambda: self._search_in_system_environment(
                environment_variable_name = "VERILATOR_ROOT",
                executable_relative_path = relative_path
            ),
            lambda: self._search_in_common_installation_directories(
                executable_common_installation_directories = common_installation_dirs,
                executable_relative_path = relative_path
            ),
            lambda: self._check_hardcoded_path(hardcoded_executable_path = self._cfg.hardcoded_verilator_path)
        ]
        
        for search_operation in search_operations:
            path: Path | None = search_operation()
            if path is not None:
                return path

        # IF none of the paths are valid, than raises an error.
        fallback_info = f"'{self._cfg.hardcoded_verilator_path}'" if self._cfg.hardcoded_verilator_path else "None provided"

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
            f"     - {[str(p) for p in common_installation_dirs]}\n"
            f"  4. User fallback path: {fallback_info}\n\n"
            "Recommendations:\n"
            "  - Windows: Run 'choco install verilator' or 'scoop install verilator'\n"
            "  - Linux (Ubuntu/Debian): Run 'sudo apt-get install verilator'\n"
            "  - macOS: Run 'brew install verilator'\n"
            "  - Or set the 'VERILATOR_ROOT' environment variable to your installation directory.\n"
            "================================================================================"
        )

    #* ======= Vivado Executable Location =======
    def locate_vivado_executable(self) -> Path:
        """
        Performs a multi-tier search to locate the Vivado ('vivado') executable binary.

        The search hierarchy evaluates:
        1. System 'PATH' environment variable via shell lookup ('vivado').
        2. The 'XILINX_VIVADO' environment variable.
        3. Standard platform installation directories (Windows, Linux, OSS CAD Suite).
        4. Optional hardcoded fallback configuration.

        Raises:
            FileNotFoundError: If the 'vivado' executable cannot be resolved across any
                of the search tiers, with troubleshooting advice for Windows, Linux, and macOS.

        Returns:
            Path: Absolute filesystem path to the located 'vivado' executable.
        """
        # ------- Layer-Wise Search of Verilator Executable. -------
        # Finds out the binary name from the OS.
        relative_path: Path = self._get_binary_name(
            windows_binary_name = "bin/vivado.bat",
            linux_binary_name = "bin/vivado"
        )

        # Defines common installation paths.
        common_installation_dirs: list[Path] = [
            # Windows.
            Path("C:/Xilinx/Vivado"),
            Path("C:/Vivado"),

            # Linux.
            Path("/opt/Xilinx/Vivado"),
            Path("/tools/Xilinx/Vivado") 
        ]

        # List of all search functions, executed one-by-one in strict priority order.
        search_operations: list[Callable[[], Path | None]] = [
            lambda: self._search_in_system_path(system_cmds = "vivado"),
            lambda: self._search_in_system_environment(
                environment_variable_name = "XILINX_VIVADO",
                executable_relative_path = relative_path
            ),
            lambda: self._search_in_common_installation_directories(
                executable_common_installation_directories = common_installation_dirs,
                executable_relative_path = relative_path
            ),
            lambda: self._check_hardcoded_path(hardcoded_executable_path = self._cfg.hardcoded_verilator_path)
        ]

        for search_operation in search_operations:
            path: Path | None = search_operation()
            if path is not None:
                return path

        # IF none of the paths are valid, than raises an error.
        fallback_info = f"'{self._cfg.hardcoded_verilator_path}'" if self._cfg.hardcoded_verilator_path else "None provided"

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
            f"     - {[str(p) for p in common_installation_dirs]}\n"
            f"  4. User fallback path: {fallback_info}\n\n"
            "Recommendations:\n"
            "  - Windows: Run 'choco install verilator' or 'scoop install verilator'\n"
            "  - Linux (Ubuntu/Debian): Run 'sudo apt-get install verilator'\n"
            "  - macOS: Run 'brew install verilator'\n"
            "  - Or set the 'VERILATOR_ROOT' environment variable to your installation directory.\n"
            "================================================================================"
        )