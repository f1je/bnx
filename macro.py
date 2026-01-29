
try:
    import fade
    import colorama
    from colorama import Fore
    import time
    import os
    from pynput.mouse import Listener as MouseListener, Button, Controller
    from pynput import keyboard
    import datetime
    import threading
    import win32gui
    import win32process
    import psutil
except:
    os.system('pip install fade colorama pynput pywin32 psutil')
def cls():
    os.system('cls')

colorama.init()
mouse = Controller()
keyboard_controller = keyboard.Controller()

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

# ===================== ROBLOX CHECK =====================
roblox_active = False

def check_roblox_loop():
    global roblox_active
    last = None

    while True:
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            roblox_active = proc.name().lower() == "robloxplayerbeta.exe"
        except:
            roblox_active = False

        if roblox_active != last:
            log(f"Roblox active: {roblox_active}")
            last = roblox_active

        time.sleep(0.1)

threading.Thread(target=check_roblox_loop, daemon=True).start()

# ===================== UI =====================
print(Fore.BLUE + "SOURCE: @FWAKAAZZ // discord.gg/akaazz (python 1st person macro)" + Fore.RESET)

question = input(
    Fore.WHITE +
    "If you want mouse buttons type (mouse)\n"
    "Otherwise type a keyboard key\n\nKEYBIND: "
).lower()

key_to_start = None

if question == "mouse":
    btn = input("Mouse button (Middle / M1 / M2): ").lower()
    key_to_start = {
        "middle": Button.middle,
        "m1": Button.x1,
        "m2": Button.x2
    }.get(btn)
else:
    key_to_start = keyboard.KeyCode.from_char(question)

mode = input("toggle or hold?: ").lower()
macro_enabled = False

def print_status():
    os.system("cls")
    fade.water(f"Press {key_to_start} to {mode} the macro\n")
    print(
        Fore.GREEN + "MACRO RUNNING" if macro_enabled else Fore.RED + "MACRO STOPPED",
        Fore.RESET
    )
    if not roblox_active:
        print(Fore.YELLOW + "Waiting for Roblox window..." + Fore.RESET)

# ===================== INPUT HANDLERS =====================
def on_press(key):
    global macro_enabled
    if key == key_to_start:
        if mode == "toggle":
            macro_enabled = not macro_enabled
        elif mode == "hold":
            macro_enabled = True
        print_status()

def on_release(key):
    global macro_enabled
    if mode == "hold" and key == key_to_start:
        macro_enabled = False
        print_status()

def on_click(x, y, button, pressed):
    global macro_enabled
    if button == key_to_start:
        if mode == "toggle" and pressed:
            macro_enabled = not macro_enabled
        elif mode == "hold":
            macro_enabled = pressed
        print_status()

# ===================== MACRO =====================
def run_macro():
    if not macro_enabled or not roblox_active:
        return

    mouse.scroll(0, 1)
    mouse.scroll(0, -1)
    mouse.scroll(0, 1)
    mouse.scroll(0, -1)

# ===================== MAIN =====================
def main():
    print_status()
    with keyboard.Listener(on_press=on_press, on_release=on_release), \
         MouseListener(on_click=on_click):
        while True:
            run_macro()
            time.sleep(0.007)

if __name__ == "__main__":
    main()
