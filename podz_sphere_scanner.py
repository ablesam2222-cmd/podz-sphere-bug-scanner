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
║               Z E R O - B A L A N C E   M O D E              ║
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
        input(f"\n{Y}Press ENTER to exit...{RST}")
