import os
from os import path
import logging
from configparser import ConfigParser
import tempfile

import tkinter as tk
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
    def __init__(self):
        self.builder = builder = pygubu.Builder()
        builder.add_from_file("fantaconvert.ui")
        self.main_window = builder.get_object("Toplevel")
        builder.connect_callbacks({
            "browse_chardir": self.browse_chardir,
            "browse_basedir": self.browse_basedir,
            "convert": self.start_convert,
            "convert_all": self.start_convert_all
        })
        logger.addHandler(LoggerWidget(builder.get_object("txt_log")))
        self.char_dir = ""
        self.base_dir = ""

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
                char_ini = ConfigParser()
                char_ini.read_string(f.read())
                logger.info("Found char.ini for character {}.".format(
                    char_ini["Options"]["name"]))
        except (OSError, KeyError) as e:
            logger.error(e)
            return False

        logger.info("Ready to convert.")
        self.builder.get_object("btn_convert").config(state=tk.NORMAL)
        self.builder.get_object("btn_convert_all").config(state=tk.NORMAL)
        return True

    def start_convert(self):
        btn_convert = self.builder.get_object("btn_convert")
        btn_convert_all = self.builder.get_object("btn_convert_all")
        btn_convert.config(state=tk.DISABLED)
        btn_convert_all.config(state=tk.DISABLED)
        assets_dir = path.join(os.getcwd(), "assets")
        try:
            # Create temporary directory to work in containing our asset
            with tempfile.TemporaryDirectory(prefix="fantaconvert") as temp_dir:
                convert(self.char_dir, self.base_dir, temp_dir, assets_dir)
        except Exception as e:
            logger.error("-- A conversion error occurred!")
            logger.error(e, exc_info=True)
        btn_convert.config(state=tk.NORMAL)
        btn_convert_all.config(state=tk.NORMAL)

    def start_convert_all(self):
        btn_convert = self.builder.get_object("btn_convert")
        btn_convert_all = self.builder.get_object("btn_convert_all")
        btn_convert.config(state=tk.DISABLED)
        btn_convert_all.config(state=tk.DISABLED)
        assets_dir = path.join(os.getcwd(), "assets")
        chars_dir = path.dirname(self.char_dir)
        for char_dir in os.listdir(chars_dir):
            try:
                # Create temporary directory to work in containing our asset
                with tempfile.TemporaryDirectory(prefix="fantaconvert") as temp_dir:
                    convert(path.join(chars_dir, char_dir),
                            self.base_dir, temp_dir, assets_dir)
            except Exception as e:
                logger.error("-- A conversion error occurred!")
                logger.error(e, exc_info=True)
        btn_convert.config(state=tk.NORMAL)
        btn_convert_all.config(state=tk.NORMAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = FantaConvertUI()
    app.run()
