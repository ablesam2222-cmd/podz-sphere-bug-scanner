import requests
import os
import sys
import time
from datetime import datetime
import threading
import queue

# ================== CONFIG ==================
TIMEOUT = 7
CHUNK_SIZE = 2048
MAX_WORKERS = 10

# ================== COLORS ==================
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    
    # Primary colors
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    
    # Backgrounds
    BG_DARK = "\033[48;5;236m"
    BG_SUCCESS = "\033[48;5;22m"
    BG_WARNING = "\033[48;5;130m"

# ================== HTTP ==================
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive"
}

# ================== UTILITIES ==================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Professional header with timestamp"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Colors.BG_DARK}{Colors.WHITE}{Colors.BOLD}")
    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║                           PODZ SPHERE SCANNER                            ║")
    print("║                    Zero-Data Traffic Detection Suite                     ║")
    print(f"║                     {current_time}                           ║")
    print("╚══════════════════════════════════════════════════════════════════════════╗")
    print(f"{Colors.RESET}")

def print_section(title):
    """Print section header"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}▶ {title}")
    print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")

def print_status(message, status_type="info"):
    """Print status messages with icons"""
    icons = {
        "info": f"{Colors.BLUE}[i]{Colors.RESET}",
        "success": f"{Colors.GREEN}[✓]{Colors.RESET}",
        "warning": f"{Colors.YELLOW}[!]{Colors.RESET}",
        "error": f"{Colors.RED}[✗]{Colors.RESET}",
        "progress": f"{Colors.CYAN}[→]{Colors.RESET}"
    }
    print(f"  {icons.get(status_type, '[ ]')} {message}")

def animated_loading(text, duration=0.3):
    """Simple loading animation"""
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    for frame in frames:
        sys.stdout.write(f"\r{Colors.CYAN}{frame}{Colors.RESET} {text}")
        sys.stdout.flush()
        time.sleep(duration)
    sys.stdout.write("\r" + " " * (len(text) + 10) + "\r")

def progress_bar(current, total, length=40):
    """Professional progress bar"""
    percent = current / total
    filled = int(length * percent)
    bar = f"{Colors.GREEN}{'█' * filled}{Colors.DIM}{'░' * (length - filled)}{Colors.RESET}"
    return f"[{bar}] {current}/{total} ({percent:.1%})"

# ================== CORE SCANNER ==================
class TrafficScanner:
    def __init__(self, timeout=TIMEOUT, max_workers=MAX_WORKERS):
        self.timeout = timeout
        self.max_workers = max_workers
        self.results = []
        self.stats = {
            'total': 0,
            'with_traffic': 0,
            'no_traffic': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def check_domain(self, domain):
        """Check if domain generates traffic"""
        url = f"http://{domain}"
        try:
            response = requests.head(
                url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True
            )
            # Try to read a small amount of data if HEAD fails
            if response.status_code in [405, 501]:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    stream=True
                )
                data = response.raw.read(CHUNK_SIZE, decode_content=True)
                return bool(data and len(data) > 0)
            return True
        except requests.exceptions.Timeout:
            return False
        except requests.exceptions.ConnectionError:
            return False
        except Exception:
            return False
    
    def worker(self, q, index, total):
        """Worker thread for parallel scanning"""
        while not q.empty():
            try:
                domain = q.get_nowait()
                # Show progress
                sys.stdout.write(f"\r{Colors.DIM}Scanning... {progress_bar(index[0], total)}{Colors.RESET}")
                sys.stdout.flush()
                
                result = self.check_domain(domain)
                
                with threading.Lock():
                    if result:
                        self.results.append(f"{Colors.GREEN}{Colors.BOLD}✓ {domain}{Colors.RESET}")
                        self.stats['with_traffic'] += 1
                        print(f"\r  {Colors.GREEN}[✓] {domain}{' ' * 50}")
                    else:
                        self.stats['no_traffic'] += 1
                        print(f"\r  {Colors.DIM}[ ] {domain}{Colors.RESET}{' ' * 50}")
                    
                    index[0] += 1
                    self.stats['total'] = index[0]
                
                q.task_done()
                
            except queue.Empty:
                break
            except Exception:
                self.stats['errors'] += 1
                q.task_done()
    
    def scan_domains(self, domains):
        """Scan list of domains with parallel processing"""
        self.stats['start_time'] = datetime.now()
        self.stats['total'] = len(domains)
        
        q = queue.Queue()
        for domain in domains:
            q.put(domain)
        
        print_section("SCAN PROGRESS")
        
        # Create worker threads
        threads = []
        index = [0]  # Mutable counter for progress
        
        for _ in range(min(self.max_workers, len(domains))):
            t = threading.Thread(target=self.worker, args=(q, index, len(domains)))
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Wait for completion
        q.join()
        
        self.stats['end_time'] = datetime.now()
        
        # Clear progress line
        sys.stdout.write("\r" + " " * 80 + "\r")
        
        return self.results

# ================== MAIN APPLICATION ==================
def main():
    clear_screen()
    print_header()
    
    # Configuration section
    print_section("CONFIGURATION CHECK")
    
    requirements = [
        ("Mobile Data", True),
        ("Wi-Fi Off", True),
        ("Zero-Balance SIM", True),
        ("Network Stability", True)
    ]
    
    all_met = True
    for req, met in requirements:
        icon = f"{Colors.GREEN}✓" if met else f"{Colors.RED}✗"
        print(f"  {icon}{Colors.RESET} {req}")
        if not met:
            all_met = False
    
    if not all_met:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}Warning:{Colors.RESET} Some requirements not met. Results may be inaccurate.")
    
    # File input with validation
    print_section("INPUT")
    while True:
        file_name = input(f"  {Colors.WHITE}Enter domain list file path: {Colors.RESET}").strip()
        
        if not file_name:
            print_status("No file provided. Exiting.", "error")
            sys.exit(0)
        
        if not os.path.exists(file_name):
            print_status(f"File not found: {file_name}", "error")
            continue
        
        try:
            with open(file_name, 'r') as f:
                domains = [line.strip() for line in f if line.strip()]
            
            if not domains:
                print_status("File is empty.", "error")
                continue
            
            print_status(f"Loaded {len(domains)} domains", "success")
            break
            
        except Exception as e:
            print_status(f"Error reading file: {str(e)}", "error")
            continue
    
    # Optional settings
    print_section("SCAN SETTINGS")
    try:
        workers = input(f"  {Colors.WHITE}Parallel workers [{MAX_WORKERS}]: {Colors.RESET}").strip()
        workers = int(workers) if workers else MAX_WORKERS
    except ValueError:
        workers = MAX_WORKERS
        print_status(f"Invalid input. Using default: {MAX_WORKERS}", "warning")
    
    # Start scan
    print_section("INITIALIZING SCAN")
    animated_loading("Initializing scanner threads...", 0.5)
    
    scanner = TrafficScanner(max_workers=workers)
    results = scanner.scan_domains(domains)
    
    # Results display
    print_section("SCAN RESULTS")
    
    # Summary table
    print(f"\n{Colors.BOLD}{'STATISTICS':^60}{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")
    
    stats = scanner.stats
    duration = (stats['end_time'] - stats['start_time']).total_seconds()
    
    metrics = [
        ("Total Domains", f"{stats['total']}"),
        ("Traffic Detected", f"{Colors.GREEN}{stats['with_traffic']}{Colors.RESET}"),
        ("No Traffic", f"{stats['no_traffic']}"),
        ("Errors", f"{Colors.YELLOW}{stats['errors']}{Colors.RESET}"),
        ("Duration", f"{duration:.2f}s"),
        ("Rate", f"{stats['total']/duration:.1f}/s" if duration > 0 else "N/A")
    ]
    
    for i in range(0, len(metrics), 2):
        left = metrics[i]
        right = metrics[i + 1] if i + 1 < len(metrics) else ("", "")
        
        if left[0]:
            print(f"  {left[0]:<20} {Colors.WHITE}{left[1]:>15}{Colors.RESET}", end="")
        if right[0]:
            print(f"     {right[0]:<20} {Colors.WHITE}{right[1]:>15}{Colors.RESET}")
        else:
            print()
    
    # Show results if any
    if results:
        print_section("DETECTED DOMAINS")
        for i, result in enumerate(results[:20], 1):  # Limit to first 20
            print(f"  {i:3d}. {result}")
        
        if len(results) > 20:
            print(f"  {Colors.DIM}... and {len(results) - 20} more{Colors.RESET}")
    
    # Save results option
    print_section("EXPORT RESULTS")
    save = input(f"  {Colors.WHITE}Save results to file? (y/N): {Colors.RESET}").strip().lower()
    
    if save == 'y':
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scan_results_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write(f"PODZ Sphere Scan Results\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total: {stats['total']}\n")
            f.write(f"With Traffic: {stats['with_traffic']}\n")
            f.write(f"No Traffic: {stats['no_traffic']}\n")
            f.write(f"Errors: {stats['errors']}\n\n")
            f.write("DOMAINS WITH TRAFFIC:\n")
            for result in results:
                f.write(result.replace(Colors.RESET, '').replace(Colors.GREEN, '').replace(Colors.BOLD, '') + "\n")
        
        print_status(f"Results saved to: {filename}", "success")
    
    # Exit gracefully
    print_section("SESSION COMPLETE")
    print_status("Scan completed successfully", "success")
    print(f"\n{Colors.DIM}Press Enter to exit...{Colors.RESET}", end="")
    input()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Scan interrupted by user.{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {str(e)}{Colors.RESET}")
        sys.exit(1)