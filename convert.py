import os
from os import path
from configparser import ConfigParser
import hashlib
import json
import logging
import shutil
import zipfile
logger = logging.getLogger()

def convert(char_dir, base_dir, temp_dir, target_dir, progress=lambda x: None, strip=False):
    char_name = path.basename(char_dir)
    logger.info("-- Conversion started for {}".format(char_name))
    progress(5)
    logger.debug("Reading char.ini")
    with open(path.join(char_dir, "char.ini")) as f:
        char_ini = ConfigParser(comment_prefixes=("#", ";", "//"), strict=False)
        char_ini.read_string(f.read())
    info = {
        "name": char_ini["Options"]["name"],
        "side": char_ini["Options"]["side"],
        # icon: Note that this may not work well with AO1.
        # AO1 uses DemoThings files which are buried in misc.
        "icon": "char_icon.png",
        "blip": "blip.wav",
        "emotes": [],
        "preanims": {},
        "objection_override": {},
        "files": []
    }

    # Try to use friendly name instead of internal name (AO2)
    try:
        info["name"] = char_ini["Options"]["showname"]
    except KeyError:
        pass

    # Copy all files to temp dir
    logger.debug("Scanning original files")
    progress(10)

    for root, dirs, files in os.walk(char_dir):
        for name in files:
            full_path = path.join(root, name)
            if not path.isfile(full_path):
                continue

            filename = path.join(path.relpath(root, char_dir), name)
            filename = filename.replace("\\", "/")

            # KILL THE DOT FOLDER WITH FIRE
            if filename[:2] == "./":
                filename = filename[2:]

            # Find some of the interjection WAV files.
            # Surprisingly enough, some characters use
            # capital letters in the filenames.
            lowercase = filename.lower()
            if lowercase == "holdit.wav":
                info["objection_override"]["hold_it"] = filename
            elif lowercase == "objection.wav":
                info["objection_override"]["objection"] = filename
            elif lowercase == "takethat.wav":
                info["objection_override"]["take_that"] = filename
            elif lowercase == "custom.wav":
                info["objection_override"]["custom"] = filename
            info["files"].append(filename)
            logger.debug(filename)

    # Copy extra files
    # extra_files: array of tuples containing filename and source path
    extra_files = []
    logger.debug("Getting blip sound effect")
    progress(18)
    try:
        blip_sfx = "sfx-blip" + char_ini["Options"]["gender"] + ".wav"
    except KeyError:
        # Sorry for assuming gender.. but there is no "generic" blip!
        blip_sfx = "sfx-blipmale.wav"
    extra_files.append(("blip.wav", path.join(base_dir, "sounds", "general", blip_sfx)))

    logger.debug("Converting emotes")
    progress(20)
    # Find case-insensitive emotions folder
    emotions_folder = [d for d in os.listdir(
        char_dir) if d.lower() == "emotions"][0]

    # Go through all emotes and find preanimations
    preanims = info["preanims"]
    for i in range(1, int(char_ini["Emotions"]["number"]) + 1):
        emote_raw = char_ini["Emotions"][str(i)].split("#")
        emote = {
            "name": emote_raw[0],
            "icon": "{}/button{}_on.png".format(emotions_folder, i),
            # This also covers the case where the (a) and (b) emotes are
            # placed in different folders using the `/` trick.
            "idle": "(a){}.gif".format(emote_raw[2]),
            "talking": "(b){}.gif".format(emote_raw[2]),
        }
        if emote_raw[3] == 5:
            emote["zoom"] = True
        
        # Check if a preanim exists
        preanim_name = emote_raw[1]
        if preanim_name not in ("-", "normal"):
            emote["talking_preanim"] = preanim_name

            # Check if it is already on the list
            if preanim_name not in preanims:
                preanim = {
                    "anim": "{}.gif".format(preanim_name)
                }
                try:
                    preanim["duration"] = int(char_ini["Time"][preanim_name]) * 60
                except KeyError:
                    pass

                # Check if this emote has a sound effect, and add it to the preanim
                sfx_name = char_ini["SoundN"][str(i)]
                if len(sfx_name) > 1:
                    sfx_file = "{}.wav".format(sfx_name)
                    preanim["sfx"] = {
                        "file": sfx_file,
                        # 1 tick = 60 ms
                        "delay": int(char_ini["SoundT"][str(i)]) * 60
                    }

                    # Copy sound effect
                    logger.debug("Copying sound effect {}".format(sfx_file))
                    extra_files.append((sfx_file, path.join(base_dir, "sounds", "general", sfx_file)))

                preanims[preanim_name] = preanim
        info["emotes"].append(emote)

    logger.debug("Writing info.json")
    progress(25)

    info_path = path.join(temp_dir, "info.json")
    extra_files.append(("info.json", info_path))

    # Finalize file list
    all_files = [(f, path.join(char_dir, f)) for f in info["files"]]
    for fp in extra_files:
        info["files"].append(fp[0])
        all_files.append(fp)
    all_files = set(all_files)

    with open(info_path, "w") as f:
        json.dump(info, f)

    logger.debug("Scanning files and creating content archive")
    progress(30)
    zip_path = path.join(temp_dir, "content.zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.comment = b"Auto-generated by fantaconvert"
        cur_progress, max_progress = 0, len(all_files)
        for filename, full_path in all_files:
            with open(full_path, "rb") as f:
                archive.write(full_path, arcname=filename)
            cur_progress += 1
            progress(int(30 + (cur_progress / max_progress) * 55))

    logger.debug("Calculating hash")
    progress(85)

    with open(zip_path, "rb") as f:
        hash = hashlib.sha1()
        hash.update(f.read())
        hash_str = hash.hexdigest()
    logger.info("SHA-1: {}".format(hash_str))
    os.rename(zip_path, path.join(temp_dir, hash_str + ".zip"))
    zip_path = path.join(temp_dir, hash_str + ".zip")

    logger.debug("Copying files")
    progress(95)
    shutil.move(zip_path, target_dir)

    logger.info("-- Conversion complete for {}".format(char_name))
    progress(100)
