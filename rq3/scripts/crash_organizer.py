#!/usr/bin/env python3
"""
Organizes compiler crash data by reading crashes.json files from subdirectories
and grouping them by traceback patterns using proper frame filtering.
Modified to ignore options differences - only traceback is used for grouping.
"""

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional

def is_irrelevant_function(func: str) -> bool:
    """Check if a function is irrelevant for crash identification."""
    irrelevant_functions = {
        "__GI_abort",
        "__assert_fail_base", 
        "__GI___assert_fail",
        "diagnostic_context::action_after_output",
        "diagnostic_context::report_diagnostic",
        "diagnostic_context::diagnostic_impl",
        "diagnostics::context::action_after_output",
        "diagnostics::context::report_diagnostic",
        "diagnostics::context::diagnostic_impl",
        "c_cpp_diagnostic",
        "cpp_error_at",
        "cpp_errno_filename",
        "_cpp_find_file",
        "cpp_read_main_file",
        "c_common_post_options",
        "toplev::main",
        "main",
        "diagnostic_action_after_output",
        "diagnostic_report_diagnostic", 
        "diagnostic_impl",
        "internal_error",
        "fancy_abort",
        "__GI_exit",
        "__libc_start_call_main",
        "__libc_start_main_impl",
        "_start",
        "llvm::sys::Process::Exit(int, bool)",
        "LLVMErrorHandler(void*, char const*, bool)",
        "llvm::report_fatal_error(llvm::Twine const&, bool)",
        "llvm::report_fatal_error(char const*, bool)",
        "llvm::llvm_unreachable_internal(char const*, char const*, unsigned int)",
        "tree_class_check",
        "tree_check",
        "tree_not_check", 
        "tree_ssa_strip_useless_type_conversions",
        "gimplify_expr",
        "c_gimplify_expr",
        "_fatal_insn",
        "_fatal_insn_not_found",
        "llvm::CastInst::Create(llvm::Instruction::CastOps, llvm::Value*, llvm::Type*, llvm::Twine const&, llvm::InsertPosition)",
        "llvm::IRBuilderBase::CreateCast(llvm::Instruction::CastOps, llvm::Value*, llvm::Type*, llvm::Twine const&)",
    }
    return func in irrelevant_functions

def get_identity_frames(traceback: List[str]) -> List[List[Optional[str]]]:
    """
    Extract meaningful identity frames from traceback, filtering out irrelevant functions.
    Returns up to 2 meaningful frames in format [file, function, line].
    """
    identity_frames = []
    
    for tr in traceback:
        if len(identity_frames) >= 2:
            break
            
        if ': ' in tr:
            parts = tr.split(': ')
            if len(parts) >= 3:
                file, func, line = parts[0], parts[1], parts[2]
                file = file.split('/')[-1] if file != '??' else None
                line = line if line != '??' else None
            elif len(parts) >= 2:
                file, func, line = None, parts[1], None
            else:
                file, func, line = None, tr.strip(), None
        else:
            file, func, line = None, tr.strip(), None
        
        # Only add if function is relevant
        if not is_irrelevant_function(func):
            identity_frames.append([file, func, line])
    
    return identity_frames

def normalize_traceback_for_grouping(traceback: List[List[Optional[str]]]) -> tuple:
    """Convert traceback to hashable tuple for grouping."""
    return tuple(tuple(frame) for frame in traceback)

def extract_mutator_and_create_srcfile_entry(srcfile_path: str, timestamp: float) -> Dict[str, Any]:
    """
    Extract mutator from file path and create srcfile entry.
    Expected path format: .../mutator,compiler,id/filename.c
    """
    parts = srcfile_path.split('/')
    if len(parts) >= 2:
        # Look for the part containing mutator,compiler,id
        for part in parts:
            if ',' in part:
                mutator = part.split(',')[0]
                return {
                    "mutator": mutator,
                    "date": timestamp,
                    "file": srcfile_path
                }
    
    # Fallback if pattern not found
    return {
        "mutator": "unknown",
        "date": timestamp,
        "file": srcfile_path
    }

