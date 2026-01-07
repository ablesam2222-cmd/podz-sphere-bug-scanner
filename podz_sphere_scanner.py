import requests
import os
import sys
import time
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

DEFAULT_TIMEOUT = 15
DEFAULT_MAX_WORKERS = 15
DEFAULT_RETRIES = 0
DEFAULT_RETRY_DELAY = 3
CHUNK_SIZE = 2048

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
UNDERLINE = "\033[4m"

GREEN = "\033[92m"
CYAN = "\033[96m"
BLUE = "\033[94m"
WHITE = "\033[97m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"

headers = {
    "User-Agent": "Mozilla/5.0 (Android; Termux)",
    "Accept": "*/*",
    "Connection": "close"
}

def clear_screen():
    os.system("clear")

def print_colored(text, color=WHITE, style=""):
    """Helper function for colored output"""
    style_codes = {
        "bold": BOLD,
        "dim": DIM,
        "underline": UNDERLINE
    }
    style_code = style_codes.get(style, "")
    print(f"{style_code}{color}{text}{RESET}")

def banner():
    """Display the banner"""
    clear_screen()
    print(f"""{BOLD}{CYAN}
 ╔═══════════════════════════════════════════════════════════════╗
 ║+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+║
 ║             PODZ SPHERE BUG HOST ACCURACY SCANNER             ║
 ║+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+║
 ║                                                               ║
 ║               ©©©©©     ©©©©    ©©©©©    ©©©©©©               ║
 ║               ©    ©   ©    ©   ©    ©        ©               ║
 ║               ©    ©   ©    ©   ©    ©       ©                ║
 ║               ©©©©©    ©    ©   ©    ©      ©                 ║
 ║               ©        ©    ©   ©    ©     ©                  ║
 ║               ©        ©    ©   ©    ©   ©                    ║
 ║               ©         ©©©©    ©©©©©    ©©©©©®               ║
 ║                                                               ║
 ║                                                               ║
 ║                         Dev @astp2019                         ║
 ╚═══════════════════════════════════════════════════════════════╝
{RESET}""")

def show_txt_files():
    """Display all txt files in current directory with numbering"""
    txt_files = glob.glob("*.txt")
    
    if not txt_files:
        print_colored("❌ No .txt files found in current directory!", RED)
        print_colored("Please add domain list files to this folder.", YELLOW)
        return None
    
    print_colored(f"\n📁 Available domain files ({len(txt_files)} found):", CYAN, "underline")
    print_colored("─" * 50, DIM)
    
    for i, file in enumerate(txt_files, 1):
        size = os.path.getsize(file)
        try:
            with open(file, 'r') as f:
                lines = sum(1 for _ in f)
            info = f"{lines:,} domains | {size:,} bytes"
        except:
            info = "Error reading file"
        
        print_colored(f"{BOLD}{i:2}. {file}{RESET} {DIM}({info}){RESET}")
    
    print_colored("─" * 50, DIM)
    return txt_files

def get_user_choice(prompt, min_val, max_val, default=None):
    """Get validated user input within range"""
    while True:
        try:
            choice = input(prompt).strip()
            
            if default and choice == "":
                return default
            
            choice = int(choice)
            if min_val <= choice <= max_val:
                return choice
            else:
                print_colored(f"❌ Please enter a number between {min_val} and {max_val}", RED)
        except ValueError:
            print_colored("❌ Please enter a valid number", RED)

