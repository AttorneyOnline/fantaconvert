import os
from os import path
from configparser import ConfigParser
import binascii
import json
import logging
import shutil
import tarfile
logger = logging.getLogger()

def convert(char_dir, base_dir, temp_dir, target_dir):
    logger.info("-- Conversion started for {}".format(path.basename(char_dir)))
    logger.debug("Reading char.ini")
    with open(path.join(char_dir, "char.ini")) as f:
        char_ini = ConfigParser()
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
    logger.debug("Copying original files")
    temp_char_dir = path.join(temp_dir, "content")
    shutil.copytree(char_dir, temp_char_dir)

    # Copy extra files
    logger.debug("Copying blip sound effect")
    try:
        blip_sfx = "sfx-blip" + char_ini["Options"]["gender"] + ".wav"
    except KeyError:
        # Sorry for assuming gender.. but there is no "generic" blip!
        blip_sfx = "sfx-blipmale.wav"
    shutil.copy2(path.join(base_dir, "sounds", "general", blip_sfx),
                 path.join(temp_char_dir, "blip.wav"))

    logger.debug("Converting emotes")
    # Find case-insensitive emotions folder
    emotions_folder = [d for d in os.listdir(
        temp_char_dir) if d.lower() == "emotions"][0]

    # Go through all emotes and find preanimations
    preanims = info["preanims"]
    for i in range(1, int(char_ini["Emotions"]["number"]) + 1):
        emote_raw = char_ini["Emotions"][str(i)].split("#")
        emote = {
            "name": emote_raw[0],
            "icon": "{}/button{}_on.png".format(emotions_folder, i),
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
                    "anim": "{}.gif".format(preanim_name),
                    "duration": int(char_ini["Time"][preanim_name]) * 60
                }

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
                    logger.info("Copying sound effect {}".format(sfx_file))
                    shutil.copy2(path.join(base_dir, "sounds", "general", sfx_file),
                                 path.join(temp_char_dir, sfx_file))

                preanims[preanim_name] = preanim
        info["emotes"].append(emote)

    logger.debug("Scanning files and creating content.tar")
    with tarfile.open(path.join(temp_dir, "content.tar"), "w") as tar:
        for root, dirs, files in os.walk(temp_char_dir):
            for name in files:
                filename = path.join(path.relpath(root, temp_char_dir), name)
                filename.replace("\\", "/")

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
                logger.debug(f"{filename}")
                full_path = path.join(temp_char_dir, filename)
                i = tar.gettarinfo(full_path, arcname=filename)
                i.uid = i.gid = 0
                i.uname = i.gname = ""
                if i.isreg():
                    with open(full_path, "rb") as f:
                        tar.addfile(i, fileobj=f)
                else:
                    tar.addfile(i)

    #with tarfile.open(path.join(temp_dir, "content.tar"), "w") as tar:
    #    tar.add(temp_char_dir, arcname=path.sep)
    # shutil.make_archive(path.join(temp_dir, "content"), "tar",
    #                     root_dir=temp_char_dir, logger=logger)
    
    logger.debug("Removing content folder")
    shutil.rmtree(temp_char_dir)

    with open(path.join(temp_dir, "content.tar"), "rb") as f:
        hash = binascii.crc32(f.read())
        hash_str = "{:08x}".format(hash)
        info["hash"] = "crc32:{}".format(hash_str)
    logger.info("CRC32: {}".format(hash_str))

    logger.debug("Writing info.json")
    with open(path.join(temp_dir, "info.json"), "w") as f:
        json.dump(info, f)

    logger.debug("Copying files")
    shutil.copytree(temp_dir, path.join(target_dir, hash_str))

    logger.info("-- Conversion complete!")
