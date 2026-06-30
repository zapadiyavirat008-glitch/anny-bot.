# -*- coding: utf-8 -*-
import os
import socket
import ssl
import threading
import sys
import time
from datetime import datetime
import requests

if len(sys.argv) < 3:
    print("Usage: python cfront_finder.py <hosts.txt> <ips.txt>")
    sys.exit(1)

HOST_FILE = sys.argv[1]
IP_FILE = sys.argv[2]

# TELEGRAM CONFIGURATION (Ab yeh GitHub Secrets se secure folder variable se aayega)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# CloudFront sirf 443 aur 80 support karta hai
PORTS_TO_SCAN = [443]
THREADS = 100

GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"

progress_lock = threading.Lock()
processed_count = 0
total_tasks = 0
hit_count = 0  # Total hits track karne ke liye

def send_telegram_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

def check_target(ip, host, port):
    global processed_count, hit_count
    try:
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(4.0) 
        
        if port == 443:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            secure_sock = context.wrap_socket(raw_sock, server_hostname=host)
            secure_sock.connect((ip, port))
        else:
            raw_sock.connect((ip, port))
            secure_sock = raw_sock
        
        payload = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"User-Agent: Mozilla/5.0 (Linux; Android 10; K)\r\n\r\n"
        )
        
        secure_sock.sendall(payload.encode())
        response1 = secure_sock.recv(1024).decode(errors='ignore')
        
        if "HTTP/1.1 101" in response1:
            time.sleep(0.8)
            try:
                secure_sock.send(b"\r\n")
                response2 = secure_sock.recv(1024).decode(errors='ignore')
                
                if "SSH-" in response2 or "SSH-2.0" in response2:
                    with progress_lock:
                        hit_count += 1
                    current_time = datetime.now().strftime("%H:%M:%S")
                    print("\n" + "="*55)
                    print(f"{GREEN}[✓] CLOUDFRONT TUNNEL HIT FOUND [{current_time}]{RESET}")
                    print(f"    {CYAN}Proxy/Endpoint :{RESET} {ip}:{port}")
                    print(f"    {CYAN}SNI Host       :{RESET} {host}")
                    print("="*55 + "\n")
                    
                    # Telegram notification send karein
                    text = (
                        f"☁️ *CLOUDFRONT TUNNEL HIT FOUND!*\n\n"
                        f"🌐 *Proxy:* `{ip}:{port}`\n"
                        f"🎯 *SNI:* `{host}`\n"
                        f"📋 *Log Response:* `{response2.strip()}`"
                    )
                    send_telegram_message(text)
            except socket.error:
                pass
                
        secure_sock.close()
    except Exception:
        pass
    finally:
        with progress_lock:
            processed_count += 1
            sys.stdout.write(f"\rProgress: [{processed_count}/{total_tasks}] Scanning CloudFront edge...")
            sys.stdout.flush()

def worker(task_list):
    for ip, host, port in task_list:
        check_target(ip, host, port)

# --- MAIN EXECUTION ---
try:
    with open(HOST_FILE, 'r') as f:
        hosts = [h.strip() for f_line in f.readlines() if (h := f_line.strip())]
    with open(IP_FILE, 'r') as f:
        ips = [i.strip() for f_line in f.readlines() if (i := f_line.strip())]
except FileNotFoundError as e:
    print(f"Error: {e}")
    sys.exit(1)

tasks = [(ip, host, port) for ip in ips for host in hosts for port in PORTS_TO_SCAN]
total_tasks = len(tasks)

print(f"Loaded {len(hosts)} Hosts and {len(ips)} IPs.")
print(f"Scanning CloudFront Networks on ports {PORTS_TO_SCAN}. Total tasks: {total_tasks}\n")

# STARTING SCAN MESSAGE
send_telegram_message(f"🚀 *CloudFront Edge Scanner Started!*\n🎯 Total Scanning Tasks: `{total_tasks}`\n⏱️ Time: {datetime.now().strftime('%H:%M:%S')}")

chunk_size = max(1, len(tasks) // THREADS)
threads = []
for i in range(0, len(tasks), chunk_size):
    chunk = tasks[i:i + chunk_size]
    t = threading.Thread(target=worker, args=(chunk,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

# ENDING SCAN MESSAGE WITH SUMMARY
send_telegram_message(f"🏁 *CloudFront Scan Completed!*\n📊 Total Tasks Checked: `{total_tasks}`\n🎯 Total Hits Found: `{hit_count}`")
print("\n\nCloudFront Scan completed.")