def configure_settings():
    """Allow user to configure scanning settings"""
    print_colored("\n⚙️  CONFIGURATION SETTINGS", CYAN, "underline")
    print_colored("─" * 50, DIM)
    
    print_colored("\n1. Threads/Workers", WHITE, "bold")
    print_colored("   Controls how many domains are scanned simultaneously", DIM)
    print_colored(f"   Default: {DEFAULT_MAX_WORKERS}, Recommended: 10-30", DIM)
    max_workers = get_user_choice(f"{BOLD}   Enter max workers [{DEFAULT_MAX_WORKERS}]: {RESET}", 1, 100, DEFAULT_MAX_WORKERS)
    
    print_colored("\n2. Timeout (seconds)", WHITE, "bold")
    print_colored("   How long to wait for server response", DIM)
    print_colored(f"   Default: {DEFAULT_TIMEOUT}, Recommended: 5-30", DIM)
    timeout = get_user_choice(f"{BOLD}   Enter timeout [{DEFAULT_TIMEOUT}]: {RESET}", 1, 60, DEFAULT_TIMEOUT)
    
    print_colored("\n3. Retry Attempts", WHITE, "bold")
    print_colored("   Number of times to retry failed domains", DIM)
    print_colored(f"   Default: {DEFAULT_RETRIES}, Recommended: 0-3", DIM)
    retries = get_user_choice(f"{BOLD}   Enter retries [{DEFAULT_RETRIES}]: {RESET}", 0, 10, DEFAULT_RETRIES)
    
    if retries > 0:
        print_colored("\n4. Retry Delay (seconds)", WHITE, "bold")
        print_colored("   Time to wait between retry attempts", DIM)
        retry_delay = get_user_choice(f"{BOLD}   Enter retry delay [{DEFAULT_RETRY_DELAY}]: {RESET}", 1, 30, DEFAULT_RETRY_DELAY)
    else:
        retry_delay = DEFAULT_RETRY_DELAY
    
    print_colored("\n" + "─" * 50, DIM)
    
    print_colored("\n📋 Configuration Summary:", GREEN)
    print_colored(f"   • Max Workers: {max_workers}", WHITE)
    print_colored(f"   • Timeout: {timeout}s", WHITE)
    print_colored(f"   • Retries: {retries}", WHITE)
    if retries > 0:
        print_colored(f"   • Retry Delay: {retry_delay}s", WHITE)
    
    confirm = input(f"\n{BOLD}Start scan with these settings? (Y/n): {RESET}").strip().lower()
    if confirm in ['n', 'no']:
        return configure_settings()
    
    return max_workers, timeout, retries, retry_delay

def show_requirements():
    """Display requirements notice"""
    print_colored("\n⚠️  IMPORTANT REQUIREMENTS", YELLOW, "underline")
    print_colored("─" * 50, DIM)
    print_colored(f"{BOLD}✓{RESET} Mobile data {GREEN}ON{RESET}")
    print_colored(f"{BOLD}✓{RESET} SIM balance must be {GREEN}0MB{RESET}")
    print_colored(f"{BOLD}✓{RESET} Wi‑Fi {RED}OFF{RESET}")
    print_colored("─" * 50, DIM)
    
    input(f"\n{BOLD}Press Enter to continue...{RESET}")

def try_request(url, timeout):
    """Test if a domain responds with traffic"""
    try:
        r = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            stream=True
        )
        data = r.raw.read(CHUNK_SIZE, decode_content=True)
        return bool(data)
    except:
        return False

def has_traffic(domain, timeout):
    """Check if domain has HTTP/HTTPS traffic"""
    if try_request(f"http://{domain}", timeout):
        return "HTTP"
    if try_request(f"https://{domain}", timeout):
        return "HTTPS"
    return None

def scan(domains, round_no, timeout, max_workers):
    """Scan a list of domains for traffic"""
    hits = []
    misses = []
    total = len(domains)
    scanned = 0
    start = time.time()
    
    est_time = total / (max_workers / (timeout * 0.5))
    
    print_colored(f"\n🚀 Round {round_no}: Scanning {total:,} domains...", BLUE, "bold")
    print_colored(f"   Workers: {max_workers} | Timeout: {timeout}s | Est. time: {est_time:.1f}s", DIM)
    print_colored("─" * 50, DIM)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(has_traffic, d, timeout): d for d in domains}
        
        for future in as_completed(futures):
            domain = futures[future]
            result = future.result()
            scanned += 1
            
            elapsed = time.time() - start
            rate = scanned / elapsed if elapsed > 0 else 0
            remaining = total - scanned
            eta = remaining / rate if rate > 0 else 0
            
            progress = int((scanned / total) * 40)
            bar = f"{BOLD}[{GREEN}{'█' * progress}{WHITE}{'░' * (40 - progress)}{RESET}{BOLD}]{RESET}"
            
            print(
                f"\r{bar} {scanned:4}/{total:4} "
                f"{DIM}[Rate: {rate:.1f}/s | ETA: {eta:.0f}s]{RESET}",
                end=""
            )
            
            if result:
                hits.append(domain)
                print(f"\n{GREEN}  ✓ {domain.ljust(40)} ({result}){RESET}")
            elif scanned == total:
                print() 
    
    print_colored("─" * 50, DIM)
    print_colored(f"✅ Round {round_no} complete: {len(hits):,} hits, {len(misses):,} misses", GREEN)
    
    return hits, misses

