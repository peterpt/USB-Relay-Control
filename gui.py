import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel, Listbox, Frame, Label, Button, Entry
from functools import partial
import serial
import serial.tools.list_ports
import configparser
import time
import sys
import os
from PIL import Image, ImageTk, UnidentifiedImageError

# --- Configuration (remains the same) ---
CONFIG_FILE = 'config.ini'
ICONS_DIR = 'icons'
DEFAULT_ON_ICON = 'Onled.png'
DEFAULT_OFF_ICON = 'Offled.png'
DEFAULT_ICON_SIZE = (48, 48)
BAUD_RATE = 9600
CH340_HWID = '1A86:7523'
# ---------------------

# --- Command Codebook (remains the same) ---
COMMANDS = {
    'ON': [bytearray.fromhex(h) for h in ['3A46453035303030304646303046450D0A', '3A46453035303030314646303046440D0A', '3A46453035303030324646303046430D0A', '3A46453035303030334646303046420D0A', '3A46453035303030344646303046410D0A', '3A46453035303030354646303046390D0A', '3A46453035303030364646303046380D0A', '3A46453035303030374646303046370D0A', '3A46453035303030384646303046360D0A', '3A46453035303030394646303046350D0A', '3A46453035303030414646303046340D0A', '3A46453035303030424646303046330D0A', '3A46453035303030434646303046320D0A', '3A46453035303030444646303046310D0A', '3A46453035303030454646303046300D0A', '3A46453035303030464646303046460D0A']],
    'OFF': [bytearray.fromhex(h) for h in ['3A46453035303030303030303046440D0A', '3A46453035303030313030303046430D0A', '3A46453035303030323030303046420D0A', '3A46453035303030333030303046410D0A', '3A46453035303030343030303046390D0A', '3A46453035303030353030303046380D0A', '3A46453035303030363030303046370D0A', '3A46453035303030373030303046360D0A', '3A46453035303030383030303046350D0A', '3A46453035303030393030303046340D0A', '3A46453035303030413030303046330D0A', '3A46453035303030423030303046320D0A', '3A46453035303030433030303046310D0A', '3A46453035303030443030303046300D0A', '3A46453035303030453030303046460D0A', '3A46453035303030463030303046450D0A']],
    'ALL_ON':  bytearray.fromhex('3A464530463030303030303130303246464645330D0A'),
    'ALL_OFF': bytearray.fromhex('3A4645304630303030303030313030323030303045310D0A'),
}

