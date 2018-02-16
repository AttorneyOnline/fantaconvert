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
    logger.info("Conversion started")
    logger.info("Reading char.ini")
    with open(path.join(char_dir, "char.ini")) as f:
        char_ini = ConfigParser()
        char_ini.read_string(f.read())
    info = {
        # showname: AO2 only
        "name": char_ini["Options"]["showname"] or char_ini["Options"]["name"],
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

    # Copy all files to temp dir
    logger.info("Copying original files")
    temp_char_dir = path.join(temp_dir, "content")
    shutil.copytree(char_dir, temp_char_dir)

    # Copy extra files
    logger.info("Copying blip sound effect")
    blip_sfx = "sfx-blip" + char_ini["Options"]["gender"] + ".wav"
    shutil.copy2(path.join(base_dir, "sounds", "general", blip_sfx),
                 path.join(temp_char_dir, "blip.wav"))

    logger.info("Converting emotes")
    preanims = info["preanims"]
    for i in range(1, int(char_ini["Emotions"]["number"]) + 1):
        emote_raw = char_ini["Emotions"][str(i)].split("#")
        emote = {
            "name": emote_raw[0],
            "icon": "emotions/button{}_on.png".format(i),
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

    logger.info("Scanning files")
    for root, dirs, files in os.walk(temp_char_dir):
        for filename in files:
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

    logger.info("Creating content.tar")
    shutil.make_archive(path.join(temp_dir, "content"), "tar",
                        root_dir=temp_char_dir, logger=logger)
    
    logger.info("Removing content folder")
    shutil.rmtree(temp_char_dir)

    logger.info("Computing crc32 of content.tar")
    with open(path.join(temp_dir, "content.tar"), "rb") as f:
        hash = binascii.crc32(f.read())
        hash_str = "{:08x}".format(hash)
        info["hash"] = "crc32:{}".format(hash_str)

    logger.info("Writing info.json")
    with open(path.join(temp_dir, "info.json"), "w") as f:
        json.dump(info, f)

    logger.info("Copying files")
    shutil.copytree(temp_dir, path.join(target_dir, hash_str))

    logger.info("Conversion complete!")
