import os
import math
from pick import pick
from colorama import init, Fore, Style
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

# Initialize colorama for Windows color support
init()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    clear_screen()
    print(f"{Fore.CYAN}╔══════════════════════════════════╗")
    print(f"║         COMBO EDITOR           ║")
    print(f"╚══════════════════════════════════╝{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Creator: JemPH{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'=' * 30}{Style.RESET_ALL}")

def get_combo_file():
    """Get the combo file path from user input."""
    while True:
        file_path = input(f"\n{Fore.CYAN}Enter path to combo file: {Style.RESET_ALL}").strip()
        if os.path.exists(file_path):
            return file_path
        print(f"{Fore.RED}File not found. Please try again.{Style.RESET_ALL}")

def ensure_results_dir():
    """Create results directory if it doesn't exist."""
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_dir, exist_ok=True)
    return results_dir

def get_thread_count():
    """Get the number of threads to use from user input."""
    while True:
        try:
            thread_count = input(f"\n{Fore.CYAN}Enter number of threads (1-32, default: 4): {Style.RESET_ALL}").strip()
            if not thread_count:
                return 4
            thread_count = int(thread_count)
            if 1 <= thread_count <= 32:
                return thread_count
            print(f"{Fore.RED}Please enter a number between 1 and 32.{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")

def process_file_chunk(lines, process_func):
    """Process a chunk of lines with the given function."""
    return [process_func(line) for line in lines if line.strip()]

