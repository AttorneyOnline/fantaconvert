import os, sys, glob, cx_Freeze

os.environ['TCL_LIBRARY'] = os.path.join(sys.exec_prefix, 'tcl', 'tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(sys.exec_prefix, 'tcl', 'tk8.6')

executables = [cx_Freeze.Executable("fantaconvert.py", targetName="fantaconvert.exe")]

cx_Freeze.setup(
    name="fantaconvert",
    version="1.0",
    options={"build_exe": {
        "optimize": 2,
        #"compressed": True,
        "include_msvcr": True,
        "packages": ["pygubu", "tkinter", "asyncio"],
        #"include_files": glob.glob("res/*.*")
        "include_files": [
            os.path.join(sys.exec_prefix, 'DLLs', 'tk86t.dll'),
            os.path.join(sys.exec_prefix, 'DLLs', 'tcl86t.dll'),
            "fantaconvert.ui",
            "standard_base.json",
            "README.md",
            "LICENSE"
        ],
        "zip_include_packages": "*",
        "zip_exclude_packages": "",
    }
    },
    executables=executables)
