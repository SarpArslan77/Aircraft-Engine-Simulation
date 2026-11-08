
#* scripts/run_vivado.py

#* ======= Libraries =======
# ------- Natives. -------
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

    hardcoded_vivado_path: Path | None = None

#* ======= Vivado Runner Class =======
class SynthesisRunner:
    def __init__(
        self,
        config_synthesis_runner: ConfigSynthesisRunner
    ) -> None:
        """
        Initializes the SynthesisRunner with synthesis paths and execution configurations.

        Args:
            config_synthesis_runner (ConfigSynthesisRunner): Configuration dataclass holding
                project paths, output directories, script locations, and optional Vivado binary path.

        Returns:
            None
        """
        self._cfg: ConfigSynthesisRunner = config_synthesis_runner

    def _execute_vivado(
            self,
            cmd: list[Any],
            should_update_readme: bool
    ) -> None:
        """
        Executes an AMD/Xilinx Vivado batch process as a managed subprocess.

        Launches Vivado in non-project batch mode within the synthesis build directory,
        capturing stdout and stderr in-memory. Evaluates execution exit codes to detect
        toolchain, Tcl, or licensing failures, raising an exception with full diagnostic
        logs upon non-zero exit statuses.

        Args:
            cmd (list[Any]): Formatted command-line arguments and invocation flags for Vivado.
            should_update_readme (bool): Flag indicating whether the current run represents
                the primary execution logging to console, suppressing completion messages during sweeps.

        Raises:
            RuntimeError: If Vivado exits with a non-zero exit code, appending tool stdout and stderr.

        Returns:
            None
        """
        # Executes Vivado.
        #? cmd: A list of strings representing the command line invocation.
        #? cwd: Current Working Directory (CWD).
        #? capture_checkput: True -> Directs both standard output 'stdout' and standard
        #   error 'stderr' into intermal memory buffers instead of streaming them
        #   live to the active terminal console.
        #? check: Determines what Python should do if the external program fails.
        #   - True: Raises 'subprocess.CalledProcessError' and crashes.
        #   - False: Suppresses automatic crash.
        #? text: True -> Tells Python to decode the raw binary byte streams into strings.
        result: CompletedProcess[str] = subprocess.run( 
            cmd,
            cwd = self._cfg.build_synth_dir_path,
            capture_output = True,
            check = False,
            text = True
        )
        
        # Checks whether any failure happened.
        if result.returncode != 0:
            print()
            print("[VIVADO EXECUTION FAILED]")
            print(result.stdout)
            print(result.stderr)
            raise RuntimeError(f"Vivado failed with exit code {result.returncode}. See output above.")
        
        if not should_update_readme:
            print("Vivado process finished successfully.")

    def _clean_reports(
            self,
            report_file_name: str
        ) -> None:
            """
            Sanitizes sensitive local machine metadata and absolute paths from Vivado reports.
    
            Inspects generated Static Timing Analysis ('timing.rpt') and resource utilization
            ('utilization.rpt') files in-place. Replaces local computer network hostnames,
            operating system build numbers, and user-specific filesystem directory paths with
            generic, anonymized placeholders to prevent information disclosure in public repositories.
    
            Args:
                report_file_name (str): Target report's file name ('utilization.rpt' or 'timing.rpt').
    
            Returns:
                None
            """
            report_file_path: Path = self._cfg.build_synth_dir_path / report_file_name
    
            if report_file_path.is_file():
                report: str = report_file_path.read_text(
                    encoding = "utf-8",
                    errors = "replace"
                )
    
                # Cleans specific patterns in the reports.
                hostname_pattern: str = r"\|\s*Host\s*:.*"
                hostname_cleaned_report: str = re.sub(
                    pattern = hostname_pattern,
                    repl = r"| Host         : [ANONYMIZED_BUILD_HOST]",
                    string = report
                )
    
                local_path_pattern: str = r"\{?[a-zA-Z]:[/\\].*?[/\\]([^}\s\r\n]+\.rpt)\}?"
                local_path_cleaned_report: str = re.sub(
                    pattern = local_path_pattern,
                    repl = r"[PROJECT_ROOT]/build_synth/\1",
                    string = hostname_cleaned_report
                )
    
                report_file_path.write_text(
                    data = local_path_cleaned_report,
                    encoding = "utf-8"
                )

    def _move_stray_files(
            self,
            stray_files: list[str]
    ) -> None:
        """
        Relocates transient scratch files produced by Vivado into the build output directory.

        Monitors the project root directory for stray temporary files dumped during
        synthesis (such as 'clockinfo.txt' and 'dfx_runtime.txt'), unlinking pre-existing
        destinations and moving the files into 'build_synth' to keep the root repository clean.

        Args:
            stray_files (list[str]): List of filenames expected to be generated in the root directory.

        Returns:
            None
        """
        # Moves any stray scratch files dumped by Vivado into 'build_synth'.
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

    def ___parse_lut_metrics(
            self,
            text: str,
            metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Extracts Slice Look-Up Table (LUT) utilization figures from utilization report text.

        Scans the Slice Logic table using regular expressions to capture used and available
        Slice LUT counts. Computes the percentage utilization and updates the metrics dictionary.

        Args:
            text (str): Raw sanitized text content read from 'utilization.rpt'.
            metrics (dict[str, Any]): Dictionary of parsed hardware metrics to be updated in-place.

        Returns:
            dict[str, Any]: The metrics dictionary populated with 'lut_used', 'lut_avail',
                and 'lut_util' values.
        """
        # Regex for Slice LUTs: | Slice LUTs* | <used> | <fixed> | <prohibited> | <available> |.
        lut_metrics: Match[str] | None = re.search( 
            pattern = r"\|\s*Slice LUTs\s*\*?\s*\|\s*(\d+)\s*\|(?:.*?\|){2}\s*(\d+)\s*\|",
            string = text
        )
        if lut_metrics:
            metrics["lut_used"] = int(lut_metrics.group(1))
            metrics["lut_avail"] = int(lut_metrics.group(2))
        
            if metrics["lut_avail"] > 0:
                metrics["lut_util"] = (metrics["lut_used"] / metrics["lut_avail"]) * 100.0

        return metrics

    def ___parse_ff_metrics(
            self,
            text: str,
            metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Extracts Slice Register (Flip-Flop) utilization figures from utilization report text.

        Parses the utilization report using regular expressions targeting either 'Register as Flip Flop'
        or 'Slice Registers' entries. Computes the percentage utilization and updates the metrics dictionary.

        Args:
            text (str): Raw sanitized text content read from 'utilization.rpt'.
            metrics (dict[str, Any]): Dictionary of parsed hardware metrics to be updated in-place.

        Returns:
            dict[str, Any]: The metrics dictionary populated with 'ff_used', 'ff_avail',
                and 'ff_util' values.
        """
        # Regex for Flip Flops: | Slice Registers | <used> | <fixed> | <prohibited> | <available> |.
        ff_match: Match[str] | None = re.search( 
            pattern = r"\|\s*(?:Register as Flip Flop|Slice Registers)\s*\|\s*(\d+)\s*\|(?:.*?\|){2}\s*(\d+)\s*\|",
            string = text
        )
        if ff_match:
            metrics["ff_used"] = int(ff_match.group(1))
            metrics["ff_avail"] = int(ff_match.group(2))
        
            if metrics["ff_avail"] > 0:
                metrics["ff_util"] = (metrics["ff_used"] / metrics["ff_avail"]) * 100.0

        return metrics

    def ___parse_dsp_metrics(
            self,
            text: str,
            metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Extracts DSP48 slice utilization figures from utilization report text.

        Parses the DSP block summary table within the utilization report using regular expressions
        to extract the quantity of utilized and device-available DSP48E1 slices, calculating the
        utilization percentage.

        Args:
            text (str): Raw sanitized text content read from 'utilization.rpt'.
            metrics (dict[str, Any]): Dictionary of parsed hardware metrics to be updated in-place.

        Returns:
            dict[str, Any]: The metrics dictionary populated with 'dsp_used', 'dsp_avail',
                and 'dsp_util' values.
        """
        # Regex for DSP48 slices: | DSPs | <used> | <fixed> | <prohibited> | <available> |.
        dsp_match: Match[str] | None = re.search( 
            pattern = r"\|\s*DSPs?\s*\|\s*(\d+)\s*\|(?:.*?\|){2}\s*(\d+)\s*\|",
            string = text
        )
        if dsp_match:
            metrics["dsp_used"] = int(dsp_match.group(1))
            metrics["dsp_avail"] = int(dsp_match.group(2))
    
            if metrics["dsp_avail"] > 0:
                metrics["dsp_util"] = (metrics["dsp_used"] / metrics["dsp_avail"]) * 100.0

        return metrics

    def __parse_utilization_report(
            self,
            utilization_report_file_path: Path,
            metrics: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Coordinates the sequential extraction of hardware resource utilization metrics from disk.

        Verifies the existence of 'utilization.rpt', extracts the target FPGA silicon part name
        from the report header, and delegates to specialized sub-parsers to populate LUT,
        Flip-Flop, and DSP slice utilization data.

        Args:
            utilization_report_file_path (Path): Absolute filesystem path to 'utilization.rpt'.
            metrics (dict[str, Any]): Base metrics dictionary to populate with utilization values.

        Returns:
            dict[str, Any] | None: Populated metrics dictionary if the file was found and parsed,
                otherwise None.
        """
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
            # Extracts the device name from the header.
            device_name: Match[str] | None = re.search(
                pattern = r"\|\s*Device\s*:\s*(\S+)",
                string = text
            )
            if device_name:
                #? .group(): Capture Groups.
                #       - '0': Returns entire matched pattern.
                #       - '1': Returns whatever was captured inside the first set of parantheses.
                metrics["device"] = device_name.group(1)
        
            # Parses lut metrics.
            lut_updated_metrics: dict[str, Any] = self.___parse_lut_metrics(
                text = text,
                metrics = metrics
            )

            # Parses flip-flops.
            ff_updated_metrics: dict[str, Any] = self.___parse_ff_metrics(
                text = text,
                metrics = lut_updated_metrics
            )

            # Parses dsp-slices.
            dsp_updated_metrics: dict[str, Any] = self.___parse_dsp_metrics(
                text = text,
                metrics = ff_updated_metrics
            )

            return dsp_updated_metrics
        else:
            print(f"Warning: Utilization report not found at '{utilization_report_file_path}'")

            return None

    def ___parse_clk_metrics(
            self,
            text: str,
            metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Parses clock period and frequency constraints from Static Timing Analysis reports.

        Extracts waveform timing parameters from the Clock Summary table within 'timing.rpt'
        using regular expressions, updating the metrics dictionary with the applied target
        clock period constraint and resulting target frequency.

        Args:
            text (str): Raw sanitized text content read from 'timing.rpt'.
            metrics (dict[str, Any]): Dictionary of parsed hardware metrics to be updated.

        Returns:
            dict[str, Any]: The metrics dictionary updated with 'target_period_ns' and
                'target_freq_mhz' values.
        """
        # Targets period and frequency from Clock Summary table.
        clk_match: Match[str] | None = re.search(
            pattern = r"\S+\s+\{[^\}]+\}\s+([\d\.]+)\s+([\d\.]+)",
            string = text
        )
        if clk_match:
            metrics["target_period_ns"] = float(clk_match.group(1))
            metrics["target_freq_mhz"] = float(clk_match.group(2))

        return metrics

    def ___parse_wns_metrics(
            self,
            text: str,
            metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Parses Worst Negative Slack (WNS) and evaluates maximum achievable clock frequency (F_max).

        Searches the Max Delay Paths setup summary table within 'timing.rpt' for the worst
        setup slack value. Computes the maximum achievable frequency (F_max) accounting for
        slack deviation and flags whether timing constraints were met (WNS >= 0.0 ns).

        Args:
            text (str): Raw sanitized text content read from 'timing.rpt'.
            metrics (dict[str, Any]): Dictionary holding timing metrics and target constraints.

        Returns:
            dict[str, Any]: The metrics dictionary populated with 'wns', 'f_max_mhz', and
                'timing_met' status flags.
        """
        #? re.IGNORECASE: Makes the search case-insensitive.
        # Worst Negative Slack (WNS).
        wns_match: Match[str] | None = re.search(
            pattern = r"Setup\s*:\s*\d+\s*Failing Endpoints,\s*Worst Slack\s*([-]?[\d\.]+)ns", 
            string = text, 
            flags = re.IGNORECASE    
        )
        
        if wns_match:
            wns = float(wns_match.group(1))
            metrics["wns"] = wns
            achieved_period_ns = metrics["target_period_ns"] - wns
        
            # Avoids division by zero, if critical path is broken.
            if (achieved_period_ns > 0):
                metrics["f_max_mhz"] = round((1000.0 / achieved_period_ns), 2)
            else:
                metrics["f_max_mhz"] = 0.0
        
            metrics["timing_met"] = (wns >= 0.0)

        return metrics

    def __parse_timing_report(
            self,
            timing_report_file_path: Path,
            metrics: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Coordinates the extraction of Static Timing Analysis (STA) metrics from disk.

        Verifies the existence of 'timing.rpt' and delegates parsing to sub-parsers to extract
        applied clock period constraints, Worst Negative Slack (WNS), maximum achievable frequency,
        and timing closure verification status.

        Args:
            timing_report_file_path (Path): Absolute filesystem path to 'timing.rpt'.
            metrics (dict[str, Any]): Dictionary of parsed hardware metrics to update.

        Returns:
            dict[str, Any] | None: Populated metrics dictionary if the file exists and was parsed,
                otherwise None.
        """
        # Parses Stating Timing Analysis (STA).
        if timing_report_file_path.exists():
            text: str = timing_report_file_path.read_text(
                encoding = "utf-8",
                errors = "replace"
            )
        
            # Parses clock metrics.
            clk_updated_metrics: dict[str, Any] = self.___parse_clk_metrics(
                text = text,
                metrics = metrics
            )

            # Parses 'Worst Negative Slack (WNS)' metrics.
            wns_updated_metrics: dict[str, Any] = self.___parse_wns_metrics(
                text = text,
                metrics = clk_updated_metrics
            )

            return wns_updated_metrics
            
        else:
            print(f"Warning: Timing report not found at '{timing_report_file_path}'")

            return None

    def _parse_reports(
            self,
            target_period_ns: float
    ) -> dict[str, Any]:
        """
        Parses utilization and Static Timing Analysis (STA) reports into a unified metrics dictionary.

        Initializes default hardware resource counters and timing metrics for the specified
        target period constraint, sequentially invoking utilization and timing report parsers
        to compile complete implementation benchmarks.

        Args:
            target_period_ns (float): Target clock constraint period in nanoseconds applied
                during the synthesis run.

        Returns:
            dict[str, Any]: Unified dictionary containing device part name, LUT, FF, and DSP
                slice utilization counts, target and achieved clock frequencies, WNS, and timing status.
        """
        # Initializes the report paths and the metrics dictionary.
        utilization_report_file_path: Path = self._cfg.build_synth_dir_path / "utilization.rpt"
        timing_report_file_path: Path = self._cfg.build_synth_dir_path / "timing.rpt"

        metrics: dict[str, Any] = {
            "device": "Unknown FPGA",

            "lut_used": 0,
            "lut_avail": 0,
            "lut_util": 0.0, 

            "ff_used": 0,
            "ff_avail": 0,
            "ff_util": 0.0, 

            "dsp_used": 0,
            "dsp_avail": 0, 
            "dsp_util": 0.0,

            "target_period_ns": target_period_ns,
            "target_freq_mhz": round((1_000 / target_period_ns), 3),
            "wns": 0.0, 
            "f_max_mhz": 0.0, 
            "timing_met": False    
        }

        # Parses resource utilization.
        utilization_updated_metrics: dict[str, Any] | None = self.__parse_utilization_report(
            utilization_report_file_path = utilization_report_file_path,
            metrics = metrics
        )
        util_metrics: dict[str, Any] = utilization_updated_metrics if utilization_updated_metrics is not None else metrics

        # Parses Stating Timing Analysis (STA).
        timing_updated_metrics: dict[str, Any] | None = self.__parse_timing_report(
            timing_report_file_path = timing_report_file_path,
            metrics = util_metrics
        )
        time_metrics: dict[str, Any] = timing_updated_metrics if timing_updated_metrics is not None else util_metrics

        return time_metrics

    def _update_readme(
        self,
        metrics: dict[str, Any]
    ) -> None:
        """
        Updates the FPGA benchmark table in the repository's README.md with fresh synthesis results.

        Locates the Markdown benchmark block delimited by '<!-- SYNTH_TABLE_START -->' and
        '<!-- SYNTH_TABLE_END -->' tags and replaces it in-place with an updated Markdown table
        reflecting current resource utilization, achieved F_max, and timing closure status.

        Args:
            metrics (dict[str, Any]): Dictionary containing parsed hardware utilization
                and timing performance metrics.

        Returns:
            None
        """
        if not self._cfg.readme_file_path.exists():
            print(f"Warning: '{self._cfg.readme_file_path}' not found. Skipping README update.")
            return

        status_badge: str = "Timing Met" if metrics.get("timing_met", False) else "Timing Failed"

        # Formatted Markdown Table.
        new_table: str = f"""| Metric / Hardware Resource | Used | Available ({metrics.get('device', 'FPGA')}) | Utilization [%] |
| :--- | :--- | :--- | :--- |
| **Slice LUTs (Logic)** | {metrics.get('lut_used', 0):,} | {metrics.get('lut_avail', 0):,} | {metrics.get('lut_util', 0.0):.2f} % |
| **Slice Registers (Flip-Flops)** | {metrics.get('ff_used', 0):,} | {metrics.get('ff_avail', 0):,} | {metrics.get('ff_util', 0.0):.2f} % |
| **DSP48E1 Slices** | {metrics.get('dsp_used', 0):,} | {metrics.get('dsp_avail', 0):,} | {metrics.get('dsp_util', 0.0):.2f} % |
| **Target Clock ($F_{{\\text{{target}}}}$)** | {metrics.get('target_freq_mhz', 100.0):.2f} MHz<br>({metrics.get('target_period_ns', 10.0):.2f}&nbsp;ns) | - | - |
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
        metrics: dict[str, Any],
        should_print_metrics_summary: bool
    ) -> None:
        """
        Prints a formatted terminal summary report of the synthesis utilization and timing results.

        Displays device part number, logic slice utilization percentages, DSP slice count,
        target clock constraint, Worst Negative Slack (WNS), and timing closure status.

        Args:
            metrics (dict[str, Any]): Dictionary containing parsed hardware metrics from Vivado reports.
            should_print_metrics_summary (bool): Flag indicating whether the summary should be displayed.

        Returns:
            None
        """
        if should_print_metrics_summary:
            timing_str = "TIMING CLOSED (PASS)" if metrics.get("timing_met") else "TIMING VIOLATION (FAIL)"
            print()
            print(f" VIVADO OUT-OF-CONTEXT SYNTHESIS & TIMING REPORT  [Device: {metrics.get('device')}]")
            print(f"  - Slice LUTs:          {metrics.get('lut_used', 0):>6}  /  {metrics.get('lut_avail', 0):>6}  ({metrics.get('lut_util', 0.0):>5.2f} %)")
            print(f"  - Flip-Flops:          {metrics.get('ff_used', 0):>6}  /  {metrics.get('ff_avail', 0):>6}  ({metrics.get('ff_util', 0.0):>5.2f} %)")
            print(f"  - DSP48 Slices:        {metrics.get('dsp_used', 0):>6}  /  {metrics.get('dsp_avail', 0):>6}  ({metrics.get('dsp_util', 0.0):>5.2f} %)")
            print(f"  - Target Clock:        {metrics.get('target_freq_mhz', 100.0):.2f} MHz ({metrics.get('target_period_ns', 10.0):.3f} ns)")
            print(f"  - Worst Negative Slack: {metrics.get('wns', 0.0):>+6.3f} ns")
            print(f"  - Achieved Fmax:       {metrics.get('f_max_mhz', 0.0):>6.2f} MHz  -->  {timing_str}")

    def run_synthesis(
        self,
        vivado_path: Path,
        target_period_ns: float,
        should_update_readme: bool
    ) -> float:
        """
        Executes AMD/Xilinx Vivado in batch mode to perform Out-of-Context (OOC) synthesis and implementation.

        The execution workflow:
        1. Resolves the active Vivado executable binary path.
        2. Invokes Vivado in non-project batch mode executing the specified Tcl script with
        the target clock period constraint.
        3. Captures and checks subprocess output, halting execution upon toolchain error.
        4. Moves stray scratch files generated during synthesis into the build directory.
        5. Parses utilization ('utilization.rpt') and timing ('timing.rpt') reports.
        6. Optionally logs a formatted terminal summary and updates 'README.md' benchmark tables.

        Args:
            target_period_ns (float): Target clock period constraint in nanoseconds passed
                as an argument to the Tcl synthesis script.
            should_update_readme (bool): Flag indicating whether to output the console summary
                and update the repository's 'README.md' benchmark table.

        Raises:
            RuntimeError: If Vivado execution fails, encounters syntax/licensing errors,
                or exits with a non-zero exit code.

        Returns:
            float: Worst Negative Slack (WNS) value in nanoseconds extracted from Static Timing Analysis.
        """
        # Runs vivado.
        self._execute_vivado(
            cmd = [
                vivado_path,
                "-mode", "batch",
                "-nojournal",
                "-nolog",
                "-source", str(self._cfg.tcl_script_path),
                "-tclargs", str(target_period_ns),
            ],
            should_update_readme = should_update_readme
        )

        # Clears any local computer hostname and absolute paths from generated reports.
        self._clean_reports(report_file_name = "utilization.rpt")
        self._clean_reports(report_file_name = "timing.rpt")

        # Moves any stray scratch files dumped by Vivado into 'build_synth'.
        stray_files: list[str] = [
            "clockinfo.txt",
            "dfx_runtime.txt"
        ]

        self._move_stray_files(stray_files = stray_files)

        # Parses reports.
        metrics: dict[str, Any] = self._parse_reports(target_period_ns = target_period_ns)

        # Prints terminal summary.
        if should_update_readme:
            self._print_metrics_summary(
                metrics = metrics,
                should_print_metrics_summary = should_update_readme
            )

        # Updates README.md.
        if should_update_readme:
            self._update_readme(metrics = metrics) 

        return float(metrics["wns"])
