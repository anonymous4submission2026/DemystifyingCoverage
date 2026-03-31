#!/usr/bin/env python3

import os
import sys
import time
import json
import argparse
import re
import shlex
from pathlib import Path
from lib.Fuzzer import Fuzzer, FuzzArgs, CompilerTracer  # Import your classes
from lib.CompilerInstance import Testcase
from lib.Compilers import make_compilers
from lib.Muss import *
from lib import Utils
from lib.CrashPattern import *

directory = "./"
os.system(f"mkdir -p {directory}/tmp_dir")
os.environ['TMPDIR'] = f"{directory}/tmp_dir"

class BatchCrashChecker:
    def __init__(self, input_dir, output_dir="./batch_crash_results", timeout=30):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.timeout = timeout
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Stats
        self.total_files = 0
        self.crashes_found = 0
        self.processed_files = 0
        self.failed_files = 0
        
        # Results tracking
        self.results = []
        self.crash_files = []
        
    def find_mutant_files(self):
        """Find all mutant.c files in subdirectories"""
        mutant_files = []
        
        if not self.input_dir.exists():
            print(f"Error: Input directory {self.input_dir} does not exist")
            return []
            
        # Look for mutant.c files in subdirectories
        for subdir in self.input_dir.iterdir():
            if subdir.is_dir():
                # Find all files matching the pattern mutant*.c
                for mutant_file in subdir.glob("mutant*.c"):
                    mutant_files.append(mutant_file)
                    
        return mutant_files
    
    def parse_crash_log(self, log_file):
        """Parse crash.log file to extract file paths"""
        log_path = Path(log_file)
        if not log_path.exists():
            print(f"Error: Log file {log_path} does not exist")
            return []
        
        crash_files = []
        
        # Regular expression to match the log format
        # Format: number: [compiler] Found bug report message in /path/to/file.c
        # pattern = r'^\d+:\s*\[(?:GCC|Clang)\]\s*Found bug report message in\s+(.+\.c)$'
        pattern = r'^\d+(?:\.\d+)?:\s*\[(.*)\]\s*Found bug report message in\s+(.+\.c)$'
        
        try:
            with open(log_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    match = re.match(pattern, line)
                    if match:
                        file_path = match.group(2)
                        crash_files.append(Path(file_path))
                    else:
                        print(f"Warning: Could not parse line {line_num}: {line}")
        
        except Exception as e:
            print(f"Error reading log file {log_path}: {e}")
            return []
        
        # Filter out files that don't exist
        existing_files = []
        for file_path in crash_files:
            # if file_path.exists():
                existing_files.append(file_path)
            # else:
            #     print(f"Warning: File does not exist: {file_path}")
        
        return existing_files
    
    def create_fuzzer(self):
        """Create a minimal fuzzer instance for crash checking"""
        class MinimalFuzzArgs:
            def __init__(self, output_dir, timeout):
                self.wdir = str(output_dir)
                self.timeout = timeout
                self.mutator = Mutator("kitten", "")
                self.cc = make_compilers()[0]
        
        fuzz_args = MinimalFuzzArgs(self.output_dir, self.timeout)
        return Fuzzer(fuzz_args)
    
    def crash_checking(self, fuzzer, testcase):
        for cc in [configs.clang_bin]:
            for opt_str in [""]:
                options = shlex.split(opt_str)
                for cfile in testcase.ifiles:
                    t = Testcase(cfile, wdir=testcase.wdir)
                    cmd = fuzzer.get_cc_cmdline(cc, t, options=options, tolist=False)
                    tracer = CompilerTracer(cmd, fuzzer.fuzz_args.timeout)
                    res, traceback = tracer.traceback()
                    if not res: continue
                    crash_pattern = CrashPattern(cc, options, traceback)
                    fuzzer.crashes.setdefault(crash_pattern,
                        CompilerCrash(crash_pattern))
                    fuzzer.crashes[crash_pattern].add_bugfile(str(t),
                        time.time() - fuzzer.start_time)
                    with open(f"{fuzzer.fuzz_args.wdir}/crashes.json", 'w+') as fp:
                        j = [v.to_json() for v in fuzzer.crashes.values()]
                        fp.write(json.dumps(j, indent=2))

    def check_single_file(self, file_path, fuzzer, source_type="mutant"):
        """Check a single C file for crashes"""
        start_time = time.time()
        result = {
            'file': str(file_path),
            'relative_path': str(file_path.relative_to(self.input_dir)) if source_type == "mutant" else str(file_path),
            'source_type': source_type,
            'has_crash': False,
            'processing_time': 0,
            'error': None
        }
        
        try:
            # Create testcase object
            testcase = Testcase(str(file_path))
            
            # Run crash check
            has_crash = fuzzer.check_crash(testcase)
            self.crash_checking(fuzzer, testcase)
            
            result['has_crash'] = has_crash
            result['processing_time'] = time.time() - start_time
            
            if has_crash:
                self.crashes_found += 1
                self.crash_files.append(str(file_path))
                print(f"  ✓ CRASH FOUND: {file_path.name}")
            else:
                # if source_type == "log":
                #     self.crash_checking(fuzzer, testcase)
                print(f"  ✗ No crash: {file_path.name}")
                
        except Exception as e:
            result['error'] = str(e)
            self.failed_files += 1
            print(f"  ERROR: {file_path.name} - {e}")
        
        self.processed_files += 1
        return result
    
    def process_files(self, files_to_check, source_type="mutant"):
        """Process files sequentially"""
        print(f"Processing {len(files_to_check)} {source_type} files sequentially...")
        print("-" * 50)
        
        # Create single fuzzer instance to reuse
        fuzzer = self.create_fuzzer()
        
        for i, file_path in enumerate(files_to_check, 1):
            if source_type == "mutant":
                display_path = file_path.relative_to(self.input_dir)
            else:
                display_path = file_path
            
            print(f"[{i}/{len(files_to_check)}] Processing {display_path}")
            
            result = self.check_single_file(file_path, fuzzer, source_type)
            self.results.append(result)
            
            # Progress summary every 50 files
            if i % 50 == 0:
                print(f"\n--- Progress Summary ---")
                print(f"Processed: {i}/{len(files_to_check)} ({i/len(files_to_check)*100:.1f}%)")
                print(f"Crashes found: {self.crashes_found}")
                print(f"Failed files: {self.failed_files}")
                print("-" * 50)
            Utils.remove_files(f"{directory}/tmp_dir")
    
    def save_results(self):
        """Save all results to JSON files"""
        # Save detailed results
        results_file = self.output_dir / "crash_check_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Save crash files list
        crash_files_file = self.output_dir / "crash_files.txt"
        with open(crash_files_file, 'w') as f:
            for crash_file in self.crash_files:
                f.write(f"{crash_file}\n")
        
        # Save summary
        summary = {
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'crashes_found': self.crashes_found,
            'failed_files': self.failed_files,
            'crash_rate': f"{self.crashes_found/self.processed_files*100:.2f}%" if self.processed_files > 0 else "0%"
        }
        
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nResults saved to:")
        print(f"  - Detailed results: {results_file}")
        print(f"  - Crash files list: {crash_files_file}")
        print(f"  - Summary: {summary_file}")
    
    def run_mutant_mode(self):
        """Run in mutant.c mode (original functionality)"""
        print(f"Running in MUTANT mode")
        print(f"Input directory: {self.input_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"Timeout: {self.timeout}s")
        print("=" * 50)
        
        # Find all mutant.c files
        mutant_files = self.find_mutant_files()
        self.total_files = len(mutant_files)
        
        if not mutant_files:
            print("No mutant.c files found in subdirectories!")
            return
        
        print(f"Found {len(mutant_files)} mutant.c files\n")
        
        # Process files
        start_time = time.time()
        self.process_files(mutant_files, "mutant")
        total_time = time.time() - start_time
        
        self.print_final_summary(total_time)
        self.save_results()
    
    def run_log_mode(self, log_file):
        """Run in crash.log mode (new functionality)"""
        print(f"Running in LOG mode")
        print(f"Log file: {log_file}")
        print(f"Output directory: {self.output_dir}")
        print(f"Timeout: {self.timeout}s")
        print("=" * 50)
        
        # Parse crash log
        crash_files = self.parse_crash_log(log_file)
        self.total_files = len(crash_files)
        
        if not crash_files:
            print("No valid crash files found in log!")
            return
        
        print(f"Found {len(crash_files)} crash files from log\n")
        
        # Process files
        start_time = time.time()
        self.process_files(crash_files, "log")
        total_time = time.time() - start_time
        
        self.print_final_summary(total_time)
        self.save_results()
    
    def print_final_summary(self, total_time):
        """Print final summary statistics"""
        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        print(f"Total files processed: {self.processed_files}")
        print(f"Crashes found: {self.crashes_found}")
        print(f"Failed files: {self.failed_files}")
        if self.processed_files > 0:
            print(f"Crash rate: {self.crashes_found/self.processed_files*100:.2f}%")
            print(f"Success rate: {(self.processed_files-self.failed_files)/self.processed_files*100:.2f}%")
        print(f"Total processing time: {total_time:.2f}s")
        if self.processed_files > 0:
            print(f"Average time per file: {total_time/self.processed_files:.2f}s")
        
        if self.crash_files:
            print(f"\nCrash files:")
            for crash_file in self.crash_files:
                print(f"  - {Path(crash_file).name}")

def main():
    parser = argparse.ArgumentParser(description='Sequential batch crash checker for C files')
    parser.add_argument('input', help='Input directory (for mutant mode) or crash.log file (for log mode)')
    parser.add_argument('-o', '--output', default='./batch_crash_results', 
                       help='Output directory for results (default: ./batch_crash_results)')
    parser.add_argument('-t', '--timeout', type=int, default=10, 
                       help='Timeout per file in seconds (default: 10)')
    parser.add_argument('--log-mode', action='store_true',
                       help='Process crash.log file instead of looking for mutant.c files')
    
    args = parser.parse_args()
    configs.options = ["-O2"]
    configs.max_frames = 50
    
    # Create batch checker
    if args.log_mode:
        # For log mode, we don't need input_dir, but we'll use output dir as base
        checker = BatchCrashChecker(
            input_dir=Path(args.output).parent,  # Dummy input dir
            output_dir=args.output,
            timeout=args.timeout
        )
        checker.run_log_mode(args.input)
    else:
        # Original mutant mode
        checker = BatchCrashChecker(
            input_dir=args.input,
            output_dir=args.output,
            timeout=args.timeout
        )
        checker.run_mutant_mode()

if __name__ == "__main__":
    main()