class IconManager:
    # ... (implementation unchanged)
    def __init__(self):
        self.photo_image_cache = {}
        os.makedirs(ICONS_DIR, exist_ok=True)
    def get_icon(self, filename, size):
        cache_key = (filename, size)
        if cache_key in self.photo_image_cache: return self.photo_image_cache[cache_key]
        try:
            path = os.path.join(ICONS_DIR, filename)
            with Image.open(path) as img:
                resized_img = img.resize(size, Image.Resampling.LANCZOS)
                photo_image = ImageTk.PhotoImage(resized_img)
                self.photo_image_cache[cache_key] = photo_image
                return photo_image
        except (FileNotFoundError, UnidentifiedImageError): return None

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("16-Channel USB Relay Controller")
        self.config(bg='gray20')
        self.geometry("600x600")

        self.icon_manager = IconManager()
        # ... (startup icon check unchanged) ...
        
        self.config_parser = configparser.ConfigParser()
        self.config_parser.read(CONFIG_FILE)

        self.current_port_name = None
        self.serial_port = None
        self.relay_widgets = {}
        self.is_connected = False
        
        # ... (main frame setup unchanged) ...
        self.main_frame = Frame(self, bg='gray30')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.module_info_frame = Frame(self.main_frame, bg='gray30')
        self.module_info_frame.pack(fill=tk.X, pady=5)
        self.relays_frame = Frame(self.main_frame, bg='gray30')
        self.relays_frame.pack(fill=tk.BOTH, expand=True)

        self.status_bar = Label(self, text="No device selected.", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.create_menu()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.after(100, self.load_first_available_module)
        self.after(2000, self.check_connection) # Start the connection monitor

    # --- NEW: Connection Monitoring ---
    def check_connection(self):
        if not self.current_port_name:
            self.after(2000, self.check_connection) # Keep checking if no module is loaded
            return

        # Check if the port still exists in the system's list of available ports
        available_ports = [p.device for p in serial.tools.list_ports.comports()]
        
        if self.current_port_name in available_ports:
            # Port exists, check if our connection is open
            if not self.is_connected:
                print(f"Device {self.current_port_name} reconnected. Re-initializing.")
                self.draw_module_display(self.current_port_name) # Re-initialize the view
            # is_connected is handled by draw_module_display
        else:
            # Port does not exist
            if self.is_connected:
                print(f"Device {self.current_port_name} disconnected.")
                self.is_connected = False
                if self.serial_port and self.serial_port.is_open:
                    self.serial_port.close()
                self.status_bar.config(text=f"DISCONNECTED: {self.current_port_name}", fg='red')
                self.disable_controls()
        
        self.after(2000, self.check_connection) # Schedule the next check

    def disable_controls(self):
        """Greys out all relay buttons."""
        for button in self.relay_widgets.values():
            button.config(state=tk.DISABLED)

    def enable_controls(self):
        """Enables all relay buttons."""
        for button in self.relay_widgets.values():
            button.config(state=tk.NORMAL)

    def create_menu(self):
        # ... (implementation unchanged) ...
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configure", menu=config_menu)
        config_menu.add_command(label="Devices...", command=self.open_device_manager)
        self.view_menu = tk.Menu(config_menu, tearoff=0)
        config_menu.add_cascade(label="View Module", menu=self.view_menu)
        self.update_view_menu()

    def update_view_menu(self):
        # ... (implementation unchanged) ...
        self.view_menu.delete(0, 'end')
        for section in self.config_parser.sections():
            name = self.config_parser.get(section, 'name', fallback=section)
            self.view_menu.add_command(label=name, command=lambda s=section: self.draw_module_display(s))

    def load_first_available_module(self):
        # ... (implementation unchanged) ...
        available_ports = [p.device for p in serial.tools.list_ports.comports()]
        for section in self.config_parser.sections():
            if section in available_ports:
                self.draw_module_display(section)
                return
        self.clear_main_frame()
        Label(self.main_frame, text="No configured devices connected.", bg='gray30', fg='white').pack(pady=50)

    def open_device_manager(self):
        DeviceManagerWindow(self)

    def draw_module_display(self, port_name):
        self.clear_main_frame()
        self.current_port_name = port_name

        try:
            if self.serial_port and self.serial_port.is_open: self.serial_port.close()
            self.serial_port = serial.Serial(self.current_port_name, BAUD_RATE, timeout=1)
            self.status_bar.config(text=f"Connected to: {self.current_port_name}", fg='black')
            self.is_connected = True
        except serial.SerialException as e:
            self.status_bar.config(text=f"Failed to connect: {self.current_port_name}", fg='red')
            Label(self.main_frame, text=f"Error opening port '{self.current_port_name}'.", bg='gray30', fg='red').pack()
            self.is_connected = False
            return

        name = self.config_parser.get(port_name, 'name', fallback=port_name)
        Label(self.module_info_frame, text=name, bg='gray30', fg='cyan', font=("Helvetica", 16, "bold")).pack(side=tk.LEFT, padx=10)

        # ... (relay widget creation unchanged) ...
        for i in range(16):
            rn, r, col = i + 1, i // 4, i % 4
            frame = Frame(self.relays_frame, bg='gray40', relief=tk.RIDGE, borderwidth=2)
            frame.grid(row=r, column=col, padx=10, pady=10, sticky="nsew")
            self.relays_frame.grid_columnconfigure(col, weight=1)
            self.relays_frame.grid_rowconfigure(r, weight=1)
            lbl_text = self.config_parser.get(port_name, f'relay_{rn}_label', fallback=f'Relay {rn}')
            label = Label(frame, text=lbl_text, bg='gray40', fg='white', font=("Helvetica", 10))
            label.pack(pady=(5, 0))
            icon_button = Button(frame, text="", width=DEFAULT_ICON_SIZE[0], height=DEFAULT_ICON_SIZE[1], command=partial(self.toggle_relay, i), relief=tk.FLAT, bg='gray40', activebackground='gray50')
            icon_button.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            self.relay_widgets[i] = icon_button

        self.send_command(COMMANDS['ALL_OFF'])
        for i in range(16): self.update_button_style(i, False)
        self.enable_controls() # Ensure controls are enabled on a successful draw

    def clear_main_frame(self):
        # ... (implementation unchanged) ...
        self.is_connected = False
        self.current_port_name = None
        if self.serial_port and self.serial_port.is_open: self.serial_port.close()
        self.serial_port = None
        self.relay_widgets = {}
        for widget in self.module_info_frame.winfo_children(): widget.destroy()
        for widget in self.relays_frame.winfo_children(): widget.destroy()
        for widget in self.main_frame.winfo_children():
            if widget not in (self.module_info_frame, self.relays_frame): widget.destroy()

    def send_command(self, command_bytes):
        # ... (implementation unchanged) ...
        if not self.serial_port or not self.serial_port.is_open:
            self.is_connected = False # Update state if we fail here
            self.disable_controls()
            self.status_bar.config(text=f"DISCONNECTED: {self.current_port_name}", fg='red')
            return False
        try:
            self.serial_port.write(command_bytes)
            time.sleep(0.05)
            return True
        except serial.SerialException as e:
            self.status_bar.config(text=f"Communication Error: {e}", fg='red')
            self.is_connected = False
            self.disable_controls()
            return False
    
    def on_closing(self):
        # ... (implementation unchanged) ...
        if self.serial_port and self.serial_port.is_open:
            self.send_command(COMMANDS['ALL_OFF'])
            time.sleep(0.1)
            self.serial_port.close()
        self.destroy()

    def toggle_relay(self, relay_index):
        # ... (implementation unchanged) ...
        current_state_is_on = self.relay_widgets[relay_index]._state_is_on
        new_state = not current_state_is_on
        command_type = 'ON' if new_state else 'OFF'
        command = COMMANDS[command_type][relay_index]
        if self.send_command(command):
            self.update_button_style(relay_index, new_state)

    def all_on(self):
        if self.send_command(COMMANDS['ALL_ON']):
            for i in range(16): self.update_button_style(i, True)

    def all_off(self):
        if self.send_command(COMMANDS['ALL_OFF']):
            for i in range(16): self.update_button_style(i, False)

    def update_button_style(self, relay_index, state):
        # ... (implementation unchanged) ...
        btn = self.relay_widgets[relay_index]
        btn._state_is_on = state
        port_name = self.current_port_name
        relay_num = relay_index + 1
        state_str = 'on' if state else 'off'
        icon_filename = self.config_parser.get(port_name, f'relay_{relay_num}_icon_{state_str}', fallback=None)
        if not icon_filename: icon_filename = DEFAULT_ON_ICON if state else DEFAULT_OFF_ICON
        icon = self.icon_manager.get_icon(icon_filename, DEFAULT_ICON_SIZE)
        if icon:
            btn.config(image=icon, width=DEFAULT_ICON_SIZE[0], height=DEFAULT_ICON_SIZE[1])
            btn.image = icon
        else:
            fallback_color = 'green' if state else 'red'
            btn.config(image='', bg=fallback_color, width=6, height=3)

# --- All other classes (DeviceManagerWindow, IconPickerDialog, ModuleEditDialog) remain unchanged ---
# ... (Paste the full code for these classes from the previous script here) ...
class DeviceManagerWindow(Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.config_parser = parent.config_parser
        self.title("Device Manager")
        self.transient(parent)
        self.grab_set()
        self.detected_ports = []
        Label(self, text="Detected Relay Boards:", font=('Helvetica', 10, 'bold')).pack(pady=5)
        self.listbox = Listbox(self, width=60, height=10)
        self.listbox.pack(padx=10, pady=5)
        self.listbox.bind('<Double-Button-1>', self.on_double_click)
        btn_frame = Frame(self)
        btn_frame.pack(pady=10)
        Button(btn_frame, text="Configure...", command=self.configure_selected).pack(side=tk.LEFT, padx=5)
        Button(btn_frame, text="Edit", command=self.edit_selected).pack(side=tk.LEFT, padx=5)
        Button(btn_frame, text="Remove", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        Button(btn_frame, text="Refresh", command=self.populate_list).pack(side=tk.LEFT, padx=5)
        self.populate_list()
    def populate_list(self):
        self.listbox.delete(0, 'end')
        self.detected_ports = [p for p in serial.tools.list_ports.comports() if CH340_HWID in p.hwid.upper()]
        configured_ports = self.config_parser.sections()
        for port in self.detected_ports:
            if port.device in configured_ports:
                name = self.config_parser.get(port.device, 'name', fallback=port.device)
                self.listbox.insert('end', f"{name} ({port.device}) [Configured]")
                self.listbox.itemconfig('end', {'fg': 'blue'})
            else:
                self.listbox.insert('end', f"{port.device} - {port.description} [New]")
                self.listbox.itemconfig('end', {'fg': 'green'})
    def get_selected_port_device(self):
        if not (sel := self.listbox.curselection()): return None
        list_string = self.listbox.get(sel[0])
        for port in self.detected_ports:
            if port.device in list_string:
                return port.device
        return None
    def on_double_click(self, event):
        self.configure_selected()
    def configure_selected(self):
        port_device = self.get_selected_port_device()
        if not port_device: return
        if port_device in self.config_parser.sections():
            messagebox.showinfo("Already Configured", "This device is already configured. Use 'Edit' to change its settings.", parent=self)
            return
        dialog = ModuleEditDialog(self, f"Configure {port_device}", port_device)
        self.wait_window(dialog)
        if dialog.was_saved:
            self.parent.update_view_menu()
            self.parent.draw_module_display(port_device)
            self.populate_list()
    def edit_selected(self):
        port_device = self.get_selected_port_device()
        if not port_device: return
        if port_device not in self.config_parser.sections():
            messagebox.showinfo("Not Configured", "This device is not configured yet. Use 'Configure' to add it.", parent=self)
            return
        dialog = ModuleEditDialog(self, f"Edit {port_device}", port_device)
        self.wait_window(dialog)
        if dialog.was_saved:
            self.parent.update_view_menu()
            if self.parent.current_port_name == port_device: self.parent.draw_module_display(port_device)
            self.populate_list()
    def remove_selected(self):
        port_device = self.get_selected_port_device()
        if not port_device: return
        if port_device not in self.config_parser.sections(): return
        if messagebox.askyesno("Confirm Removal", f"Are you sure you want to remove the configuration for {port_device}?", parent=self):
            self.config_parser.remove_section(port_device)
            with open(CONFIG_FILE, 'w') as configfile:
                self.config_parser.write(configfile)
            self.parent.update_view_menu()
            self.populate_list()
            if self.parent.current_port_name == port_device:
                self.parent.load_first_available_module()
class IconPickerDialog(Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Select an Icon")
        self.result = None
        self.photo_images = []
        icon_files = sorted([f for f in os.listdir(ICONS_DIR) if f.lower().endswith(('.png', '.gif', '.jpg', '.jpeg'))])
        cols = 4
        for i, filename in enumerate(icon_files):
            try:
                row, col = divmod(i, cols)
                img = Image.open(os.path.join(ICONS_DIR, filename))
                img.thumbnail((64, 64), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.photo_images.append(photo)
                Button(self, image=photo, command=lambda f=filename: self.select_icon(f)).grid(row=row, column=col, padx=5, pady=5)
            except Exception as e:
                print(f"Could not load icon for picker: {filename}, Error: {e}")
    def select_icon(self, filename):
        self.result = filename
        self.destroy()
class ModuleEditDialog(Toplevel):
    def __init__(self, parent, title, port_name):
        super().__init__(parent)
        self.parent = parent
        self.config_parser = parent.config_parser
        self.port_name = port_name
        self.was_saved = False
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.entries = {}
        self.icon_labels = {}
        self.icon_filenames = {}
        Label(self, text="Module Nickname:").grid(row=0, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        self.entries['name'] = Entry(self, width=50)
        self.entries['name'].grid(row=1, column=0, columnspan=2, sticky='ew', padx=5, pady=(0, 10))
        for i in range(16):
            rn = i + 1
            row_base = i * 3 + 2
            Label(self, text=f"Relay {rn} Label:").grid(row=row_base, column=0, sticky='w', padx=5, pady=2)
            self.entries[f'relay_{rn}_label'] = Entry(self, width=40)
            self.entries[f'relay_{rn}_label'].grid(row=row_base, column=1, sticky='w', padx=5, pady=2)
            Button(self, text="ON Icon...", command=lambda r=rn: self.pick_icon(r, 'on')).grid(row=row_base + 1, column=0, sticky='w', padx=5, pady=2)
            self.icon_labels[f'{rn}_on'] = Label(self, text="Default", fg='gray50', width=30, anchor='w')
            self.icon_labels[f'{rn}_on'].grid(row=row_base + 1, column=1, sticky='w', padx=5)
            Button(self, text="OFF Icon...", command=lambda r=rn: self.pick_icon(r, 'off')).grid(row=row_base + 2, column=0, sticky='w', padx=5, pady=2)
            self.icon_labels[f'{rn}_off'] = Label(self, text="Default", fg='gray50', width=30, anchor='w')
            self.icon_labels[f'{rn}_off'].grid(row=row_base + 2, column=1, sticky='w', padx=5)
        if self.port_name in self.config_parser.sections(): self.load_data()
        Button(self, text="Save", command=self.save).grid(row=99, column=0, columnspan=2, pady=20)
    def pick_icon(self, relay_num, state):
        dialog = IconPickerDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            key = f'{relay_num}_{state}'
            self.icon_filenames[key] = dialog.result
            self.icon_labels[key].config(text=dialog.result, fg='black')
    def load_data(self):
        for key, entry in self.entries.items():
            entry.insert(0, self.config_parser.get(self.port_name, key, fallback=''))
        for rn in range(1, 17):
            for state in ['on', 'off']:
                key = f'{rn}_{state}'
                icon_file = self.config_parser.get(self.port_name, f'relay_{rn}_icon_{state}', fallback=None)
                if icon_file:
                    self.icon_filenames[key] = icon_file
                    self.icon_labels[key].config(text=icon_file, fg='black')
    def save(self):
        if not self.config_parser.has_section(self.port_name):
            self.config_parser.add_section(self.port_name)
        for key, entry in self.entries.items():
            self.config_parser.set(self.port_name, key, entry.get())
        for key, filename in self.icon_filenames.items():
            relay_num, state = key.split('_')
            config_key = f'relay_{relay_num}_icon_{state}'
            self.config_parser.set(self.port_name, config_key, filename)
        with open(CONFIG_FILE, 'w') as configfile:
            self.config_parser.write(configfile)
        self.was_saved = True
        self.destroy()

if __name__ == "__main__":
    try:
        import serial
        from PIL import Image, ImageTk
    except ImportError as e:
        if 'serial' in str(e): print("Error: 'pyserial' not installed. Please run: pip install pyserial")
        elif 'PIL' in str(e): print("Error: 'Pillow' not installed. Please run: pip install Pillow")
        sys.exit(1)
        
    app = App()
    app.mainloop()
