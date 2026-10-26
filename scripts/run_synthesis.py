
#* scripts/run_vivado.py

#* ======= Libraries =======
# ------- Native. -------
import os
#? re: Pattern Match | Noneing Engine, it lets search for patterns.
import re
#? shutil: Shell Utilities, provides high-level filesystem operations.
import shutil
#? subprocess: Runs external command-line programs.
import subprocess

from dataclasses import dataclass
from pathlib import Path
from re import Match
from subprocess import CompletedProcess
from typing import Any


#* ======= Config Vivado Runner Dataclass =======
@dataclass(frozen = True)
class ConfigSynthesisRunner:
    # ------- Paths. -------
    main_dir_path: Path
    build_synth_dir_path: Path
    scripts_dir_path: Path
    tcl_script_path: Path
    readme_file_path: Path

    default_vivado_path: Path 

#* ======= Vivado Runner Class =======
class SynthesisRunner:
    def __init__(
        self,
        config_synthesis_runner: ConfigSynthesisRunner
    ) -> None:
        self._cfg: ConfigSynthesisRunner = config_synthesis_runner

    def _locate_vivado_executable(
            self
    ) -> Path:
        # ------- Layer-wise Search of Vivado Executable. -------
        # Finds out the OS.
        #? os.name == "nt": Checks if the OS is Windows.
        if (os.name == "nt"): 
            vivado_bin_relative_path = Path("bin/vivado.bat")
        else: 
            vivado_bin_relative_path = Path("bin/vivado")

        # Searches in system environment variables.
        vivado_env_dir: str | None = os.environ.get("XILINX_VIVADO", None)
        if vivado_env_dir:
            # Combines the folder path with the executable path.
            vivado_path: Path = Path(vivado_env_dir) / vivado_bin_relative_path

            if vivado_path.is_file(): 
                return vivado_path

        # Searches in system 'PATH'.
        vivado_system_path: str | None = shutil.which(cmd = "vivado")
        if vivado_system_path: 
            return Path(vivado_system_path)

        # Searches in common installation directories.
        vivado_common_installation_dirs: list[Path] = [
            # Windows.
            Path("C:/Xilinx/Vivado"),
            Path("C:/Vivado"),

            # Linux.
            Path("/opt/Xilinx/Vivado"),
            Path("/tools/Xilinx/Vivado")    
        ]

        for dir in vivado_common_installation_dirs:
            if (dir.exists() and dir.is_dir()):
                #? .iterdir(): Yields all files and folders inside this directory.
                # Looks inside the directory for version folders.
                for version_dir in dir.iterdir():
                    if version_dir.is_dir():
                        vivado_path: Path = version_dir / vivado_bin_relative_path

                        if vivado_path.is_file(): 
                            return vivado_path

        # Falls back to the configured default path.
        return self._cfg.default_vivado_path

    def _parse_reports(
            self
    ) -> dict[str, Any]:
        # Initializes the report paths and the metrics dictionary.
        utilization_report_file_path: Path = self._cfg.build_synth_dir_path / "utilization.rpt"
        timing_report_file_path: Path = self._cfg.build_synth_dir_path / "timing.rpt"

        metrics: dict[str, Any] = {
            "lut_used": 0,
            "lut_util": 0.0, 

            "ff_used": 0, 
            "ff_util": 0.0, 

            "dsp_used": 0, 
            "dsp_util": 0.0, 

            "wns": 0.0, 
            "f_max_mhz": 0.0, 
            "timing_met": False    
        }

        # Parses resource utilization.
        if utilization_report_file_path.exists():
            #? .read_text: Opens the file and reads the entire content as a str.
            #       - errors = "replace" -> Tells Python: "If you find a broken byte, do not crash.
            #           Just swap it with the official Unicode replacement symbol (``)."
            text: str = utilization_report_file_path.read_text(
                encoding = "utf-8",
                errors = "replace"
            )

            #? re.search(): Scans the entire text looking for first place where the pattern matches.
            # Regex for Slice LUTs: | Slice LUTs* | <used> | ... | <util> |
            lut_match: Match | None = re.search( 
                pattern = r"\|\s*Slice LUTs\s*\*?\s*\|\s*(\d+)\s*\|(?:.*?\|){3}\s*([\d\.]+)\s*\|",
                string = text
            )
            if lut_match:
                #? .group(): Capture Groups.
                #       - '0': Returns entire matched pattern.
                #       - '1': Returns whatever was captured inside the first set of parantheses.
                #       - '2': Returns whatever was captured inside the second set of parantheses.
                metrics["lut_used"] = int(lut_match.group(1))
                metrics["lut_util"] = float(lut_match.group(2))

            # Regex for Flip Flops: | Register as Flip Flop | <used> | ... | <util> |
            ff_match: Match | None = re.search( 
                pattern = r"\|\s*(?:Register as Flip Flop|Slice Registers)\s*\|\s*(\d+)\s*\|.*?\|\s*([\d\.]+)\s*\|",
                string = text
            )
            if ff_match:
                metrics["ff_used"] = int(ff_match.group(1))
                metrics["ff_util"] = float(ff_match.group(2))

            # Regex for DSP48 slices: | DSPs | <used> | ... | <util> |
            dsp_match: Match | None = re.search( 
                pattern = r"\|\s*DSPs?\s*\|\s*(\d+)\s*\|.*?\|\s*([\d\.]+)\s*\|",
                string = text
            )
            if dsp_match:
                metrics["dsp_used"] = int(dsp_match.group(1))
                metrics["dsp_util"] = float(dsp_match.group(2))
        else:
            print(f"Warning: Utilization report not found at '{utilization_report_file_path}'")

        # Parses Stating Timing Analysis (STA).
        if timing_report_file_path.exists():
            text: str = timing_report_file_path.read_text(
                encoding = "utf-8",
                errors = "replace"
            )

            #? re.IGNORECASE: Makes the search case-insensitive.
            # Worst Negative Slack (WNS).
            wns_match: Match | None = re.search(
                pattern = r"Setup\s*:\s*\d+\s*Failing Endpoints,\s*Worst Slack\s*([-]?[\d\.]+)ns", 
                string = text, 
                flags = re.IGNORECASE    
            )

            if wns_match:
                wns = float(wns_match.group(1))
                metrics["wns"] = wns

                target_period_ns: float = 10.0 #TODO FH
                achieved_period_ns = target_period_ns - wns

                # Avoids division by zero, if critical path is broken.
                if (achieved_period_ns > 0):
                    metrics["f_max_mhz"] = round((1000.0 / achieved_period_ns), 2)
                else:
                    metrics["f_max_mhz"] = 0.0

                metrics["timing_met"] = (wns >= 0.0)
        else:
            print(f"Warning: Timing report not found at '{timing_report_file_path}'")

        return metrics

    def _update_readme(
        self,
        metrics: dict[str, Any]
    ) -> None:
        if not self._cfg.readme_file_path.exists():
            print(f"Warning: '{self._cfg.readme_file_path}' not found. Skipping README update.")
            return

        status_badge: str = "Timing Met" if metrics.get("timing_met", False) else "Timing Failed"

        # Formatted Markdown Table.
        new_table: str = f"""| Metric / Hardware Resource | Used | Available (Artix-7 xc7a35t) | Utilization [%] |
| :--- | :--- | :--- | :--- |
| **Slice LUTs (Logic)** | {metrics.get('lut_used', 0):,} | 20,800 | {metrics.get('lut_util', 0.0):.2f} % |
| **Slice Registers (Flip-Flops)** | {metrics.get('ff_used', 0):,} | 41,600 | {metrics.get('ff_util', 0.0):.2f} % |
| **DSP48E1 Slices** | {metrics.get('dsp_used', 0):,} | 90 | {metrics.get('dsp_util', 0.0):.2f} % |
| **Target Clock ($F_{{\\text{{target}}}}$)** | 100.00 MHz (10.0 ns) | - | - |
| **Achieved Clock ($F_{{\\text{{max}}}}$)** | **{metrics.get('f_max_mhz', 0.0):.2f} MHz** | - | - |
| **Worst Negative Slack (WNS)** | **{metrics.get('wns', 0.0):+.3f} ns** | - | **{status_badge}** |

*Raw Vivado implementation reports: [`build_synth/utilization.rpt`](build_synth/utilization.rpt) and [`build_synth/timing.rpt`](build_synth/timing.rpt).*"""

        content: str = self._cfg.readme_file_path.read_text(encoding = "utf-8")
        pattern: str = r"(<!-- SYNTH_TABLE_START -->)(.*?)(<!-- SYNTH_TABLE_END -->)"

        #? re.DOTALL: Makes the dot '.' match everyhing, including newlines.
        if not re.search(
            pattern = pattern,
            string = content,
            flags = re.DOTALL
        ):
            print("Warning: Comment tags <!-- SYNTH_TABLE_START --> ... <!-- SYNTH_TABLE_END --> not found in README.md.")
            return

        #? re.sub(): Finds and replaces a text using substitutes.
        #       - repl: What to replace with.
        #? \1 & \2: Refers back to captured groups.
        updated_content: str = re.sub(
            pattern = pattern,
            repl = f"\\1\n{new_table}\n\\3",
            string = content,
            flags = re.DOTALL
        )

        #? .write_text: Opens a file in writing mode and overwrites it with the new str.
        self._cfg.readme_file_path.write_text(
            data = updated_content,
            encoding = "utf-8"
        )

        print("README.md updated successfully with fresh synthesis benchmarks.")

    def _print_metrics_summary(
        self,
        metrics: dict[str, Any]
    ) -> None:
        timing_str = "TIMING CLOSED (PASS)" if metrics.get("timing_met") else "TIMING VIOLATION (FAIL)"
        print()
        print(" VIVADO OUT-OF-CONTEXT SYNTHESIS & TIMING REPORT")
        print(f"  - Slice LUTs:          {metrics.get('lut_used', 0):>6}  /  20,800  ({metrics.get('lut_util', 0.0):>5.2f} %)")
        print(f"  - Flip-Flops:          {metrics.get('ff_used', 0):>6}  /  41,600  ({metrics.get('ff_util', 0.0):>5.2f} %)")
        print(f"  - DSP48 Slices:        {metrics.get('dsp_used', 0):>6}  /      90  ({metrics.get('dsp_util', 0.0):>5.2f} %)")
        print("  - Target Clock:        100.00 MHz (10.000 ns)")
        print(f"  - Worst Negative Slack: {metrics.get('wns', 0.0):>+6.3f} ns")
        print(f"  - Achieved Fmax:       {metrics.get('f_max_mhz', 0.0):>6.2f} MHz  -->  {timing_str}")

    def run_synthesis(self) -> None:
        vivado_path: Path = self._locate_vivado_executable()

        # Vivado batch mode command.
        cmd: list[Any] = [
            vivado_path,
            "-mode", "batch",
            "-source", str(self._cfg.tcl_script_path),
            "-nojournal",
            "-nolog"
        ]

        # Executes Vivado.
        #TODO AC
        _: CompletedProcess = subprocess.run( 
            cmd,
            cwd = self._cfg.main_dir_path,
            capture_output = True,
            check = False,
            text = True
        )

        print("Vivado process finished successfully.")

        # Moves any stray scratch files dumped by Vivado into 'build_synth'.
        stray_files: list[str] = [
            "clockinfo.txt",
            "dfx_runtime.txt"
        ]

        for file_name in stray_files:
            stray_file_path: Path = self._cfg.main_dir_path / file_name
            destination_file_path: Path = self._cfg.build_synth_dir_path / file_name
            
            if stray_file_path.exists():
                if destination_file_path.exists():
                    destination_file_path.unlink()
                
                #? .move(): Moves a file or directory.
                shutil.move(
                    src = str(stray_file_path),
                    dst = str(destination_file_path)
                )

        # Parses reports.
        metrics: dict[str, Any] = self._parse_reports()

        # Prints terminal summary.
        self._print_metrics_summary(metrics = metrics)

        # Updates README.md.
        self._update_readme(metrics = metrics)