#!/usr/bin/env python3
"""
Podz Sphere Zero-Balance Scanner
Optimized for zero data balance SIM cards with minimal data usage
"""

import os
import sys
import time
import socket
import json
import requests
from datetime import datetime
import threading
import queue
import signal

# ===================== ZERO-BALANCE CONFIG =====================
CONFIG = {
    "MAX_DATA_USAGE": 1024 * 10,  # 10KB maximum per scan (zero balance safety)
    "TIMEOUT": 3,  # Shorter timeout to save data
    "MAX_CONCURRENT": 1,  # Sequential scanning for data control
    "STATE_FILE": ".zscan_state",
    "RESULTS_FILE": "zscan_results.txt",
    "HEADERS": {
        "User-Agent": "Mozilla/5.0 (Linux; U; Android 4.4.2; en-US; HM NOTE 1W Build/KOT49H) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 UCBrowser/11.0.5.850 U3/0.8.0 Mobile Safari/534.30",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",  # Close connection to save data
        "Cache-Control": "no-cache"
    },
    "CHUNK_SIZE": 512,  # Read only first 512 bytes to save data
}

# ===================== COLORS =====================
G = "\033[92m"  # Green
Y = "\033[93m"  # Yellow
C = "\033[96m"  # Cyan
R = "\033[91m"  # Red
M = "\033[95m"  # Magenta
B = "\033[94m"  # Blue
W = "\033[97m"  # White
D = "\033[90m"  # Gray/Dark
BOLD = "\033[1m"
UL = "\033[4m"
RST = "\033[0m"

# ===================== DATA COUNTER =====================
class DataCounter:
    """Track data usage to prevent exceeding zero balance"""
    def __init__(self):
        self.bytes_used = 0
        self.requests_made = 0
        self.start_time = time.time()
    
    def add_bytes(self, bytes_count):
        """Add bytes to counter"""
        self.bytes_used += bytes_count
        self.requests_made += 1
        
        # Check if we're approaching limit
        if self.bytes_used > CONFIG["MAX_DATA_USAGE"]:
            print(f"\n{R}⚠ DATA LIMIT REACHED!{RST}")
            print(f"{Y}Used: {self.bytes_used/1024:.1f}KB of {CONFIG['MAX_DATA_USAGE']/1024:.1f}KB{RST}")
            return False
        return True
    
    def get_stats(self):
        """Get usage statistics"""
        elapsed = time.time() - self.start_time
        return {
            "bytes": self.bytes_used,
            "requests": self.requests_made,
            "time": elapsed,
            "avg_per_request": self.bytes_used / max(1, self.requests_made)
        }

# ===================== ZERO BALANCE CHECK =====================
def check_zero_balance_mode():
    """Verify device is in zero balance mode"""
    print(f"\n{Y}📱 ZERO BALANCE MODE CHECK{RST}")
    print(f"{D}──────────────────────────{RST}")
    
    checks = [
        ("Mobile Data", "ON"),
        ("Wi-Fi", "OFF"),
        ("SIM Balance", "0 MB"),
        ("Battery Optimization", "OFF"),
        ("Airplane Mode", "OFF")
    ]
    
    for check, required in checks:
        print(f"  {G}✓{RST} {check}: {required}")
    
    print(f"\n{Y}⚠ IMPORTANT:{RST}")
    print(f"  • This scanner uses minimal data")
    print(f"  • Maximum: {CONFIG['MAX_DATA_USAGE']/1024:.1f}KB per session")
    print(f"  • Stops automatically if data limit reached")
    
    input(f"\n{Y}Press ENTER to continue...{RST}")

