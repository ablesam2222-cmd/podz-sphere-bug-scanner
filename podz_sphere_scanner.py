#!/usr/bin/env python3
"""
Podz Sphere Zero-Rated Host Detector
Detects ALL accessible sites with 0MB balance (including blank/empty pages)
"""

import os
import sys
import time
import json
import socket
from datetime import datetime

# Try to import requests, fallback to urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import ssl

# ===================== CONFIG =====================
CONFIG = {
    "TIMEOUT": 6,
    "MAX_DOWNLOAD": 5120,  # Only 5KB max download for checking
    "STATE_FILE": ".zero_host_state",
    "RESULTS_FILE": "zero_hosts.txt",
    "CATEGORIES_FILE": "host_categories.txt",
    "HEADERS": {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
        "Accept": "*/*",
        "Connection": "close",
        "Cache-Control": "no-cache"
    }
}

# ===================== COLORS =====================
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

# ===================== UTILITIES =====================
def clear_screen():
    os.system('clear')

def show_banner():
    clear_screen()
    banner = f"""{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════╗
║     PODZ SPHERE ZERO-RATED HOST DETECTOR     ║
║    Captures ALL accessible hosts at 0MB      ║
║      @astp2019 on tg                         ║
╚══════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)

# ===================== DOMAIN LOADER =====================
def load_domain_file():
    """Ask user for domain file and load domains"""
    print(f"\n{Colors.CYAN}[*] Available .txt files:{Colors.RESET}")
    
    # List all txt files
    txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]
    
    if not txt_files:
        print(f"{Colors.RED}[!] No .txt files found{Colors.RESET}")
        print(f"{Colors.YELLOW}[*] Create a file with domains (one per line){Colors.RESET}")
        return None, None
    
    for i, file in enumerate(txt_files, 1):
        size = os.path.getsize(file)
        print(f"  {i}. {file} ({size} bytes)")
    
    while True:
        try:
            choice = input(f"\n{Colors.YELLOW}[?] Select file number or enter filename: {Colors.RESET}").strip()
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(txt_files):
                    filename = txt_files[idx]
                else:
                    print(f"{Colors.RED}[!] Invalid number{Colors.RESET}")
                    continue
            else:
                filename = choice
                if not filename.endswith('.txt'):
                    filename += '.txt'
            
            if not os.path.exists(filename):
                print(f"{Colors.RED}[!] File not found: {filename}{Colors.RESET}")
                continue
            
            # Load domains
            with open(filename, 'r') as f:
                domains = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Clean domain
                        domain = line.replace('http://', '').replace('https://', '').split('/')[0]
                        # Remove port if present
                        domain = domain.split(':')[0]
                        domains.append(domain.strip())
            
            print(f"{Colors.GREEN}[✓] Loaded {len(domains)} hosts from {filename}{Colors.RESET}")
            return domains, filename
            
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[!] Cancelled{Colors.RESET}")
            return None, None
        except Exception as e:
            print(f"{Colors.RED}[!] Error: {e}{Colors.RESET}")

# ===================== STATE MANAGER =====================
class StateManager:
    @staticmethod
    def save_state(current_index, accessible_hosts, total_hosts):
        """Save scan progress"""
        state = {
            "current_index": current_index,
            "accessible_hosts": accessible_hosts,
            "total_hosts": total_hosts,
            "timestamp": datetime.now().isoformat()
        }
        try:
            with open(CONFIG["STATE_FILE"], 'w') as f:
                json.dump(state, f, indent=2)
            return True
        except:
            return False
    
    @staticmethod
    def load_state():
        """Load scan progress"""
        if not os.path.exists(CONFIG["STATE_FILE"]):
            return None
        
        try:
            with open(CONFIG["STATE_FILE"], 'r') as f:
                return json.load(f)
        except:
            return None
    
    @staticmethod
    def clear_state():
        """Clear scan state"""
        if os.path.exists(CONFIG["STATE_FILE"]):
            os.remove(CONFIG["STATE_FILE"])

# ===================== HOST DETECTOR ENGINE =====================
class ZeroHostDetector:
    def __init__(self):
        self.accessible_hosts = []  # All hosts that respond
        self.categorized_hosts = {
            "full_sites": [],      # ≥15KB content
            "medium_sites": [],    # 5KB - 15KB
            "small_sites": [],     # 1KB - 5KB
            "empty_sites": [],     # <1KB or blank
            "error_pages": [],     # HTTP errors but responsive
            "port_only": []        # Only ports open, no HTTP
        }
        self.data_used = 0
        self.total_tested = 0
        
    def check_port(self, host, port):
        """Check if port is open (fastest check)"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def test_host_minimal(self, host):
        """Test host with minimal HTTP request"""
        results = {
            "host": host,
            "http_port": False,
            "https_port": False,
            "http_response": None,
            "https_response": None,
            "content_size": 0,
            "status_code": 0,
            "final_url": "",
            "error": None
        }
        
        # Check ports first (very fast, minimal data)
        results["http_port"] = self.check_port(host, 80)
        results["https_port"] = self.check_port(host, 443)
        
        # Try HTTP if port 80 is open
        if results["http_port"]:
            try:
                url = f"http://{host}"
                
                if HAS_REQUESTS:
                    response = requests.head(
                        url,
                        headers=CONFIG["HEADERS"],
                        timeout=CONFIG["TIMEOUT"],
                        allow_redirects=True
                    )
                    results["status_code"] = response.status_code
                    results["final_url"] = str(response.url)
                    self.data_used += 200  # Approx header size
                    
                    # If HEAD successful, try minimal GET
                    if response.status_code < 500:
                        response = requests.get(
                            url,
                            headers=CONFIG["HEADERS"],
                            timeout=CONFIG["TIMEOUT"],
                            stream=True
                        )
                        
                        # Read minimal content
                        content = b""
                        for chunk in response.iter_content(chunk_size=1024):
                            content += chunk
                            if len(content) >= CONFIG["MAX_DOWNLOAD"]:
                                break
                        
                        results["content_size"] = len(content)
                        self.data_used += len(content)
                        response.close()
                        
                else:
                    # Using urllib
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    # Try HEAD first
                    req = urllib.request.Request(url, method='HEAD')
                    for key, value in CONFIG["HEADERS"].items():
                        req.add_header(key, value)
                    
                    try:
                        response = urllib.request.urlopen(req, timeout=CONFIG["TIMEOUT"], context=ctx)
                        results["status_code"] = response.status
                        results["final_url"] = response.url
                        self.data_used += 200
                        
                        # Try minimal GET
                        req_get = urllib.request.Request(url)
                        for key, value in CONFIG["HEADERS"].items():
                            req_get.add_header(key, value)
                        
                        response = urllib.request.urlopen(req_get, timeout=CONFIG["TIMEOUT"], context=ctx)
                        content = response.read(CONFIG["MAX_DOWNLOAD"])
                        results["content_size"] = len(content)
                        self.data_used += len(content)
                        
                    except urllib.error.HTTPError as e:
                        results["status_code"] = e.code
                        results["final_url"] = e.url
                        self.data_used += 200
                        
                        # Read error page content
                        try:
                            content = e.read(1024)
                            results["content_size"] = len(content)
                            self.data_used += len(content)
                        except:
                            pass
                            
            except Exception as e:
                results["error"] = str(e)
        
        self.total_tested += 1
        return results
    
    def categorize_host(self, result):
        """Categorize host based on response"""
        host = result["host"]
        
        # If no ports open and no HTTP response
        if not result["http_port"] and not result["https_port"] and result["status_code"] == 0:
            return "dead"
        
        # Check if it's port-only (no HTTP response but ports open)
        if (result["http_port"] or result["https_port"]) and result["status_code"] == 0:
            self.categorized_hosts["port_only"].append(host)
            return "port_only"
        
        # Check content size for categorization
        size = result["content_size"]
        status = result["status_code"]
        
        if status >= 400 and status < 600:
            # Error pages but server responded
            self.categorized_hosts["error_pages"].append({
                "host": host,
                "status": status,
                "size": size
            })
            return "error_page"
        elif size == 0:
            # Empty response
            self.categorized_hosts["empty_sites"].append(host)
            return "empty"
        elif size < 1024:  # <1KB
            self.categorized_hosts["small_sites"].append({
                "host": host,
                "size": size
            })
            return "small"
        elif size < 5120:  # <5KB
            self.categorized_hosts["medium_sites"].append({
                "host": host,
                "size": size
            })
            return "medium"
        else:  # ≥5KB
            self.categorized_hosts["full_sites"].append({
                "host": host,
                "size": size,
                "status": status
            })
            return "full"
    
    def test_host(self, host):
        """Test a single host and categorize it"""
        result = self.test_host_minimal(host)
        
        category = self.categorize_host(result)
        
        # Add to accessible hosts if not dead
        if category != "dead":
            self.accessible_hosts.append({
                "host": host,
                "category": category,
                "size": result["content_size"],
                "status": result["status_code"],
                "port_80": result["http_port"],
                "port_443": result["https_port"]
            })
            return True, result, category
        
        return False, result, category

