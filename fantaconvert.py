import asyncio
import concurrent
import threading

import os
from os import path

import logging

import heapq
import tempfile

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
import pygubu

from convert import convert

logger = logging.getLogger()

class LoggerWidget(logging.Handler):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def emit(self, record):
        self.widget.insert(tk.INSERT, str(record.msg) + "\n")
        self.widget.see(tk.END)


class FantaConvertUI:
    def __init__(self, loop):
        self.loop = loop
        self.builder = builder = pygubu.Builder()
        builder.add_from_file("fantaconvert.ui")
        self.main_window = builder.get_object("Toplevel")
        builder.connect_callbacks({
            "browse_chardir": self.browse_chardir,
            "browse_basedir": self.browse_basedir,
            "convert": self.start_convert,
            "convert_all": self.start_convert_all,
            "cancel": self.cancel_convert
        })
        logger.addHandler(LoggerWidget(builder.get_object("txt_log")))
        self.char_dir = ""
        self.base_dir = ""
        self.assets_dir = path.join(os.getcwd(), "assets")
        self.tasks = None

    def run(self):
        self.main_window.mainloop()

    def quit(self, event=None):
        self.main_window.quit()

    @property
    def char_dir(self):
        return self._char_dir

    @char_dir.setter
    def char_dir(self, dir):
        self._char_dir = dir
        entry = self.builder.get_object("entry_chardir")
        entry.delete(0, tk.END)
        entry.insert(0, dir)

    @property
    def base_dir(self):
        return self._base_dir

    @base_dir.setter
    def base_dir(self, dir):
        self._base_dir = dir
        entry = self.builder.get_object("entry_basedir")
        entry.delete(0, tk.END)
        entry.insert(0, dir)

    def browse_chardir(self):
        dir = filedialog.askdirectory(parent=self.main_window)
        if dir == "":
            return
        self.char_dir = dir
        base = self.find_base(dir)
        if base:
            self.base_dir = base
        self.validate()

    def browse_basedir(self):
        dir = filedialog.askdirectory(parent=self.main_window)
        if dir == "":
            return
        self.base_dir = dir
        self.validate()

    def find_base(self, dir):
        base = path.dirname(path.dirname(dir))
        return base if path.exists(path.join(base, "sounds")) else False

    def validate(self):
        if "" in (self.char_dir, self.base_dir):
            return False
        try:
            with open(path.join(self.char_dir, "char.ini")) as f:
                logger.info("Found char.ini for character {}.".format(
                    path.basename(self.char_dir)))
        except (OSError, KeyError) as e:
            logger.error(e)
            return False

        logger.info("Ready to convert.")
        self.builder.get_object("btn_convert").config(state=tk.NORMAL)
        self.builder.get_object("btn_convert_all").config(state=tk.NORMAL)
        return True

    def enable_buttons(self):
        btn_convert = self.builder.get_object("btn_convert")
        btn_convert_all = self.builder.get_object("btn_convert_all")
        btn_convert.config(state=tk.NORMAL)
        btn_convert_all.config(state=tk.NORMAL)

    def disable_buttons(self):
        btn_convert = self.builder.get_object("btn_convert")
        btn_convert_all = self.builder.get_object("btn_convert_all")
        btn_convert.config(state=tk.DISABLED)
        btn_convert_all.config(state=tk.DISABLED)

    def start_convert(self):
        self.disable_buttons()
        self.show_progress()
        def do_convert():
            self.convert_character(self.char_dir)
            self.hide_progress()
            self.enable_buttons()
        threading.Thread(target=do_convert).start()

    def show_progress(self):
        self.progress = progress = ttk.Labelframe(self.main_window)
        progress["text"] = "Progress"
        progress.grid(row=7, column=0, sticky=tk.EW, columnspan=2)
        progress.grid_columnconfigure(0, weight=1, pad=4)
        self.progress_bars = []
        # Heap of rows. The unused lowest row is always used.
        self.progress_bar_rows = [x for x in range(1, 4)]
        heapq.heapify(self.progress_bar_rows)

    def hide_progress(self):
        self.progress.grid_remove()
        del self.progress
        del self.progress_bars

    def add_progress_bar(self):
        progress_bar = ttk.Progressbar(self.progress)
        row = heapq.heappop(self.progress_bar_rows)
        progress_bar.grid(row=row, column=0, sticky=tk.EW)
        progress_bar.row = row
        self.progress_bars.append(progress_bar)
        return progress_bar

    def remove_progress_bar(self, progress_bar):
        heapq.heappush(self.progress_bar_rows, progress_bar.row)
        progress_bar.grid_remove()
        self.progress_bars.remove(progress_bar)

    def cancel_convert(self):
        self.builder.get_object("btn_cancel").config(state=tk.DISABLED)
        if self.tasks is not None:
            self.tasks.cancel()

    def start_convert_all(self):
        self.disable_buttons()
        self.builder.get_object("btn_cancel").config(state=tk.NORMAL)
        self.show_progress()
        chars_dir = path.dirname(self.char_dir)
        def do_convert_all():
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                tasks = [
                    self.loop.run_in_executor(
                        executor, self.convert_character, path.join(chars_dir, char_dir))
                    for char_dir in os.listdir(chars_dir)
                ]
                self.tasks = asyncio.gather(*tasks)
                try:
                    self.loop.run_until_complete(self.tasks)
                except concurrent.futures.CancelledError:
                    logger.warn("Canceling!")
            self.enable_buttons()
            self.builder.get_object("btn_cancel").config(state=tk.DISABLED)
            self.hide_progress()
        threading.Thread(target=do_convert_all).start()

    def convert_character(self, char_dir):
        progress = self.add_progress_bar()
        try:
            def set_progress(x):
                progress["value"] = x

            # Create temporary directory to work in containing our asset
            with tempfile.TemporaryDirectory(prefix="fantaconvert") as temp_dir:
                convert(char_dir, self.base_dir, temp_dir,
                        self.assets_dir, progress=set_progress)
        except Exception as e:
            logger.error(
                "-- A conversion error occurred for {}".format(path.basename(char_dir)))
            logger.error(e, exc_info=True)
        finally:
            self.remove_progress_bar(progress)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    app = FantaConvertUI(loop)
    app.run()
