# import queue
# import sys
# import os
import threading
# import kthread
# from datetime import datetime
# from time import sleep
# import cv2
# import json
from pathlib import Path
from datetime import datetime
import os
import queue
import subprocess

import keyboard
import webbrowser
# import requests


# from PIL import Image, ImageGrab, ImageTk
import tkinter as tk
from tkinter import filedialog as fd
from tkinter import messagebox
from tkinter import ttk
import sv_ttk
import pywinstyles
import sys  # Do not delete - prevents a 'super' error from tktoolip.
from time import sleep
from tktooltip import ToolTip  # In requirements.txt as 'tkinter-tooltip'.

from src.autopilot import ED_AP

from src.core.EDlogger import logger
from src.core.constants import EDAP_VERSION, FORM_TYPE_CHECKBOX, FORM_TYPE_SPINBOX, FORM_TYPE_ENTRY

"""
File:EDBob.py

Description:
User interface for controlling the ED Autopilot

 HotKeys:
    Home - Start FSD Assist
    INS  - Start SC Assist
    End - Terminate any ongoing assist (FSD, SC)

"""



def str_to_float(input_str: str) -> float:
    try:
        return float(input_str)
    except ValueError:
        return 0.0  # Assign a default value on error


class APGui:

    def __init__(self, root):
        self.statusbar = None
        self.root = root
        root.title("EDAutopilot " + EDAP_VERSION)
        root.geometry("1440x900")
        root.protocol("WM_DELETE_WINDOW", self.close_window)
        root.resizable(False, False)

        self.tooltips = {
            'Waypoint Assist': "When selected, will prompt for the waypoint file. \nThe waypoint file contains System names that \nwill be entered into Galaxy Map and route plotted.",
            'PitchRate': "Pitch (up/down) rate your ship has in deg/sec. Higher the number the more maneuverable the ship.",
            'YawRate': "Yaw rate (rudder) your ship has in deg/sec. Higher the number the more maneuverable the ship.",
            'PitchFactor': "TBD",
            'YawFactor': "TBD",
            'SunPitchUp+Time': "This field are for ship that tend to overheat. \nProviding 1-2 more seconds of Pitch up when avoiding the Sun \nwill overcome this problem.",
            'Sun Bright Threshold': "The low level for brightness detection, \nrange 0-255, want to mask out darker items",
            'Nav Align Tries': "How many attempts the ap should make at alignment.",
            'Jump Tries': "How many attempts the ap should make to jump.",
            'Docking Retries': "How many attempts to make to dock.",
            'Wait For Autodock': "After docking granted, \nwait this amount of time for us to get docked with autodocking",
            'Start FSD': "Button to start FSD route assist.",
            'Start SC': "Button to start Supercruise assist.",
            'Stop All': "Button to stop all assists.",
            'Refuel Threshold': "If fuel level get below this level, \nit will attempt refuel.",
            'Scoop Timeout': "Number of second to wait for full tank, \nmight mean we are not scooping well or got a small scooper",
            'Fuel Threshold Abort': "Level at which AP will terminate, \nbecause we are not scooping well.",
            'Calibrate': "Will iterate through a set of scaling values \ngetting the best match for your system. \nSee HOWTO-Calibrate.md",
            'Cap Mouse XY': "This will provide the StationCoord value of the Station in the SystemMap. \nSelecting this button and then clicking on the Station in the SystemMap \nwill return the x,y value that can be pasted in the waypoints file",
            'Debug Images': "Enables debug images to be stored in the 'debug_output' folder.",
            'Modifier Key Delay': "Delay for key modifiers to ensure modifier is detected before/after the key.",
            'Default Hold Time': "Default hold time for a key press.",
            'Repeat Key Delay': "Delay between key press repeats.",
        }

        self.gui_loaded = False
        self.log_buffer = queue.Queue()
        self.callback('log', f'Starting ED Autopilot {EDAP_VERSION}.')

        self.ed_ap = ED_AP.EDAutopilot(cb=self.callback)


        self.checkboxvar = {}
        self.radiobuttonvar = {}
        self.entries = {}
        self.lab_ck = {}
        self.WP_A_running = False

        self.msgList = self.gui_gen(root)

        self.checkboxvar['Activate Elite for each key'].set(self.ed_ap.config['ActivateEliteEachKey'])
        self.checkboxvar['Automatic logout'].set(self.ed_ap.config['AutomaticLogout'])
        self.checkboxvar['Enable Hotkeys'].set(self.ed_ap.config['HotkeysEnable'])
        self.checkboxvar['Debug Images'].set(self.ed_ap.config['DebugImages'])
        self.radiobuttonvar['dss_button'].set(self.ed_ap.config['DSSButton'])

        self.entries['ship']['PitchRate'].delete(0, tk.END)
        self.entries['ship']['YawRate'].delete(0, tk.END)
        self.entries['ship']['SunPitchUp+Time'].delete(0, tk.END)
        self.entries['ship']['PitchFactor'].delete(0, tk.END)
        self.entries['ship']['YawFactor'].delete(0, tk.END)

        self.entries['autopilot']['Sun Bright Threshold'].delete(0, tk.END)
        self.entries['autopilot']['Nav Align Tries'].delete(0, tk.END)
        self.entries['autopilot']['Jump Tries'].delete(0, tk.END)
        self.entries['autopilot']['Docking Retries'].delete(0, tk.END)
        self.entries['autopilot']['Wait For Autodock'].delete(0, tk.END)

        self.entries['refuel']['Refuel Threshold'].delete(0, tk.END)
        self.entries['refuel']['Scoop Timeout'].delete(0, tk.END)
        self.entries['refuel']['Fuel Threshold Abort'].delete(0, tk.END)

        self.entries['buttons']['Start FSD'].delete(0, tk.END)
        self.entries['buttons']['Start SC'].delete(0, tk.END)
        self.entries['buttons']['Stop All'].delete(0, tk.END)

        self.entries['keys']['Modifier Key Delay'].delete(0, tk.END)
        self.entries['keys']['Default Hold Time'].delete(0, tk.END)
        self.entries['keys']['Repeat Key Delay'].delete(0, tk.END)

        self.entries['ship']['PitchRate'].insert(0, float(self.ed_ap.pitchrate))
        self.entries['ship']['YawRate'].insert(0, float(self.ed_ap.yawrate))
        self.entries['ship']['SunPitchUp+Time'].insert(0, float(self.ed_ap.sunpitchuptime))
        self.entries['ship']['PitchFactor'].insert(0, float(self.ed_ap.pitchfactor))
        self.entries['ship']['YawFactor'].insert(0, float(self.ed_ap.yawfactor))

        self.entries['autopilot']['Sun Bright Threshold'].insert(0, int(self.ed_ap.config['SunBrightThreshold']))
        self.entries['autopilot']['Nav Align Tries'].insert(0, int(self.ed_ap.config['NavAlignTries']))
        self.entries['autopilot']['Jump Tries'].insert(0, int(self.ed_ap.config['JumpTries']))
        self.entries['autopilot']['Docking Retries'].insert(0, int(self.ed_ap.config['DockingRetries']))
        self.entries['autopilot']['Wait For Autodock'].insert(0, int(self.ed_ap.config['WaitForAutoDockTimer']))
        self.entries['refuel']['Refuel Threshold'].insert(0, int(self.ed_ap.config['RefuelThreshold']))
        self.entries['refuel']['Scoop Timeout'].insert(0, int(self.ed_ap.config['FuelScoopTimeOut']))
        self.entries['refuel']['Fuel Threshold Abort'].insert(0, int(self.ed_ap.config['FuelThresholdAbortAP']))
        self.entries['buttons']['Start FSD'].insert(0, str(self.ed_ap.config['HotKey_StartFSD']))
        self.entries['buttons']['Start SC'].insert(0, str(self.ed_ap.config['HotKey_StartSC']))
        self.entries['buttons']['Stop All'].insert(0, str(self.ed_ap.config['HotKey_StopAllAssists']))

        self.entries['keys']['Modifier Key Delay'].insert(0, float(self.ed_ap.config['Key_ModDelay']))
        self.entries['keys']['Default Hold Time'].insert(0, float(self.ed_ap.config['Key_DefHoldTime']))
        self.entries['keys']['Repeat Key Delay'].insert(0, float(self.ed_ap.config['Key_RepeatDelay']))

        if self.ed_ap.config['LogDEBUG']:
            self.radiobuttonvar['debug_mode'].set("Debug")
        elif self.ed_ap.config['LogINFO']:
            self.radiobuttonvar['debug_mode'].set("Info")
        else:
            self.radiobuttonvar['debug_mode'].set("Error")

        # Hotkeys
        self.setup_hotkeys()

        # check for updates
        self.check_updates()

        sleep(0.25)  # Added because the custom tkinter takes longer to load? Without, you occasionally get errors
        # that the main thread is not in main loop.
        self.ed_ap.gui_loaded = True
        self.gui_loaded = True
        # Send a log entry which will flush out the buffer.
        self.callback('log', 'ED Autopilot loaded successfully.')

    def setup_hotkeys(self):
        """ Enable or disable hotkeys.
        Global trap for these keys, the 'end' key will stop any current AP action the 'home' key will start the
        FSD Assist. May want another to start SC Assist.
        """
        # Remove all the hotkeys. Adding a dummy hotkey will eliminate an error if none had been configured.
        keyboard.add_hotkey(' ', print)
        keyboard.remove_all_hotkeys()

        if self.ed_ap.config['HotkeysEnable']:
            # Add the desired hotkeys
            keyboard.add_hotkey(self.ed_ap.config['HotKey_StopAllAssists'], self.stop_all_assists)
            keyboard.add_hotkey(self.ed_ap.config['HotKey_StartFSD'], self.callback, args=('fsd_start', None))

    # callback from the EDAP, to configure GUI items
    def callback(self, msg, body=None):
        if msg == 'log':
            self.log_msg(body)
        elif msg == 'log+vce':
            self.log_msg(body)
        elif msg == 'statusline':
            self.root.after(0, self.update_statusline, body)
        elif msg == 'waypoint_stop':
            logger.debug("Detected 'waypoint_stop' callback msg")
            self.root.after(0, lambda: (self.checkboxvar['Waypoint Assist'].set(0), self.check_cb('Waypoint Assist')))
        elif msg == 'waypoint_start':
            self.root.after(0, lambda: (self.checkboxvar['Waypoint Assist'].set(1), self.check_cb('Waypoint Assist')))
        elif msg == 'stop_all_assists':
            logger.debug("Detected 'stop_all_assists' callback msg")
            self.root.after(0, lambda: (self.checkboxvar['Waypoint Assist'].set(0), self.check_cb('Waypoint Assist')))

        elif msg == 'jumpcount':
            self.root.after(0, self.update_jumpcount, body)
        elif msg == 'update_ship_cfg':
            self.root.after(0, self.update_ship_cfg)

    def update_ship_cfg(self):
        # load up the display with what we read from ED_AP for the current ship
        self.entries['ship']['PitchRate'].delete(0, tk.END)
        self.entries['ship']['YawRate'].delete(0, tk.END)
        self.entries['ship']['SunPitchUp+Time'].delete(0, tk.END)
        self.entries['ship']['PitchFactor'].delete(0, tk.END)
        self.entries['ship']['YawFactor'].delete(0, tk.END)

        self.entries['ship']['PitchRate'].insert(0, self.ed_ap.pitchrate)
        self.entries['ship']['YawRate'].insert(0, self.ed_ap.yawrate)
        self.entries['ship']['SunPitchUp+Time'].insert(0, self.ed_ap.sunpitchuptime)
        self.entries['ship']['PitchFactor'].insert(0, self.ed_ap.pitchfactor)
        self.entries['ship']['YawFactor'].insert(0, self.ed_ap.yawfactor)

    def quit(self):
        logger.debug("Entered: quit")
        self.close_window()

    def close_window(self):
        logger.debug("Entered: close_window")
        self.stop_all_assists()
        sleep(0.5)
        self.ed_ap.quit()
        sleep(0.1)
        self.root.destroy()

    # this routine is to stop any current autopilot activity
    def stop_all_assists(self):
        logger.debug("Entered: stop_all_assists")
        self.callback('stop_all_assists')

    def start_waypoint(self):
        logger.debug("Entered: start_waypoint")
        self.ed_ap.set_waypoint_assist(True)
        self.WP_A_running = True
        self.log_msg("Waypoint Assist start")

    def stop_waypoint(self):
        logger.debug("Entered: stop_waypoint")
        self.ed_ap.set_waypoint_assist(False)
        self.WP_A_running = False
        self.log_msg("Waypoint Assist stop")
        self.update_statusline("Idle")

    def about(self):
        webbrowser.open_new("https://github.com/Fumlop/EDBob")

    def check_for_updates(self, repo_path):
        try:
            # Fetch the latest changes from the remote repository
            subprocess.run(["git", "fetch"], cwd=repo_path, check=True, capture_output=True)

            # Get the current commit hash of the local repository
            local_hash = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, text=True,
                                        check=True).stdout.strip()

            # Get the commit hash of the remote repository
            remote_hash = subprocess.run(["git", "rev-parse", "origin/HEAD"], cwd=repo_path, capture_output=True,
                                         text=True, check=True).stdout.strip()

            # Compare the commit hashes
            if local_hash != remote_hash:
                logger.info("The repository has been updated. Please clone it again to get the latest version.")
                return True
            else:
                logger.debug("The repository is up to date.")
                return False

        except subprocess.CalledProcessError as e:
            logger.debug(f"Error checking for updates: {e}")
            return False
        except FileNotFoundError:
            logger.debug("Git command not found. Please ensure Git is installed and in your system's PATH.")
            return False

    def check_updates(self):
        # response = requests.get("https://api.github.com/repos/Fumlop/EDBob/releases/latest")
        # if EDAP_VERSION != response.json()["name"]:
        #     mb = messagebox.askokcancel("Update Check", "A new release version is available. Download now?")
        #     if mb == True:
        #         webbrowser.open_new("https://github.com/Fumlop/EDBob/releases/latest")

        # Example usage:
        # repo_path = "/path/to/your/local/repo"
        repo_path = "./"
        updates_available = self.check_for_updates(repo_path)

        if updates_available:
            # Optionally, provide further instructions or automate the cloning process
            self.log_msg("An update to EDBob is available!")
            self.log_msg("Visit https://github.com/Fumlop/EDBob to update.")
        else:
            self.log_msg("You have the latest version of EDBob.")

    def open_changelog(self):
        webbrowser.open_new("https://github.com/Fumlop/EDBob/blob/main/ChangeLog.md")

    def open_discord(self):
        webbrowser.open_new("https://discord.gg/HCgkfSc")

    def open_logfile(self):
        os.startfile('autopilot.log')

    def log_msg(self, msg):
        message = datetime.now().strftime("%H:%M:%S: ") + msg

        try:
            if not self.gui_loaded:
                # Store message in queue
                self.log_buffer.put(message)
                logger.info(msg)
            else:
                # Add queued messages to the list
                while not self.log_buffer.empty():
                    self.msgList.insert(tk.END, self.log_buffer.get())

                self.msgList.insert(tk.END, message)
                self.msgList.yview(tk.END)
                logger.info(msg)
        except Exception:
            # Store message in queue
            self.log_buffer.put(message)
            logger.info(msg)

    def set_statusbar(self, txt):
        self.statusbar.configure(text=txt)

    def update_jumpcount(self, txt):
        self.jumpcount.configure(text=txt)

    def update_statusline(self, txt):
        self.status.configure(text="Status: " + txt)
        self.log_msg(f"Status update: {txt}")

    def ship_tst_pitch(self):
        self.ed_ap.ship_tst_pitch_enabled = True

    def ship_tst_roll(self):
        self.ed_ap.ship_tst_roll_enabled = True

    def ship_tst_yaw(self):
        self.ed_ap.ship_tst_yaw_enabled = True

    def save_settings(self):
        self.entry_update(None)
        self.ed_ap.update_config()
        self.ed_ap.update_ship_configs()
        self.log_msg("Saved all settings.")

    def load_settings(self):
        self.ed_ap.load_ship_configs()

    def load_waypoint_file(self):
        filepath = fd.askopenfilename(
            title="Open Waypoint File",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
            initialdir="./waypoints"
        )
        if filepath:
            self._do_load_waypoint(filepath)

    def load_last_waypoint_file(self):
        filepath = self.ed_ap.config.get('WaypointFilepath', '')
        if filepath:
            self._do_load_waypoint(filepath)

    def _do_load_waypoint(self, filepath):
        if self.ed_ap.waypoint.load_waypoint_file(filepath):
            self.wp_file_label.config(text=Path(filepath).name)
            self.refresh_commodity_tree()
        else:
            self.wp_file_label.config(text="Load failed")

    def refresh_commodity_tree(self):
        self.comm_tree.delete(*self.comm_tree.get_children())
        wps = self.ed_ap.waypoint.waypoints
        for key, value in wps.items():
            if key == "GlobalShoppingList":
                for comm, qty in value.get('BuyCommodities', {}).items():
                    self.comm_tree.insert("", "end", values=(key, "Buy", comm, qty))
            else:
                for comm, qty in value.get('BuyCommodities', {}).items():
                    self.comm_tree.insert("", "end", values=(key, "Buy", comm, qty))
                for comm, qty in value.get('SellCommodities', {}).items():
                    self.comm_tree.insert("", "end", values=(key, "Sell", comm, qty))

    def _on_commodity_select(self, event):
        sel = self.comm_tree.selection()
        if not sel:
            return
        vals = self.comm_tree.item(sel[0], "values")
        self.comm_qty_spin.delete(0, "end")
        self.comm_qty_spin.insert(0, vals[3])

    def update_commodity_qty(self):
        sel = self.comm_tree.selection()
        if not sel:
            return
        item = sel[0]
        vals = list(self.comm_tree.item(item, "values"))
        new_qty = int(self.comm_qty_spin.get())
        vals[3] = new_qty
        self.comm_tree.item(item, values=vals)

    def save_commodities(self):
        wps = self.ed_ap.waypoint.waypoints
        # Clear existing commodities
        for key, value in wps.items():
            if key == "GlobalShoppingList":
                value['BuyCommodities'] = {}
            else:
                value['BuyCommodities'] = {}
                value['SellCommodities'] = {}
        # Rebuild from treeview
        for item_id in self.comm_tree.get_children():
            wp_name, buy_sell, comm, qty = self.comm_tree.item(item_id, "values")
            qty = int(qty)
            if buy_sell == "Buy":
                wps[wp_name]['BuyCommodities'][comm] = qty
            else:
                wps[wp_name]['SellCommodities'][comm] = qty
        # Save to file
        self.ed_ap.waypoint.write_waypoints(
            data=None, filename='./waypoints/' + Path(self.ed_ap.waypoint.filename).name)
        self.log_msg("Saved commodity changes.")

    # new data was added to a field, re-read them all for simple logic
    def entry_update(self, event):
        try:
            self.ed_ap.pitchrate = float(self.entries['ship']['PitchRate'].get())
            self.ed_ap.yawrate = float(self.entries['ship']['YawRate'].get())
            self.ed_ap.sunpitchuptime = float(self.entries['ship']['SunPitchUp+Time'].get())
            self.ed_ap.pitchfactor = float(self.entries['ship']['PitchFactor'].get())
            self.ed_ap.yawfactor = float(self.entries['ship']['YawFactor'].get())

            self.ed_ap.config['SunBrightThreshold'] = int(self.entries['autopilot']['Sun Bright Threshold'].get())
            self.ed_ap.config['NavAlignTries'] = int(self.entries['autopilot']['Nav Align Tries'].get())
            self.ed_ap.config['JumpTries'] = int(self.entries['autopilot']['Jump Tries'].get())
            self.ed_ap.config['DockingRetries'] = int(self.entries['autopilot']['Docking Retries'].get())
            self.ed_ap.config['WaitForAutoDockTimer'] = int(self.entries['autopilot']['Wait For Autodock'].get())
            self.ed_ap.config['RefuelThreshold'] = int(self.entries['refuel']['Refuel Threshold'].get())
            self.ed_ap.config['FuelScoopTimeOut'] = int(self.entries['refuel']['Scoop Timeout'].get())
            self.ed_ap.config['FuelThresholdAbortAP'] = int(self.entries['refuel']['Fuel Threshold Abort'].get())
            self.ed_ap.config['HotKey_StartFSD'] = str(self.entries['buttons']['Start FSD'].get())
            self.ed_ap.config['HotKey_StartSC'] = str(self.entries['buttons']['Start SC'].get())
            self.ed_ap.config['HotKey_StopAllAssists'] = str(self.entries['buttons']['Stop All'].get())
            self.ed_ap.config['HotkeysEnable'] = self.checkboxvar['Enable Hotkeys'].get()
            self.ed_ap.config['DebugImages'] = self.checkboxvar['Debug Images'].get()
            self.ed_ap.config['Key_ModDelay'] = float(self.entries['keys']['Modifier Key Delay'].get())
            self.ed_ap.config['Key_DefHoldTime'] = float(self.entries['keys']['Default Hold Time'].get())
            self.ed_ap.config['Key_RepeatDelay'] = float(self.entries['keys']['Repeat Key Delay'].get())

            # Process config[] settings to update classes as necessary
            self.ed_ap.process_config_settings()
        except (ValueError, KeyError):
            messagebox.showinfo("Exception", "Invalid float entered")

    # ckbox.state:(ACTIVE | DISABLED)

    def check_cb(self, field):
        if field == 'Waypoint Assist':
            if self.checkboxvar['Waypoint Assist'].get() == 1 and self.WP_A_running == False:
                self.start_waypoint()

            elif self.checkboxvar['Waypoint Assist'].get() == 0 and self.WP_A_running == True:
                self.stop_waypoint()

        if self.checkboxvar['Activate Elite for each key'].get():
            self.ed_ap.set_activate_elite_eachkey(True)
            self.ed_ap.keys.activate_window = True
        else:
            self.ed_ap.set_activate_elite_eachkey(False)
            self.ed_ap.keys.activate_window = False

        if self.checkboxvar['Automatic logout'].get():
            self.ed_ap.set_automatic_logout(True)
        else:
            self.ed_ap.set_automatic_logout(False)

        self.ed_ap.config['DSSButton'] = self.radiobuttonvar['dss_button'].get()

        if self.radiobuttonvar['debug_mode'].get() == "Error":
            self.ed_ap.set_log_error(True)
        elif self.radiobuttonvar['debug_mode'].get() == "Debug":
            self.ed_ap.set_log_debug(True)
        elif self.radiobuttonvar['debug_mode'].get() == "Info":
            self.ed_ap.set_log_info(True)

        if field == 'Enable Hotkeys':
            self.ed_ap.config['HotkeysEnable'] = self.checkboxvar['Enable Hotkeys'].get()
            self.setup_hotkeys()

        if field == 'Debug Images':
            self.ed_ap.debug_images = self.checkboxvar['Debug Images'].get()

    def makeform(self, win, ftype, fields, r: int = 0, inc: float = 1, r_from: float = 0, rto: float = 1000):
        entries = {}
        win.columnconfigure(1, weight=1)

        for field in fields:
            if ftype == FORM_TYPE_CHECKBOX:
                self.checkboxvar[field] = tk.IntVar()
                lab = ttk.Checkbutton(win, text=field, variable=self.checkboxvar[field], command=(lambda field=field: self.check_cb(field)))
                self.lab_ck[field] = lab
                lab.grid(row=r, column=0, columnspan=2, padx=2, pady=2, sticky=tk.W)
            else:
                lab = ttk.Label(win, text=field + ": ")
                if ftype == FORM_TYPE_SPINBOX:
                    ent = ttk.Spinbox(win, width=10, from_=r_from, to=rto, increment=inc, justify=tk.RIGHT)
                else:
                    ent = ttk.Entry(win, width=10, justify=tk.RIGHT)
                ent.bind('<FocusOut>', self.entry_update)
                ent.insert(0, "0")
                lab.grid(row=r, column=0, padx=2, pady=2, sticky=tk.W)
                ent.grid(row=r, column=1, padx=2, pady=2, sticky=tk.E)
                entries[field] = ent

            lab = ToolTip(lab, msg=self.tooltips[field], delay=1.0, bg="#808080", fg="#FFFFFF")
            r += 1
        return entries

    def gui_gen(self, win):

        modes_check_fields = ('Waypoint Assist',)
        ship_entry_fields = ('PitchRate', 'YawRate', 'PitchFactor', 'YawFactor')
        autopilot_entry_fields = ('Sun Bright Threshold', 'Nav Align Tries', 'Jump Tries', 'Docking Retries', 'Wait For Autodock')
        buttons_entry_fields = ('Start FSD', 'Start SC', 'Stop All')
        refuel_entry_fields = ('Refuel Threshold', 'Scoop Timeout', 'Fuel Threshold Abort')
        keys_entry_fields = ('Modifier Key Delay', 'Default Hold Time', 'Repeat Key Delay')

        # notebook pages
        blk_top_buttons = ttk.Frame(win)
        blk_top_buttons.grid(row=0, column=0, padx=10, pady=5, sticky="EW")
        blk_top_buttons.columnconfigure(0)
        blk_top_buttons.columnconfigure(1, weight=1)

        btn_load = ttk.Button(blk_top_buttons, text='Load All Settings', command=self.load_settings)
        btn_load.grid(row=0, column=0, padx=5, pady=5, sticky="W")
        btn_save = ttk.Button(blk_top_buttons, text='Save All Settings', command=self.save_settings, style="Accent.TButton")
        btn_save.grid(row=0, column=1, padx=2, pady=5, sticky="W")

        win.grid_rowconfigure(1, weight=1)
        win.grid_columnconfigure(0, weight=1)

        nb = ttk.Notebook(win)
        nb.grid(row=1, padx=10, pady=5, sticky="NSEW")

        page0 = ttk.Frame(nb)
        page0.grid_columnconfigure(0, weight=1)
        page0.grid_rowconfigure(0, weight=0)
        page0.grid_rowconfigure(1, weight=2)  # Commodities row
        page0.grid_rowconfigure(2, weight=1)  # Log row
        nb.add(page0, text="Main")  # main page

        page1 = ttk.Frame(nb)
        page1.grid_columnconfigure(0, weight=1)
        nb.add(page1, text="Settings")  # options page

        # === MAIN TAB ===
        # main options block
        blk_main = ttk.Frame(page0)
        blk_main.grid(row=0, column=0, padx=10, pady=5, sticky="NSEW")
        blk_main.columnconfigure([0, 1], weight=1, minsize=100, uniform="group1")

        # ap mode checkboxes block
        blk_modes = ttk.LabelFrame(blk_main, text="MODE", padding=(10, 5))
        blk_modes.grid(row=0, column=0, padx=2, pady=2, sticky="NSEW")
        self.makeform(blk_modes, FORM_TYPE_CHECKBOX, modes_check_fields)

        # waypoints block
        blk_wp = ttk.LabelFrame(blk_main, text="WAYPOINTS", padding=(10, 5))
        blk_wp.grid(row=0, column=1, padx=2, pady=2, sticky="NSEW")

        self.wp_file_label = ttk.Label(blk_wp, text="No file loaded")
        self.wp_file_label.grid(row=0, column=0, columnspan=2, pady=3, sticky=tk.W)

        btn_load_wp = ttk.Button(blk_wp, text="Load File", command=self.load_waypoint_file)
        btn_load_wp.grid(row=1, column=0, padx=2, pady=2, sticky="NSEW")

        btn_load_last = ttk.Button(blk_wp, text="Load Last", command=self.load_last_waypoint_file)
        btn_load_last.grid(row=1, column=1, padx=2, pady=2, sticky="NSEW")

        # commodities block
        blk_comm = ttk.LabelFrame(page0, text="COMMODITIES", padding=(10, 5))
        blk_comm.grid(row=1, column=0, padx=10, pady=5, sticky="NSEW")
        blk_comm.grid_columnconfigure(0, weight=1)
        blk_comm.grid_rowconfigure(0, weight=1)

        cols = ("waypoint", "type", "commodity", "qty")
        self.comm_tree = ttk.Treeview(blk_comm, columns=cols, show="headings", height=5)
        self.comm_tree.heading("waypoint", text="Waypoint")
        self.comm_tree.heading("type", text="Buy/Sell")
        self.comm_tree.heading("commodity", text="Commodity")
        self.comm_tree.heading("qty", text="Qty")
        self.comm_tree.column("waypoint", width=150)
        self.comm_tree.column("type", width=60)
        self.comm_tree.column("commodity", width=150)
        self.comm_tree.column("qty", width=60)
        self.comm_tree.grid(row=0, column=0, sticky="NSEW")

        comm_scroll = ttk.Scrollbar(blk_comm, orient="vertical", command=self.comm_tree.yview)
        comm_scroll.grid(row=0, column=1, sticky="NS")
        self.comm_tree.configure(yscrollcommand=comm_scroll.set)

        # Edit row: qty spinbox + save button
        comm_edit_frame = ttk.Frame(blk_comm)
        comm_edit_frame.grid(row=1, column=0, columnspan=2, sticky="EW", pady=(5, 0))

        ttk.Label(comm_edit_frame, text="Qty:").pack(side="left", padx=2)
        self.comm_qty_spin = ttk.Spinbox(comm_edit_frame, width=8, from_=0, to=99999, increment=1)
        self.comm_qty_spin.pack(side="left", padx=2)

        ttk.Button(comm_edit_frame, text="Update", command=self.update_commodity_qty).pack(side="left", padx=2)
        ttk.Button(comm_edit_frame, text="Save", command=self.save_commodities).pack(side="left", padx=2)

        self.comm_tree.bind("<<TreeviewSelect>>", self._on_commodity_select)

        # log window
        log = ttk.LabelFrame(page0, text="LOG", padding=(10, 5))
        log.grid(row=2, column=0, padx=10, pady=5, sticky="NSEW")
        log.grid_columnconfigure(0, weight=1)
        log.grid_rowconfigure(0, weight=1)
        y_scrollbar = ttk.Scrollbar(log)
        y_scrollbar.grid(row=0, column=1, sticky="NSE")
        x_scrollbar = ttk.Scrollbar(log, orient="horizontal")
        x_scrollbar.grid(row=1, column=0, sticky="EW")
        mylist = tk.Listbox(log, width=100, height=10, yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        mylist.grid(row=0, column=0, sticky="NSEW")
        y_scrollbar.config(command=mylist.yview)
        x_scrollbar.config(command=mylist.xview)

        # === SETTINGS TAB ===
        # settings block
        blk_settings = ttk.Frame(page1)
        blk_settings.grid(row=0, column=0, padx=10, pady=5, sticky="EW")
        blk_settings.columnconfigure([0, 1], weight=1, minsize=100, uniform="group1")

        # autopilot settings block
        blk_ap = ttk.LabelFrame(blk_settings, text="AUTOPILOT", padding=(10, 5))
        blk_ap.grid(row=0, column=0, padx=2, pady=2, sticky="NSEW")
        self.entries['autopilot'] = self.makeform(blk_ap, FORM_TYPE_SPINBOX, autopilot_entry_fields)
        self.checkboxvar['Automatic logout'] = tk.BooleanVar()
        cb_logout = ttk.Checkbutton(blk_ap, text='Automatic logout', variable=self.checkboxvar['Automatic logout'], command=(lambda field='Automatic logout': self.check_cb(field)))
        cb_logout.grid(row=6, column=0, columnspan=2, sticky=tk.W)

        # buttons settings block
        blk_buttons = ttk.LabelFrame(blk_settings, text="BUTTONS", padding=(10, 5))
        blk_buttons.grid(row=0, column=1, padx=2, pady=2, sticky="NSEW")
        blk_dss = ttk.Frame(blk_buttons)
        blk_dss.grid(row=0, column=0, columnspan=2, padx=0, pady=0, sticky="NSEW")
        lb_dss = ttk.Label(blk_dss, text="DSS Button: ")
        lb_dss.grid(row=0, column=0, sticky=tk.W)
        self.radiobuttonvar['dss_button'] = tk.StringVar()
        rb_dss_primary = ttk.Radiobutton(blk_dss, text="Primary", variable=self.radiobuttonvar['dss_button'], value="Primary", command=(lambda field='dss_button': self.check_cb(field)))
        rb_dss_primary.grid(row=0, column=1, sticky=tk.W)
        rb_dss_secondary = ttk.Radiobutton(blk_dss, text="Secondary", variable=self.radiobuttonvar['dss_button'], value="Secondary", command=(lambda field='dss_button': self.check_cb(field)))
        rb_dss_secondary.grid(row=1, column=1, sticky=tk.W)
        self.checkboxvar['Enable Hotkeys'] = tk.BooleanVar()
        cb_enable = ttk.Checkbutton(blk_buttons, text='Enable Hotkeys (toggle after hotkey change)', variable=self.checkboxvar['Enable Hotkeys'], command=(lambda field='Enable Hotkeys': self.check_cb(field)))
        cb_enable.grid(row=2, column=0, columnspan=2, sticky=tk.W)
        self.entries['buttons'] = self.makeform(blk_buttons, FORM_TYPE_ENTRY, buttons_entry_fields, 3)

        # refuel settings block
        blk_fuel = ttk.LabelFrame(blk_settings, text="FUEL", padding=(10, 5))
        blk_fuel.grid(row=1, column=0, padx=2, pady=2, sticky="NSEW")
        self.entries['refuel'] = self.makeform(blk_fuel, FORM_TYPE_SPINBOX, refuel_entry_fields)

        # Keys settings block
        blk_keys = ttk.LabelFrame(blk_settings, text="KEYS", padding=(10, 5))
        blk_keys.grid(row=2, column=0, padx=2, pady=2, sticky="NSEW")
        self.checkboxvar['Activate Elite for each key'] = tk.BooleanVar()
        cb_activate_elite = ttk.Checkbutton(blk_keys, text='Activate Elite for each key', variable=self.checkboxvar['Activate Elite for each key'], command=(lambda field='Activate Elite for each key': self.check_cb(field)))
        cb_activate_elite.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        self.entries['keys'] = self.makeform(blk_keys, FORM_TYPE_SPINBOX, keys_entry_fields, 1, 0.01)

        # ship settings block
        blk_ship = ttk.LabelFrame(blk_settings, text="SHIP", padding=(10, 5))
        blk_ship.grid(row=2, column=1, padx=2, pady=2, sticky="NSEW")
        self.entries['ship'] = self.makeform(blk_ship, FORM_TYPE_SPINBOX, ship_entry_fields, 1, 0.5)

        lbl_sun_pitch_up = ttk.Label(blk_ship, text='SunPitchUp +/- Time:')
        lbl_sun_pitch_up.grid(row=5, column=0, pady=3, sticky=tk.W)
        spn_sun_pitch_up = ttk.Spinbox(blk_ship, width=10, from_=-100, to=100, increment=0.5, justify=tk.RIGHT)
        spn_sun_pitch_up.grid(row=5, column=1, padx=2, pady=2, sticky=tk.E)
        spn_sun_pitch_up.bind('<FocusOut>', self.entry_update)
        self.entries['ship']['SunPitchUp+Time'] = spn_sun_pitch_up

        btn_tst_pitch = ttk.Button(blk_ship, text='Calibrate Pitch Rate', command=self.ship_tst_pitch)
        btn_tst_pitch.grid(row=6, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")
        btn_tst_yaw = ttk.Button(blk_ship, text='Calibrate Yaw Rate', command=self.ship_tst_yaw)
        btn_tst_yaw.grid(row=7, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")

        # settings button block
        blk_settings_buttons = ttk.Frame(page1)
        blk_settings_buttons.grid(row=5, column=0, padx=10, pady=5, sticky="NSEW")
        blk_settings_buttons.columnconfigure([0, 1], weight=1, minsize=100)
        btn_save = ttk.Button(blk_settings_buttons, text='Save All Settings', command=self.save_settings, style="Accent.TButton")
        btn_save.grid(row=0, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")

        # === LOGGING & DEBUG (on Settings tab) ===
        blk_logging = ttk.LabelFrame(page1, text="LOGGING", padding=(10, 5))
        blk_logging.grid(row=6, column=0, padx=10, pady=5, sticky="NSEW")
        blk_logging.columnconfigure([0, 1], weight=1, minsize=100)

        self.radiobuttonvar['debug_mode'] = tk.StringVar()
        rb_debug_debug = ttk.Radiobutton(blk_logging, text="Debug + Info + Errors", variable=self.radiobuttonvar['debug_mode'], value="Debug", command=(lambda field='debug_mode': self.check_cb(field)))
        rb_debug_debug.grid(row=0, column=0, sticky=tk.W)
        rb_debug_info = ttk.Radiobutton(blk_logging, text="Info + Errors", variable=self.radiobuttonvar['debug_mode'], value="Info", command=(lambda field='debug_mode': self.check_cb(field)))
        rb_debug_info.grid(row=1, column=0, sticky=tk.W)
        rb_debug_error = ttk.Radiobutton(blk_logging, text="Errors only (default)", variable=self.radiobuttonvar['debug_mode'], value="Error", command=(lambda field='debug_mode': self.check_cb(field)))
        rb_debug_error.grid(row=2, column=0, sticky=tk.W)
        btn_open_logfile = ttk.Button(blk_logging, text='Open Log File', command=self.open_logfile)
        btn_open_logfile.grid(row=3, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")

        self.checkboxvar['Debug Images'] = tk.BooleanVar()
        cb_debug_images = ttk.Checkbutton(blk_logging, text='Debug Images', variable=self.checkboxvar['Debug Images'], command=(lambda field='Debug Images': self.check_cb(field)))
        cb_debug_images.grid(row=5, column=0, padx=2, pady=2, sticky=tk.W)
        tip = ToolTip(cb_debug_images, msg=self.tooltips['Debug Images'], delay=1.0, bg="#808080", fg="#FFFFFF")

        # === HELP & APP (on Settings tab) ===
        blk_app = ttk.LabelFrame(page1, text="APPLICATION", padding=(10, 5))
        blk_app.grid(row=7, column=0, padx=10, pady=5, sticky="NSEW")
        blk_app.columnconfigure([0, 1], weight=1, minsize=100)

        btn_check_updates = ttk.Button(blk_app, text="Check for Updates", command=self.check_updates)
        btn_check_updates.grid(row=0, column=0, padx=2, pady=2, sticky="NSEW")
        btn_about = ttk.Button(blk_app, text="About", command=self.about)
        btn_about.grid(row=0, column=1, padx=2, pady=2, sticky="NSEW")
        btn_view_changelog = ttk.Button(blk_app, text="View Changelog", command=self.open_changelog)
        btn_view_changelog.grid(row=1, column=0, padx=2, pady=2, sticky="NSEW")
        btn_join_discord = ttk.Button(blk_app, text="Join Discord", command=self.open_discord)
        btn_join_discord.grid(row=1, column=1, padx=2, pady=2, sticky="NSEW")
        btn_restart = ttk.Button(blk_app, text="Restart", command=self.restart_program)
        btn_restart.grid(row=2, column=0, padx=2, pady=2, sticky="NSEW")
        btn_exit = ttk.Button(blk_app, text="Exit", command=self.close_window)
        btn_exit.grid(row=2, column=1, padx=2, pady=2, sticky="NSEW")

        # === Status Bar ===
        statusbar = ttk.Frame(win)
        statusbar.grid(row=2, column=0, sticky="EW")
        self.status = ttk.Label(win, text="Status: ", relief=tk.SUNKEN, anchor=tk.W, justify=tk.LEFT, width=29)
        self.jumpcount = ttk.Label(statusbar, text="<info> ", relief=tk.SUNKEN, anchor=tk.W, justify=tk.LEFT, width=40)
        self.status.pack(in_=statusbar, side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.jumpcount.pack(in_=statusbar, side=tk.RIGHT, fill=tk.Y, expand=False)

        return mylist

    def restart_program(self):
        logger.debug("Entered: restart_program")
        logger.info("restart now")

        self.stop_all_assists()
        self.ed_ap.quit()
        sleep(0.1)

        import sys
        logger.debug("argv was %s", sys.argv)
        logger.debug("sys.executable was %s", sys.executable)
        logger.info("restart now")

        import os
        os.execv(sys.executable, ['python'] + sys.argv)


def apply_theme_to_titlebar(root):
    version = sys.getwindowsversion()

    if version.major == 10 and version.build >= 22000:
        # Set the title bar color to the background color on Windows 11 for better appearance
        pywinstyles.change_header_color(root, "#1c1c1c" if sv_ttk.get_theme() == "dark" else "#fafafa")
    elif version.major == 10:
        pywinstyles.apply_style(root, "dark" if sv_ttk.get_theme() == "dark" else "normal")

        # A hacky way to update the title bar's color on Windows 10 (it doesn't update instantly like on Windows 11)
        root.wm_attributes("-alpha", 0.99)
        root.wm_attributes("-alpha", 1)


def main():
    #   handle = win32gui.FindWindow(0, "Elite - Dangerous (CLIENT)")
    #   if handle != None:
    #       win32gui.SetForegroundWindow(handle)  # put the window in foreground

    root = tk.Tk()
    app = APGui(root)

    sv_ttk.set_theme("dark")

    # Remove focus outline from tabs by setting focuscolor to the background color
    style = ttk.Style()
    bg_color = "#1c1c1c" if sv_ttk.get_theme() == "dark" else "#fafafa"
    style.configure("TNotebook.Tab", focuscolor=bg_color)

    # if sys.platform == "win32":
    #     apply_theme_to_titlebar(root)

    root.mainloop()


if __name__ == "__main__":
    main()