def save_results(hits, filename):
    """Save results to file with timestamp"""
    if not hits:
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"results_{timestamp}.txt"
    
    with open(output_file, 'w') as f:
        f.write(f"# PODZ Sphere Scan Results\n")
        f.write(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Source: {filename}\n")
        f.write(f"# Total hits: {len(hits)}\n")
        f.write("#" * 50 + "\n\n")
        
        for domain in sorted(hits):
            f.write(f"{domain}\n")
    
    return output_file

def main():
    banner()
    
    show_requirements()
    
    txt_files = show_txt_files()
    if not txt_files:
        input(f"\n{BOLD}Press Enter to exit...{RESET}")
        sys.exit(0)
    
    file_idx = get_user_choice(
        f"\n{BOLD}Select file number (1-{len(txt_files)}): {RESET}",
        1, len(txt_files)
    ) - 1
    
    selected_file = txt_files[file_idx]
    print_colored(f"\n📄 Selected: {BOLD}{selected_file}{RESET}", GREEN)
    
    try:
        with open(selected_file) as f:
            domains = [d.strip() for d in f if d.strip() and not d.startswith('#')]
        
        if not domains:
            print_colored("❌ File is empty!", RED)
            sys.exit(0)
        
        print_colored(f"📊 Loaded {len(domains):,} domains", GREEN)
        
    except Exception as e:
        print_colored(f"❌ Error reading file: {e}", RED)
        sys.exit(0)
    
    max_workers, timeout, retries, retry_delay = configure_settings()
    
    all_hits = []
    remaining = domains
    
    print_colored("\n" + "═" * 60, CYAN, "bold")
    print_colored("🚀 STARTING SCAN", MAGENTA, "bold")
    print_colored("═" * 60, CYAN, "bold")
    
    for attempt in range(1, retries + 2):
        hits, misses = scan(remaining, attempt, timeout, max_workers)
        all_hits.extend(hits)
        remaining = misses
        
        if not remaining:
            break
        
        if attempt <= retries:
            print_colored(f"\n🔄 Retrying {len(remaining):,} missed domains in {retry_delay}s...", YELLOW)
            time.sleep(retry_delay)
    
    print_colored("\n" + "═" * 60, CYAN, "bold")
    print_colored("📊 FINAL SUMMARY", MAGENTA, "bold")
    print_colored("═" * 60, CYAN, "bold")
    
    print()
    print_colored(f"{BOLD}📈 Statistics:{RESET}")
    print_colored(f"   Total domains scanned: {len(domains):,}", WHITE)
    print_colored(f"   {GREEN}✓ Traffic detected: {len(all_hits):,} ({len(all_hits)/len(domains)*100:.1f}%){RESET}", WHITE)
    print_colored(f"   {RED}✖ No traffic: {len(remaining):,} ({len(remaining)/len(domains)*100:.1f}%){RESET}", WHITE)
    
    if all_hits:
        output_file = save_results(all_hits, selected_file)
        print_colored(f"\n💾 Results saved to: {BOLD}{output_file}{RESET}", GREEN)
    
    print_colored(f"\n{UNDERLINE}📝 Important Notes:{RESET}", YELLOW)
    print_colored("• Detected traffic ≠ guaranteed billing exemption", DIM)
    print_colored("• If no billing, domain may be bugged", DIM)
    print_colored("• Always verify important domains manually", DIM)
    print_colored("• Scanner accuracy depends on network conditions", DIM)
    
    print_colored(f"\n{BOLD}✨ Scan completed successfully!{RESET}", GREEN)
    
    if all_hits and input(f"\n{BOLD}Show detected domains? (y/N): {RESET}").lower() == 'y':
        print_colored("\nDetected domains:", CYAN, "underline")
        for domain in sorted(all_hits)[:50]: 
            print_colored(f"  {domain}", GREEN)
        if len(all_hits) > 50:
            print_colored(f"  ... and {len(all_hits)-50} more", DIM)
    
    input(f"\n{BOLD}Press Enter to exit...{RESET}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\n⏹️  Scan interrupted by user", RED)
        sys.exit(0)
    except Exception as e:
        print_colored(f"\n❌ Unexpected error: {e}", RED)
        sys.exit(1)