# ===================== PROGRESS DISPLAY =====================
def show_progress(current, total, accessible, start_time, data_used):
    """Show scanning progress"""
    elapsed = time.time() - start_time
    percent = (current / total) * 100
    
    sys.stdout.write('\r')
    sys.stdout.write(f"{Colors.CYAN}[*] Progress: {current}/{total} ({percent:.1f}%) | ")
    sys.stdout.write(f"{Colors.GREEN}Accessible: {accessible}{Colors.RESET} | ")
    sys.stdout.write(f"Data: {data_used/1024:.1f}KB | ")
    sys.stdout.write(f"Time: {elapsed:.1f}s{Colors.RESET}")
    sys.stdout.flush()

# ===================== MAIN SCAN FUNCTION =====================
def run_host_detection(hosts):
    """Run host detection scan"""
    detector = ZeroHostDetector()
    total = len(hosts)
    start_time = time.time()
    
    print(f"\n{Colors.YELLOW}[*] Starting host detection on {total} hosts{Colors.RESET}")
    print(f"{Colors.YELLOW}[*] Using {'requests' if HAS_REQUESTS else 'urllib/socket'}{Colors.RESET}")
    print(f"{Colors.YELLOW}[*] Detecting ALL responsive hosts (including blank/empty){Colors.RESET}")
    
    try:
        for i, host in enumerate(hosts, 1):
            # Show progress
            show_progress(i, total, len(detector.accessible_hosts), start_time, detector.data_used)
            
            # Test host
            is_accessible, result, category = detector.test_host(host)
            
            if is_accessible:
                # Show with appropriate color based on category
                if category == "full":
                    print(f"\n{Colors.GREEN}[✓] FULL: {host} ({result['content_size']} bytes){Colors.RESET}")
                elif category == "medium":
                    print(f"\n{Colors.BLUE}[~] MEDIUM: {host} ({result['content_size']} bytes){Colors.RESET}")
                elif category == "small":
                    print(f"\n{Colors.YELLOW}[.] SMALL: {host} ({result['content_size']} bytes){Colors.RESET}")
                elif category == "empty":
                    print(f"\n{Colors.MAGENTA}[0] EMPTY: {host} (empty response){Colors.RESET}")
                elif category == "error_page":
                    print(f"\n{Colors.RED}[E] ERROR: {host} ({result['status_code']}){Colors.RESET}")
                elif category == "port_only":
                    print(f"\n{Colors.CYAN}[P] PORT: {host} (port open){Colors.RESET}")
            else:
                # Dead host
                print(f"\n{Colors.WHITE}[✗] DEAD: {host}{Colors.RESET}")
            
            # Save state every 10 hosts
            if i % 10 == 0:
                accessible_list = [h["host"] for h in detector.accessible_hosts]
                StateManager.save_state(i, accessible_list, total)
            
            # Small delay
            time.sleep(0.05)
        
        # Final progress update
        show_progress(total, total, len(detector.accessible_hosts), start_time, detector.data_used)
        print()  # New line
        
        return detector.accessible_hosts, detector.categorized_hosts, detector.data_used
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[!] Scan interrupted{Colors.RESET}")
        accessible_list = [h["host"] for h in detector.accessible_hosts]
        return accessible_list, detector.categorized_hosts, detector.data_used

