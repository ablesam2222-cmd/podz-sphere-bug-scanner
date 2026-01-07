# Podz Sphere Bug Scanner

**Podz Sphere Bug Scanner** is a terminal-based Python utility designed to detect
which domains deliver **real HTTP traffic** when a mobile SIM card has
**0MB data balance**.

The tool is optimized for **Android devices using Termux** and focuses on
accuracy, simplicity, and real-world ISP behavior.

> ⚠️ This tool **is created for teaching Papua New Guineans how to do there own bug host hunting, basically sni hunting**.  
> It only detects domains that are already accessible (zero-rated or whitelisted).

---

## 🚀 Features

- Works with **mobile data ON and zero data balance**
- Designed specifically for **Termux (Android)**
- Uses a fixed **7-second timeout** per domain/added workers to scan multiple domains at a time
- Detects **real payload traffic**, not just connectivity
- Silent scanning — only successful domains are shown
- Clean, professional terminal UI
- Can run with screen OFF (with battery optimization disabled)

---

## 📋 Requirements

### Device & OS
- Android device (Android 8.0+ recommended)

### Software
- **Termux** (installed from **F-Droid**, not Play Store)
- **Python 3**
- **Git** (optional, for cloning the repository)

### Python Dependencies
- `requests`

---

## 🌐 Network Requirements

Before running the scanner:

- 📶 Mobile data **must be ON**
- ❌ Wi-Fi **must be OFF**
- 📴 SIM card balance should be **0MB**
- 🔋 Battery optimization for Termux should be **disabled**

---

## ⚙️ Installation

### 1. Install Termux
Download and install **Termux from F-Droid**.

---

### 2. Update packages and install Python & Git

```bash
pkg update && pkg upgrade -y
pkg install python git -y
```
3. Clone the repository
```bash
git clone https://github.com/ablesam2222-cmd/podz-sphere-bug-scanner.git
cd podz-sphere-bug-scanner
```
4. Install Python dependencies
```bash
pip install -r requirements.txt
```
▶️ Usage
1. Create a domain list
Create a text file with one domain per line:
```bash
nano domains.txt
```
Example content
`
google.com
m.facebook.com
wikipedia.org
vodafone.com.pg
`
Save and exit:
CTRL + O → ENTER → CTRL + X

### Run the scanner

```bash
python podz_sphere_scanner.py
```
 Then enter the domain list name you just made and watch the magic.

Join me on telegram https://t.me/podzsphere