def read_crashes_from_subdirectories(base_path: str = ".") -> List[Dict[str, Any]]:
    """
    Read crashes.json files from all subdirectories.
    """
    all_crashes = []
    base = Path(base_path)
    
    # Find all crashes.json files in subdirectories
    crashes_files = list(base.rglob("crashes.json"))
    
    print(f"Found {len(crashes_files)} crashes.json files")
    
    for crashes_file in crashes_files:
        try:
            with open(crashes_file, 'r') as f:
                crash_data = json.load(f)
                
            # Add the crash data to our list
            if isinstance(crash_data, dict):
                # Single crash object
                all_crashes.append(crash_data)
            elif isinstance(crash_data, list):
                # List of crashes
                all_crashes.extend(crash_data)
            else:
                print(f"Warning: Unexpected data format in {crashes_file}")
                
            print(f"Loaded crash data from {crashes_file}")
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON in {crashes_file}: {e}")
        except Exception as e:
            print(f"Error reading {crashes_file}: {e}")
    
    return all_crashes

def organize_crashes(input_data: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Transform crash data from individual instances to grouped-by-traceback format.
    Uses proper frame filtering to identify meaningful crash patterns.
    Options are ignored - only traceback is used for grouping.
    
    Returns:
        tuple: (valid_organized_crashes, invalid_crashes)
    """
    # Group crashes by (compiler, identity_frames) - options removed
    grouped_crashes = defaultdict(lambda: {
        'compiler': None,
        'options': set(),  # Collect all options used
        'traceback': None,
        'mutators': set(),
        'srcfiles': []
    })
    
    # Track invalid crashes
    invalid_crashes = []
    
    processed_count = 0
    skipped_count = 0
    
    for crash in input_data:
        # Skip if missing required fields
        if 'traceback' not in crash or 'compiler' not in crash:
            invalid_reason = "Missing required fields (traceback or compiler)"
            invalid_crashes.append({
                'crash': crash,
                'reason': invalid_reason,
                'srcfiles': crash.get('srcfiles', [])
            })
            print(f"Warning: {invalid_reason}")
            skipped_count += 1
            continue
            
        # Extract meaningful identity frames from traceback
        identity_frames = get_identity_frames(crash['traceback'])
        
        # Skip if no meaningful frames found
        if len(identity_frames) == 0:
            invalid_reason = "No meaningful frames found in traceback"
            invalid_crashes.append({
                'crash': crash,
                'reason': invalid_reason,
                'original_traceback': crash['traceback'],
                'srcfiles': crash.get('srcfiles', [])
            })
            print(f"Warning: {invalid_reason}")
            skipped_count += 1
            continue
            
        # Create grouping key - only compiler and identity frames, no options
        compiler = crash['compiler']
        
        # Use identity frames for grouping
        identity_key = normalize_traceback_for_grouping(identity_frames)
        key = (compiler, identity_key)  # Removed options from key
        
        group = grouped_crashes[key]
        
        # Set basic info (same for all crashes in group)
        if group['compiler'] is None:
            group['compiler'] = compiler
            group['traceback'] = identity_frames  # Use filtered frames
        
        # Collect all options used (for informational purposes)
        options = crash.get('options', '')
        if options:
            group['options'].add(options)
        
        # Process source files
        srcfiles = crash.get('srcfiles', [])
        for srcfile_info in srcfiles:
            if isinstance(srcfile_info, list) and len(srcfile_info) == 2:
                # Format: [filepath, timestamp]
                filepath, timestamp = srcfile_info
                srcfile_entry = extract_mutator_and_create_srcfile_entry(filepath, timestamp)
                group['mutators'].add(srcfile_entry['mutator'])
                group['srcfiles'].append(srcfile_entry)
            elif isinstance(srcfile_info, str):
                # Handle string format (fallback)
                srcfile_entry = extract_mutator_and_create_srcfile_entry(srcfile_info, 0.0)
                group['mutators'].add(srcfile_entry['mutator'])
                group['srcfiles'].append(srcfile_entry)
            elif isinstance(srcfile_info, dict):
                # Handle dict format (already processed)
                group['mutators'].add(srcfile_info.get('mutator', 'unknown'))
                group['srcfiles'].append(srcfile_info)
        
        processed_count += 1
    
    # Convert to final format
    result = []
    for group_data in grouped_crashes.values():
        result.append({
            'compiler': group_data['compiler'],
            'options': sorted(list(group_data['options'])),  # List of all options used
            'traceback': group_data['traceback'],  # Already in target format
            'mutators': sorted(list(group_data['mutators'])),
            'srcfiles': group_data['srcfiles']
        })
    
    print(f"Processed: {processed_count}, Skipped: {skipped_count}")
    return result, invalid_crashes

def main():
    """Main function to process the crash data."""
    
    # Ask user for base directory or use current directory
    # base_path = input("Enter base directory to search for crashes.json files (press Enter for current directory): ").strip()
    # if not base_path:
    base_path = "."
    
    if not os.path.exists(base_path):
        print(f"Error: Directory {base_path} does not exist")
        return
    
    # Read crashes from all subdirectories
    print(f"Searching for crashes.json files in {base_path}")
    input_data = read_crashes_from_subdirectories(base_path)
    
    if not input_data:
        print("No crash data found!")
        return
    
    print(f"Total crashes loaded: {len(input_data)}")
    
    # Process the data
    organized_data, invalid_crashes = organize_crashes(input_data)
    
    # Write valid crashes output file
    try:
        output_file = f"{base_path}/crashes.json"
        with open(output_file, 'w') as f:
            json.dump(organized_data, f, indent=2)
        print(f"Successfully organized {len(input_data)} crashes into {len(organized_data)} groups")
        print(f"Output written to: {output_file}")
        
        # Write invalid crashes file if any exist
        if invalid_crashes:
            invalid_file = "invalid_crashes.json"
            with open(invalid_file, 'w') as f:
                json.dump(invalid_crashes, f, indent=2)
            print(f"Invalid crashes written to: {invalid_file}")
        
        # Print summary
        print("\nSummary:")
        print(f"- Total crash instances: {len(input_data)}")
        print(f"- Valid unique crash patterns: {len(organized_data)}")
        print(f"- Invalid crashes: {len(invalid_crashes)}")
        
        if invalid_crashes:
            print("\nInvalid crash breakdown:")
            invalid_reasons = defaultdict(int)
            for invalid in invalid_crashes:
                invalid_reasons[invalid['reason']] += 1
            for reason, count in invalid_reasons.items():
                print(f"  - {reason}: {count}")
        
        # Count mutators
        all_mutators = set()
        for group in organized_data:
            all_mutators.update(group['mutators'])
        print(f"- Unique mutators found: {len(all_mutators)} ({', '.join(sorted(all_mutators))})")
        
        # Show some example patterns
        if organized_data:
            print("\nExample valid crash patterns found:")
            for i, group in enumerate(organized_data[:3]):  # Show first 3
                options_used = len(group['options'])
                print(f"  Pattern {i+1}: {len(group['srcfiles'])} crashes with {options_used} different option sets")
                for frame in group['traceback'][:2]:  # Show first 2 frames
                    func = frame[1] if frame[1] else "unknown"
                    print(f"    -> {func}")
                if group['options']:
                    print(f"    Options used: {', '.join(group['options'][:3])}{'...' if len(group['options']) > 3 else ''}")
        
        # Show some example invalid crashes
        if invalid_crashes:
            print(f"\nExample invalid crashes:")
            for i, invalid in enumerate(invalid_crashes[:3]):  # Show first 3
                reason = invalid['reason']
                srcfiles = invalid.get('srcfiles', [])
                srcfile_count = len(srcfiles)
                print(f"  Invalid {i+1}: {reason} ({srcfile_count} srcfiles)")
                if 'original_traceback' in invalid:
                    traceback = invalid['original_traceback']
                    print(f"    Original traceback had {len(traceback)} frames")
                    # Show first few frames to see what was filtered out
                    for j, frame in enumerate(traceback[:3]):
                        print(f"      {j+1}: {frame}")
                    if len(traceback) > 3:
                        print(f"      ... and {len(traceback) - 3} more frames")
        
    except Exception as e:
        print(f"Error writing output file: {e}")

if __name__ == "__main__":
    main()