# ===================== RESULTS DISPLAY =====================
def show_host_results(accessible_hosts, categorized_hosts, data_used, total_hosts):
    """Display host detection results"""
    print(f"\n{Colors.CYAN}{'═'*70}{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}[*] ZERO-RATED HOST DETECTION COMPLETE{Colors.RESET}")
    print(f"{Colors.CYAN}{'═'*70}{Colors.RESET}")
    
    print(f"\n{Colors.YELLOW}[*] Overall Statistics:{Colors.RESET}")
    print(f"  Total hosts tested: {total_hosts}")
    print(f"  Accessible hosts: {len(accessible_hosts)}")
    print(f"  Data used: {data_used/1024:.1f} KB")
    
    # Show categorized counts
    print(f"\n{Colors.CYAN}[*] Host Categories:{Colors.RESET}")
    print(f"  {Colors.GREEN}● Full sites (≥5KB):{Colors.RESET} {len(categorized_hosts['full_sites'])}")
    print(f"  {Colors.BLUE}● Medium sites (1-5KB):{Colors.RESET} {len(categorized_hosts['medium_sites'])}")
    print(f"  {Colors.YELLOW}● Small sites (<1KB):{Colors.RESET} {len(categorized_hosts['small_sites'])}")
    print(f"  {Colors.MAGENTA}● Empty sites:{Colors.RESET} {len(categorized_hosts['empty_sites'])}")
    print(f"  {Colors.RED}● Error pages:{Colors.RESET} {len(categorized_hosts['error_pages'])}")
    print(f"  {Colors.CYAN}● Port only (no HTTP):{Colors.RESET} {len(categorized_hosts['port_only'])}")
    
    # Save all accessible hosts
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_hosts_file = f"all_accessible_hosts_{timestamp}.txt"
    
    with open(all_hosts_file, 'w') as f:
        f.write("# All Accessible Hosts (Zero Balance Test)\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write(f"# Total tested: {total_hosts}\n")
        f.write(f"# Accessible: {len(accessible_hosts)}\n")
        f.write(f"# Data used: {data_used/1024:.1f} KB\n")
        f.write("#" * 60 + "\n\n")
        
        f.write("ALL ACCESSIBLE HOSTS:\n")
        f.write("=" * 60 + "\n")
        for host_info in accessible_hosts:
            host = host_info["host"]
            category = host_info["category"]
            size = host_info.get("size", 0)
            status = host_info.get("status", 0)
            
            f.write(f"{host}")
            if status > 0:
                f.write(f" [HTTP {status}]")
            if size > 0:
                f.write(f" ({size} bytes)")
            f.write(f" - {category.upper()}\n")
    
    print(f"\n{Colors.GREEN}[✓] All accessible hosts saved to: {all_hosts_file}{Colors.RESET}")
    
    # Save categorized hosts
    categories_file = f"host_categories_{timestamp}.txt"
    
    with open(categories_file, 'w') as f:
        f.write("# Host Categories (Zero Balance Test)\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write("#" * 60 + "\n\n")
        
        # Full sites
        if categorized_hosts["full_sites"]:
            f.write("FULL SITES (≥5KB):\n")
            f.write("=" * 60 + "\n")
            for site in categorized_hosts["full_sites"]:
                f.write(f"{site['host']} ({site['size']} bytes)")
                if site.get('status'):
                    f.write(f" [HTTP {site['status']}]")
                f.write("\n")
            f.write("\n")
        
        # Medium sites
        if categorized_hosts["medium_sites"]:
            f.write("MEDIUM SITES (1-5KB):\n")
            f.write("=" * 60 + "\n")
            for site in categorized_hosts["medium_sites"]:
                f.write(f"{site['host']} ({site['size']} bytes)\n")
            f.write("\n")
        
        # Small sites
        if categorized_hosts["small_sites"]:
            f.write("SMALL SITES (<1KB):\n")
            f.write("=" * 60 + "\n")
            for site in categorized_hosts["small_sites"]:
                f.write(f"{site['host']} ({site['size']} bytes)\n")
            f.write("\n")
        
        # Empty sites
        if categorized_hosts["empty_sites"]:
            f.write("EMPTY/BLANK SITES:\n")
            f.write("=" * 60 + "\n")
            for host in categorized_hosts["empty_sites"]:
                f.write(f"{host}\n")
            f.write("\n")
        
        # Error pages
        if categorized_hosts["error_pages"]:
            f.write("ERROR PAGES (but responsive):\n")
            f.write("=" * 60 + "\n")
            for error in categorized_hosts["error_pages"]:
                f.write(f"{error['host']} [HTTP {error['status']}] ({error['size']} bytes)\n")
            f.write("\n")
        
        # Port only
        if categorized_hosts["port_only"]:
            f.write("PORT ONLY (no HTTP response):\n")
            f.write("=" * 60 + "\n")
            for host in categorized_hosts["port_only"]:
                f.write(f"{host}\n")
    
    print(f"{Colors.GREEN}[✓] Categorized hosts saved to: {categories_file}{Colors.RESET}")
    
    # Show sample from each category
    print(f"\n{Colors.CYAN}[*] Sample Hosts:{Colors.RESET}")
    
    # Show 2-3 from each category
    for category_name, color, display_name in [
        ("full_sites", Colors.GREEN, "Full Sites"),
        ("empty_sites", Colors.MAGENTA, "Empty Sites"),
        ("port_only", Colors.CYAN, "Port Only"),
        ("error_pages", Colors.RED, "Error Pages")
    ]:
        hosts = categorized_hosts[category_name]
        if hosts:
            print(f"\n  {color}● {display_name}:{Colors.RESET}")
            if category_name in ["full_sites", "medium_sites", "small_sites", "error_pages"]:
                for item in hosts[:3]:
                    if isinstance(item, dict):
                        host = item["host"]
                        size = item.get("size", 0)
                        status = item.get("status", "")
                        extra = f" ({size} bytes)"
                        if status:
                            extra = f" [HTTP {status}]{extra}"
                        print(f"    • {host}{extra}")
            else:
                for host in hosts[:3]:
                    print(f"    • {host}")
    
    print(f"\n{Colors.YELLOW}[*] Important:{Colors.RESET}")
    print(f"  • ALL listed hosts are accessible with 0MB balance")
    print(f"  • 'Empty sites' = potential zero-rated hosts")
    print(f"  • 'Port only' = servers running but no web service")
    print(f"  • Test manually to verify zero-rated status")
    
    print(f"\n{Colors.CYAN}{'═'*70}{Colors.RESET}")

# ===================== RESUME FUNCTION =====================
def ask_resume():
    """Ask if user wants to resume previous scan"""
    state = StateManager.load_state()
    
    if not state:
        return None, [], 0
    
    print(f"\n{Colors.YELLOW}[!] Previous host scan detected{Colors.RESET}")
    print(f"  Progress: {state['current_index']}/{state['total_hosts']}")
    print(f"  Accessible hosts: {len(state.get('accessible_hosts', []))}")
    
    while True:
        choice = input(f"\n{Colors.YELLOW}[?] Resume? (y/n/delete): {Colors.RESET}").strip().lower()
        
        if choice == 'y':
            return state['total_hosts'], state.get('accessible_hosts', []), state['current_index']
        elif choice == 'n':
            StateManager.clear_state()
            return None, [], 0
        elif choice == 'delete':
            StateManager.clear_state()
            print(f"{Colors.GREEN}[✓] Previous scan deleted{Colors.RESET}")
            return None, [], 0
        else:
            print(f"{Colors.RED}[!] Invalid choice{Colors.RESET}")

# ===================== ZERO BALANCE CHECK =====================
def zero_balance_check():
    """Show zero balance instructions"""
    print(f"\n{Colors.YELLOW}{'═'*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}ZERO-RATED HOST CAPTURE MODE{Colors.RESET}")
    print(f"{Colors.YELLOW}{'═'*60}{Colors.RESET}")
    
    print(f"\n{Colors.RED}{Colors.BOLD}⚠ CRITICAL REQUIREMENTS:{Colors.RESET}")
    print(f"  1. {Colors.RED}Mobile Data: ON{Colors.RESET}")
    print(f"  2. {Colors.RED}Wi-Fi: OFF{Colors.RESET}")
    print(f"  3. {Colors.RED}SIM Balance: MUST BE EXACTLY 0MB{Colors.RESET}")
    print(f"  4. {Colors.RED}Airplane Mode: OFF{Colors.RESET}")
    
    print(f"\n{Colors.CYAN}[*] What this detects:{Colors.RESET}")
    print(f"  • {Colors.GREEN}Full websites{Colors.RESET} (≥5KB)")
    print(f"  • {Colors.BLUE}Small pages{Colors.RESET} (1-5KB)")
    print(f"  • {Colors.MAGENTA}Blank/empty pages{Colors.RESET} (<1KB)")
    print(f"  • {Colors.RED}Error pages{Colors.RESET} (404, 500, etc.)")
    print(f"  • {Colors.CYAN}Port-only hosts{Colors.RESET} (no web service)")
    
    print(f"\n{Colors.GREEN}[*] Why capture everything?{Colors.RESET}")
    print(f"  • Zero-rated hosts can be ANY size")
    print(f"  • Some are intentionally blank/empty")
    print(f"  • Error pages might still be zero-rated")
    print(f"  • Port access might indicate zero-rated services")
    
    print(f"\n{Colors.YELLOW}[!] Data Usage Estimate:{Colors.RESET}")
    print(f"  • Each host: ~5KB max")
    print(f"  • 100 hosts: ~500KB")
    print(f"  • With 0MB balance, only zero-rated will work!")
    
    input(f"\n\n{Colors.YELLOW}[?] Press ENTER if balance is 0MB... {Colors.RESET}")

# ===================== MAIN FUNCTION =====================
def main():
    """Main program"""
    try:
        # Show banner
        show_banner()
        
        # Zero balance check
        zero_balance_check()
        
        # Check if we should resume
        total_from_state, accessible_from_state, start_index = ask_resume()
        
        if total_from_state:
            print(f"{Colors.GREEN}[*] Resuming from position {start_index}{Colors.RESET}")
            print(f"{Colors.YELLOW}[*] Reloading the same host file...{Colors.RESET}")
        
        # Load host file
        hosts, filename = load_domain_file()
        if not hosts:
            print(f"{Colors.RED}[!] No hosts to scan{Colors.RESET}")
            return
        
        # Start scanning
        if start_index > 0 and start_index < len(hosts):
            hosts_to_scan = hosts[start_index:]
        else:
            hosts_to_scan = hosts
            accessible_from_state = []
        
        # Run host detection
        accessible_hosts, categorized_hosts, data_used = run_host_detection(hosts_to_scan)
        
        # Combine results if resuming
        all_accessible = []
        accessible_dict = {h["host"]: h for h in accessible_hosts}
        
        # Add resumed hosts
        for host in accessible_from_state:
            if host not in accessible_dict:
                all_accessible.append({
                    "host": host,
                    "category": "resumed",
                    "size": 0,
                    "status": 0
                })
        
        # Add newly scanned hosts
        all_accessible.extend(accessible_hosts)
        
        # Clear state after successful completion
        StateManager.clear_state()
        
        # Show results
        show_banner()
        show_host_results(all_accessible, categorized_hosts, data_used, len(hosts))
        
        # Ask for next action
        print(f"\n{Colors.YELLOW}[?] What next?{Colors.RESET}")
        print(f"  1. Scan another host list")
        print(f"  2. Exit")
        
        while True:
            choice = input(f"\n{Colors.YELLOW}[?] Choice (1-2): {Colors.RESET}").strip()
            
            if choice == '1':
                main()
                break
            elif choice == '2':
                print(f"\n{Colors.GREEN}[✓] Zero-rated host capture complete!{Colors.RESET}")
                print(f"{Colors.CYAN}[*] Check the saved files for all accessible hosts{Colors.RESET}")
                break
            else:
                print(f"{Colors.RED}[!] Enter 1 or 2{Colors.RESET}")
            
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[!] Program interrupted{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}[!] Error: {e}{Colors.RESET}")

# ===================== ENTRY POINT =====================
if __name__ == "__main__":
    # Run main function
    main()