def process_with_threads(file_path, process_func, thread_count=4):
    """Process a file using multiple threads."""
    try:
        # Read all lines
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Remove empty lines and whitespace
        lines = [line.strip() for line in lines if line.strip()]
        
        if not lines:
            print(f"{Fore.RED}No lines to process in the file.{Style.RESET_ALL}")
            return []

        # Calculate chunk size
        chunk_size = max(1, len(lines) // thread_count)
        chunks = [lines[i:i + chunk_size] for i in range(0, len(lines), chunk_size)]

        processed_lines = []
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            # Submit chunks for processing
            future_to_chunk = {
                executor.submit(process_file_chunk, chunk, process_func): chunk 
                for chunk in chunks
            }

            # Collect results
            for future in as_completed(future_to_chunk):
                try:
                    result = future.result()
                    processed_lines.extend(result)
                except Exception as e:
                    print(f"{Fore.RED}Error processing chunk: {str(e)}{Style.RESET_ALL}")

        return processed_lines

    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
        return []

def remove_duplicates(file_path):
    """Remove duplicate lines from the combo file."""
    try:
        thread_count = get_thread_count()
        
        def process_line(line):
            return line.strip()
        
        lines = process_with_threads(file_path, process_line, thread_count)
        
        # Remove duplicates while preserving order
        unique_lines = list(dict.fromkeys(lines))
        
        # Save to new file in results directory
        results_dir = ensure_results_dir()
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = os.path.join(results_dir, f"{base_name}_no_dupes.txt")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(unique_lines))
        
        print(f"\n{Fore.GREEN}Successfully removed duplicates:{Style.RESET_ALL}")
        print(f"Original count: {len(lines)}")
        print(f"New count: {len(unique_lines)}")
        print(f"Removed: {len(lines) - len(unique_lines)} duplicates")
        print(f"Saved to: {output_file}")
        
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def fix_password_format(file_path):
    """Check and fix password format in combo file."""
    try:
        thread_count = get_thread_count()
        
        def process_line(line):
            if not line or ':' not in line:
                return None
                
            email, password = line.split(':', 1)
            
            # Only allow letters and numbers
            allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
            
            # Check if password contains only allowed characters
            if all(c in allowed_chars for c in password):
                # Check if password meets length requirement
                if len(password) >= 6:
                    # Check if password needs uppercase
                    if not any(c.isupper() for c in password):
                        # Capitalize first letter that can be capitalized
                        for i, char in enumerate(password):
                            if char.isalpha():
                                password = password[:i] + char.upper() + password[i+1:]
                                break
                    return f"{email}:{password}"
            return None
        
        processed_lines = process_with_threads(file_path, process_line, thread_count)
        valid_lines = [line for line in processed_lines if line is not None]
        
        # Save processed combos
        results_dir = ensure_results_dir()
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = os.path.join(results_dir, f"{base_name}_fixed.txt")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(valid_lines))
        
        print(f"\n{Fore.GREEN}Successfully processed combos:{Style.RESET_ALL}")
        print(f"Original count: {len(processed_lines)}")
        print(f"Valid combos: {len(valid_lines)}")
        print(f"Invalid/Skipped: {len(processed_lines) - len(valid_lines)}")
        print(f"Saved to: {output_file}")
        
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def split_combo_file(file_path):
    """Split combo file into smaller files."""
    try:
        thread_count = get_thread_count()
        
        def process_line(line):
            return line.strip()
        
        lines = process_with_threads(file_path, process_line, thread_count)
        
        if not lines:
            return
            
        while True:
            try:
                lines_per_file = input(f"\n{Fore.CYAN}Enter number of lines per file: {Style.RESET_ALL}")
                lines_per_file = int(lines_per_file)
                if lines_per_file > 0:
                    break
                print(f"{Fore.RED}Please enter a positive number.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")
        
        # Calculate number of files needed
        total_files = math.ceil(len(lines) / lines_per_file)
        
        # Create output directory
        results_dir = ensure_results_dir()
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Split and save files
        for i in range(total_files):
            start_idx = i * lines_per_file
            end_idx = start_idx + lines_per_file
            chunk = lines[start_idx:end_idx]
            
            output_file = os.path.join(results_dir, f"{base_name}_part{i+1}.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(chunk))
        
        print(f"\n{Fore.GREEN}Successfully split file:{Style.RESET_ALL}")
        print(f"Total lines: {len(lines)}")
        print(f"Lines per file: {lines_per_file}")
        print(f"Files created: {total_files}")
        print(f"Files saved in: {results_dir}")
        
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def remove_urls(file_path):
    """Remove URLs and domains from combo lines."""
    try:
        thread_count = get_thread_count()
        
        def process_line(line):
            if not line or ':' not in line:
                return None
            
            # Remove common URL patterns and extra colons
            line = re.sub(r'^https?://|www\.|:\d+/|/.*$', '', line)
            parts = line.split(':')
            if len(parts) >= 2:
                return f"{parts[0]}:{parts[1]}"
            return None
        
        processed_lines = process_with_threads(file_path, process_line, thread_count)
        valid_lines = [line for line in processed_lines if line is not None]
        
        # Save processed combos
        results_dir = ensure_results_dir()
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = os.path.join(results_dir, f"{base_name}_no_urls.txt")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(valid_lines))
        
        print(f"\n{Fore.GREEN}Successfully removed URLs:{Style.RESET_ALL}")
        print(f"Original count: {len(processed_lines)}")
        print(f"Valid combos: {len(valid_lines)}")
        print(f"Invalid/Skipped: {len(processed_lines) - len(valid_lines)}")
        print(f"Saved to: {output_file}")
        
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def compile_combo_files():
    """Compile multiple combo files into a single file."""
    try:
        thread_count = get_thread_count()
        print(f"\n{Fore.CYAN}Select combo files to compile (Enter 'done' when finished):{Style.RESET_ALL}")
        file_paths = []
        while True:
            file_path = input(f"{Fore.CYAN}Enter path to combo file (or 'done'): {Style.RESET_ALL}").strip()
            if file_path.lower() == 'done':
                if not file_paths:
                    print(f"{Fore.RED}No files selected. Operation cancelled.{Style.RESET_ALL}")
                    return
                break
            if os.path.exists(file_path):
                file_paths.append(file_path)
            else:
                print(f"{Fore.RED}File not found. Please try again.{Style.RESET_ALL}")
        
        # Process all files using threads
        all_lines = set()
        for file_path in file_paths:
            def process_line(line):
                return line.strip()
            
            lines = process_with_threads(file_path, process_line, thread_count)
            all_lines.update(lines)
        
        # Save compiled file
        results_dir = ensure_results_dir()
        output_file = os.path.join(results_dir, "compiled_combo.txt")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(all_lines)))
        
        print(f"\n{Fore.GREEN}Successfully compiled files:{Style.RESET_ALL}")
        print(f"Total unique combos: {len(all_lines)}")
        print(f"Saved to: {output_file}")
        
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def main():
    while True:
        print_banner()
        title = f"Choose an option:"
        options = [
            "Remove duplicates",
            "Fix password format",
            "Split combo file",
            "Remove URLs",
            "Compile combo files",
            "Exit"
        ]
        
        option, index = pick(options, title, indicator='>')
        
        if option == "Exit":
            clear_screen()
            print(f"{Fore.GREEN}Thanks for using Combo Editor!{Style.RESET_ALL}")
            break
            
        if option == "Compile combo files":
            compile_combo_files()
        else:
            file_path = get_combo_file()
            
            if option == "Remove duplicates":
                remove_duplicates(file_path)
            elif option == "Fix password format":
                fix_password_format(file_path)
            elif option == "Split combo file":
                split_combo_file(file_path)
            elif option == "Remove URLs":
                remove_urls(file_path)
        
        input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