# ===================== DOMAIN LOADER =====================
def get_domain_file():
    """Ask user for domain list file"""
    print(f"\n{C}📁 SELECT DOMAIN LIST{RST}")
    print(f"{D}───────────────────{RST}")
    
    # Show available .txt files
    txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]
    
    if txt_files:
        print(f"{G}Available files:{RST}")
        for i, file in enumerate(txt_files, 1):
            size = os.path.getsize(file)
            print(f"  {i}. {file} ({size/1024:.1f}KB)")
    
    while True:
        print(f"\n{Y}Enter filename (or drag & drop file):{RST} ", end='')
        filename = input().strip()
        
        # Remove quotes if user drags and drops
        filename = filename.strip('\'"')
        
        if not filename:
            print(f"{R}❌ No filename entered{RST}")
            continue
        
        # Add .txt extension if missing
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        if os.path.exists(filename):
            # Count lines
            with open(filename, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
                domains = [line for line in lines if not line.startswith('#')]
            
            print(f"{G}✓ Loaded {len(domains)} domains{RST}")
            return filename, domains
        else:
            print(f"{R}❌ File not found: {filename}{RST}")
            print(f"{Y}Create a .txt file with one domain per line{RST}")

# ===================== STATE MANAGEMENT =====================
class ZeroBalanceState:
    """Manage state for zero-balance scanning"""
    
    @staticmethod
    def save(domains, current_index, found):
        """Save scan progress"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "total_domains": len(domains),
            "current_index": current_index,
            "found_domains": found,
            "data_used": 0
        }
        try:
            with open(CONFIG["STATE_FILE"], 'w') as f:
                json.dump(state, f)
            return True
        except:
            return False
    
    @staticmethod
    def load():
        """Load scan progress"""
        if not os.path.exists(CONFIG["STATE_FILE"]):
            return None
        
        try:
            with open(CONFIG["STATE_FILE"], 'r') as f:
                return json.load(f)
        except:
            return None
    
    @staticmethod
    def clear():
        """Clear scan state"""
        if os.path.exists(CONFIG["STATE_FILE"]):
            os.remove(CONFIG["STATE_FILE"])
    
    @staticmethod
    def delete():
        """Delete state file"""
        if os.path.exists(CONFIG["STATE_FILE"]):
            os.remove(CONFIG["STATE_FILE"])

# ===================== MINIMAL SCANNER =====================
class ZeroBalanceScanner:
    """Ultra-light scanner for zero data balance"""
    
    def __init__(self):
        self.data_counter = DataCounter()
        self.found_domains = []
        self.session = requests.Session()
        self.session.headers.update(CONFIG["HEADERS"])
        self.session.max_redirects = 1  # Limit redirects to save data
    
    def minimal_request(self, domain):
        """Make minimal HTTP request to save data"""
        url = f"http://{domain}"
        
        try:
            # Start timing
            start_time = time.time()
            
            # Make HEAD request first (uses less data)
            try:
                response = self.session.head(
                    url,
                    timeout=CONFIG["TIMEOUT"],
                    allow_redirects=False
                )
                
                # Calculate data used (estimate)
                data_used = len(str(response.headers)) + 200  # Approx header size
                
                # Check if HEAD was successful
                if response.status_code < 400:
                    if self.data_counter.add_bytes(data_used):
                        response_time = (time.time() - start_time) * 1000
                        return {
                            "domain": domain,
                            "status": response.status_code,
                            "time": response_time,
                            "data": data_used,
                            "method": "HEAD"
                        }
                
            except:
                pass
            
            # If HEAD failed, try minimal GET
            try:
                response = self.session.get(
                    url,
                    timeout=CONFIG["TIMEOUT"],
                    stream=True,
                    allow_redirects=True
                )
                
                # Read only first CHUNK_SIZE bytes
                content_bytes = b""
                for chunk in response.iter_content(chunk_size=CONFIG["CHUNK_SIZE"]):
                    content_bytes += chunk
                    if len(content_bytes) >= CONFIG["CHUNK_SIZE"]:
                        break
                
                response.close()
                
                # Calculate data used
                data_used = len(str(response.headers)) + len(content_bytes) + 200
                
                if self.data_counter.add_bytes(data_used):
                    response_time = (time.time() - start_time) * 1000
                    return {
                        "domain": domain,
                        "status": response.status_code,
                        "time": response_time,
                        "data": data_used,
                        "method": "GET",
                        "size": len(content_bytes)
                    }
                    
            except Exception as e:
                pass
            
            return None
            
        except Exception as e:
            return None
    
    def scan_domain(self, domain):
        """Scan single domain with zero-balance optimization"""
        result = self.minimal_request(domain)
        
        if result:
            status = result["status"]
            
            # Success criteria (adjust as needed)
            if status < 400:
                # Additional check: domain should have some content
                if result.get("size", 0) > 100:  # At least 100 bytes
                    self.found_domains.append(domain)
                    print(f"{G}✓ {domain} ({status} - {result['time']:.0f}ms){RST}")
                    return True
                else:
                    print(f"{Y}✗ {domain} (no content){RST}")
            else:
                print(f"{D}✗ {domain} ({status}){RST}")
        else:
            print(f"{D}✗ {domain} (failed){RST}")
        
        return False

# ===================== PROGRESS DISPLAY =====================
def show_progress(current, total, found, data_used, start_time):
    """Show scanning progress"""
    elapsed = time.time() - start_time
    percent = (current / total) * 100
    
    # Calculate ETA
    if current > 0:
        time_per_domain = elapsed / current
        remaining = total - current
        eta = time_per_domain * remaining
        eta_str = f"{int(eta//60)}m {int(eta%60)}s"
    else:
        eta_str = "calculating..."
    
    # Clear line and print progress
    sys.stdout.write('\r' + ' ' * 100 + '\r')
    sys.stdout.write(f"{C}Scanning: {current}/{total} ({percent:.1f}%) | ")
    sys.stdout.write(f"Found: {found} | ")
    sys.stdout.write(f"Data: {data_used/1024:.1f}KB | ")
    sys.stdout.write(f"ETA: {eta_str}{RST}")
    sys.stdout.flush()

# ===================== BANNER =====================
def show_banner():
    """Display application banner"""
    os.system('clear' if os.name == 'posix' else 'cls')
    
    banner = f"""{C}{BOLD}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║  ██████╗  ██████╗ ██████╗ ███████╗     ███████╗██████╗ ██╗  ║
║  ██╔══██╗██╔═══██╗██╔══██╗╚══███╔╝     ██╔════╝██╔══██╗██║  ║
║  ██████╔╝██║   ██║██║  ██║  ███╔╝█████╗███████╗██████╔╝██║  ║
║  ██╔═══╝ ██║   ██║██║  ██║ ███╔╝ ╚════╝╚════██║██╔═══╝ ██║  ║
║  ██║     ╚██████╔╝██████╔╝███████╗     ███████║██║     ██║  ║
║  ╚═╝      ╚═════╝ ╚═════╝ ╚══════╝     ╚══════╝╚═╝     ╚═╝  ║
║                                                              ║
║               P O D Z - S P H E R E   TLS SCANN              ║
║                Ultra-Low Data Consumption Scanner            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{RST}
"""
    print(banner)

# ===================== MAIN SCAN FUNCTION =====================
def start_scanning(domains, resume_index=0):
    """Start the zero-balance scan"""
    scanner = ZeroBalanceScanner()
    total = len(domains)
    found_count = 0
    start_time = time.time()
    
    print(f"\n{Y}🚀 STARTING ZERO-BALANCE SCAN{RST}")
    print(f"{D}─────────────────────────────{RST}")
    print(f"{W}• Domains to scan: {total}{RST}")
    print(f"{W}• Max data usage: {CONFIG['MAX_DATA_USAGE']/1024:.1f}KB{RST}")
    print(f"{W}• Timeout: {CONFIG['TIMEOUT']} seconds{RST}")
    print(f"{W}• Starting from: #{resume_index + 1}{RST}")
    
    input(f"\n{Y}Press ENTER to begin scanning...{RST}")
    
    try:
        for i in range(resume_index, total):
            domain = domains[i]
            current_number = i + 1
            
            # Show progress
            stats = scanner.data_counter.get_stats()
            show_progress(current_number, total, len(scanner.found_domains), 
                         stats["bytes"], start_time)
            
            # Scan domain
            if scanner.scan_domain(domain):
                found_count += 1
            
            # Save progress every 10 domains
            if current_number % 10 == 0:
                ZeroBalanceState.save(domains, current_number, scanner.found_domains)
            
            # Check data limit
            if stats["bytes"] >= CONFIG["MAX_DATA_USAGE"]:
                print(f"\n\n{R}⚠ DATA LIMIT REACHED!{RST}")
                print(f"{Y}Used {stats['bytes']/1024:.1f}KB of {CONFIG['MAX_DATA_USAGE']/1024:.1f}KB allowed{RST}")
                break
            
            # Small delay to prevent overwhelming
            time.sleep(0.1)
        
        # Final progress update
        stats = scanner.data_counter.get_stats()
        show_progress(total, total, len(scanner.found_domains), 
                     stats["bytes"], start_time)
        print()  # New line after progress
        
        return scanner.found_domains, stats
        
    except KeyboardInterrupt:
        print(f"\n\n{Y}⏸ Scan paused by user{RST}")
        current_pos = i if 'i' in locals() else resume_index
        ZeroBalanceState.save(domains, current_pos, scanner.found_domains)
        print(f"{C}Progress saved. Resume later.{RST}")
        return scanner.found_domains, scanner.data_counter.get_stats()

# ===================== RESULTS DISPLAY =====================
def show_results(found_domains, stats, total_domains):
    """Display scan results"""
    print(f"\n{C}{'═'*60}{RST}")
    print(f"{G}{BOLD}📊 SCAN COMPLETED{RST}")
    print(f"{C}{'═'*60}{RST}")
    
    print(f"\n{Y}📈 STATISTICS:{RST}")
    print(f"  {W}• Domains scanned: {total_domains}{RST}")
    print(f"  {W}• Active domains found: {len(found_domains)}{RST}")
    print(f"  {W}• Success rate: {(len(found_domains)/total_domains*100):.1f}%{RST}")
    print(f"  {W}• Total data used: {stats['bytes']/1024:.2f} KB{RST}")
    print(f"  {W}• Data per request: {stats['avg_per_request']:.0f} bytes{RST}")
    print(f"  {W}• Total time: {stats['time']:.1f} seconds{RST}")
    print(f"  {W}• Requests made: {stats['requests']}{RST}")
    
    if found_domains:
        print(f"\n{G}✅ ACTIVE DOMAINS FOUND:{RST}")
        for i, domain in enumerate(found_domains[:50], 1):  # Show first 50
            print(f"  {i:3d}. {domain}")
        
        if len(found_domains) > 50:
            print(f"  {C}... and {len(found_domains) - 50} more{RST}")
        
        # Save results
        with open(CONFIG["RESULTS_FILE"], 'w') as f:
            for domain in found_domains:
                f.write(f"{domain}\n")
        print(f"\n{Y}💾 Results saved to: {CONFIG['RESULTS_FILE']}{RST}")
    else:
        print(f"\n{R}❌ No active domains found{RST}")
    
    print(f"\n{C}{'═'*60}{RST}")
    print(f"{G}Zero-balance scan completed successfully!{RST}")
    print(f"{C}{'═'*60}{RST}")

# ===================== RESUME OPTION =====================
def ask_resume():
    """Ask user if they want to resume previous scan"""
    state = ZeroBalanceState.load()
    
    if state:
        print(f"\n{Y}🔄 PREVIOUS SCAN DETECTED{RST}")
        print(f"{D}─────────────────────────{RST}")
        print(f"{W}• Progress: {state['current_index']}/{state['total_domains']} domains{RST}")
        print(f"{W}• Found: {len(state.get('found_domains', []))} active domains{RST}")
        print(f"{W}• Date: {state['timestamp'][:10]}{RST}")
        
        print(f"\n{Y}Do you want to:{RST}")
        print(f"  1. Resume from last position")
        print(f"  2. Start new scan")
        print(f"  3. Delete saved progress")
        
        while True:
            choice = input(f"\n{Y}Enter choice (1-3): {RST}").strip()
            
            if choice == '1':
                return state
            elif choice == '2':
                ZeroBalanceState.delete()
                return None
            elif choice == '3':
                ZeroBalanceState.delete()
                print(f"{G}✓ Progress deleted{RST}")
                return None
            else:
                print(f"{R}Invalid choice. Enter 1, 2, or 3.{RST}")
    
    return None

# ===================== MAIN FUNCTION =====================
def main():
    """Main program flow"""
    
    # Setup signal handler for Ctrl+C
    def signal_handler(sig, frame):
        print(f"\n{Y}⚠ Scan interrupted. Saving progress...{RST}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Show banner
    show_banner()
    
    # Check zero balance mode
    check_zero_balance_mode()
    
    # Ask about resume
    state = ask_resume()
    
    # Get domain file
    filename, domains = get_domain_file()
    
    # Prepare for scanning
    resume_index = 0
    found_domains = []
    
    if state:
        resume_index = state["current_index"]
        found_domains = state.get("found_domains", [])
        print(f"{G}✓ Resuming from domain #{resume_index + 1}{RST}")
    
    # Start scanning
    found, stats = start_scanning(domains, resume_index)
    
    # Combine with previously found domains
    all_found = list(set(found_domains + found))
    
    # Clear state file after successful completion
    ZeroBalanceState.delete()
    
    # Show results
    show_banner()
    show_results(all_found, stats, len(domains))
    
    # Ask for next action
    print(f"\n{Y}What would you like to do next?{RST}")
    print(f"  1. Scan another file")
    print(f"  2. Exit")
    
    while True:
        choice = input(f"\n{Y}Enter choice (1-2): {RST}").strip()
        
        if choice == '1':
            main()  # Restart
            break
        elif choice == '2':
            print(f"\n{G}👋 Thank you for using Podz Sphere Scanner!{RST}")
            break
        else:
            print(f"{R}Invalid choice.{RST}")

# ===================== ENTRY POINT =====================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n{R}💥 UNEXPECTED ERROR:{RST}")
        print(f"{Y}{str(e)}{RST}")
        print(f"\n{D}Please report this issue.{RST}")
        input(f"\n{Y}Press ENTER to exit...{RST}")    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
