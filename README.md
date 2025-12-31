# Podz Sphere Bug Scanner

**Podz Sphere Bug Scanner** is a terminal-based Python utility designed to detect
which domains deliver **real HTTP traffic** when a mobile SIM card has
**0MB data balance**.

The tool is optimized for **Android devices using Termux** and focuses on
accuracy, simplicity, and real-world ISP behavior.

> ⚠️ This tool **is created for teaching Papua New Guineans hoe to do there own Host hunting**.  
> It only detects domains that are already accessible (zero-rated or whitelisted).

---

## 🚀 Features

- Works with **mobile data ON and zero data balance**
- Designed specifically for **Termux (Android)**
- Uses a fixed **7-second timeout** per domain
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
```bash
git clone https://github.com/ablesam2222-cmd/PodzSphereBugScanner.git
cd PodzSphereBugScanner
```
```bash
pip install -r requirements.txt
```
```bash
