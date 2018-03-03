import os
from os import path
from configparser import ConfigParser
import datetime
import hashlib
import json
import logging
import shutil
import zipfile
logger = logging.getLogger()


def convert_char(char_dir, base_dir, temp_dir, target_dir, progress=lambda x: None,
                 standard_base_file="standard_base.json", author=None):
    """
    Convert an AO1 character to a JSON-based format.

    :param char_dir: the directory where char.ini resides
    :param base_dir: the directory where the AO installation folder resides
    :param temp_dir: a directory that may be used for temporary usage
    :param target_dir: the directory where the contents of temp_dir will be copied to
    :param progress: a function that reports progress to a UI
    """
    char_name = path.basename(char_dir)
    logger.debug("-- Conversion started for {}".format(char_name))
    progress(5)
    logger.debug("Reading char.ini")
    with open(path.join(char_dir, "char.ini")) as f:
        char_ini = ConfigParser(comment_prefixes=("#", ";", "//", "\\\\"), strict=False)
        char_ini.read_string(f.read())

    # Case-insensitive ini sections
    sections = ["Options", "Time", "Emotions", "SoundN", "SoundT"]
    for section in sections:
        section_lower = section.lower()
        if section not in char_ini and section_lower in char_ini:
            char_ini[section] = char_ini[section_lower]

    # Load in the standard base manifest.
    # This will help us determine if we need to copy in the sfx or not.
    # This manifest is special because it lists out the files
    # and their hashes, whereas normal manifests do not have this listing.
    with open(standard_base_file) as f:
        standard_base = json.load(f)

    # Contains a dictionary of files mapped to their SHA-1 hashes
    parent_files = standard_base["files"]

    files_list = []
    info = {
        "parent": standard_base["id"],
        "name": char_ini["Options"]["name"],
        "category": "character",
        "meta": {
            "author": author,
            "desc": "Imported using fantaconvert",
            "date": datetime.datetime.utcnow().astimezone().isoformat()
        },
        "side": char_ini["Options"]["side"],
        # icon: Note that this may not work well with AO1.
        # AO1 uses DemoThings files which are buried in misc.
        "icon": "char_icon.png",
        "emotes": [],
        "preanims": {},
        "interjections": []
    }

    # Try to use friendly name instead of internal name (AO2)
    try:
        info["chatbox_name"] = char_ini["Options"]["showname"]
    except KeyError:
        pass

    # Copy all files to temp dir
    logger.debug("Scanning original files")
    progress(10)

    # Scan all files
    for root, _dirs, files in os.walk(char_dir):
        for name in files:
            full_path = path.join(root, name)
            if not path.isfile(full_path):
                continue

            filename = path.join(path.relpath(root, char_dir), name)
            filename = filename.replace("\\", "/")

            # KILL THE DOT FOLDER WITH FIRE
            if filename[:2] == "./":
                filename = filename[2:]

            files_list.append(filename)
            logger.debug(filename)

    # Find some of the interjection WAV files.
    # Surprisingly enough, some characters use
    # capital letters in the filenames.
    files_insensitive = {x.lower(): x for x in files_list}
    interjections = [
        ("holdit", "Hold it!"),
        ("objection", "Objection!"),
        ("takethat", "Take that!"),
        ("custom", "Custom")
    ]
    for f, n in interjections:
        wav = f + ".wav"
        if wav in files_insensitive:
            info["interjections"].append({
                "name": n,
                "sound": files_insensitive[wav],
                "anim": (f + ".gif", f + "_bubble.gif")
                        [f + "_bubble.gif" in files_insensitive]
            })
            # Do not copy interjection sound if it is the generic one found
            # in the standard base
            if wav in parent_files:
                with open(path.join(char_dir, wav), "rb") as sound:
                    file_hash = hashlib.sha1()
                    file_hash.update(sound.read())
                if file_hash.hexdigest() == parent_files[wav]:
                    files_list.remove(wav)

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
    
    # Case 1: file exists in character folder.
    #   Do nothing - it will be copied in (I won't bother checking the hash)
    # Case 2: file exists in parent (standard base).
    #   Do nothing - it does not need to be copied
    #   (Here, though, I'll add a prefix to keep things tidy)
    # Case 3: file does not exist in parent (standard base) or in character folder
    #   Copy it in - if it doesn't exist in installation folder,
    #   we expect an error to occur
    def add_sfx(sfx_file):
        if sfx_file in files_list:
            pass
        elif "sfx/" + sfx_file in parent_files:
            sfx_file = "sfx/" + sfx_file
        else:
            extra_files.append(
                (sfx_file, path.join(base_dir, "sounds", "general", sfx_file))
            )
        return sfx_file

    info["blip"] = add_sfx(blip_sfx)

    logger.debug("Converting emotes")
    progress(20)
    # Find case-insensitive emotions folder
    emotions_folder = [d for d in os.listdir(
        char_dir) if d.lower() == "emotions"][0]

    # Go through all emotes and find preanimations
    preanims = info["preanims"]
    for i in range(1, int(char_ini["Emotions"]["number"]) + 1):
        try:
            emote_raw = char_ini["Emotions"][str(i)].split("#")
        except KeyError:
            raise KeyError("{}: char.ini error: could not find emote #{}"
                           .format(char_name, i))
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

            # Check if preanim is already on the list
            if preanim_name not in preanims:
                preanim = {
                    "anim": "{}.gif".format(preanim_name)
                }
                try:
                    preanim["duration"] = int(char_ini["Time"][preanim_name]) * 60
                except KeyError:
                    pass

                # Check if this emote has a sound effect, and add it to the preanim
                try:
                    sfx_name = char_ini["SoundN"][str(i)]
                except KeyError:
                    logger.warning("{}: char.ini warning: could not find SoundN for emote #{}"
                                   .format(char_name, i))
                    sfx_name = ""

                if len(sfx_name) > 1:
                    sfx_file = add_sfx("{}.wav".format(sfx_name))
                    preanim["sfx"] = {
                        "file": sfx_file
                    }
                    try:
                        # 1 tick = 60 ms
                        preanim["sfx"]["delay"] = int(char_ini["SoundT"][str(i)]) * 60
                    except KeyError:
                        logger.warning("{}: char.ini warning: could not find SoundT for emote #{}"
                                       .format(char_name, i))
                        preanim["sfx"]["delay"] = 0

                    # Copy sound effect
                    logger.debug("Copying sound effect {}".format(sfx_file))

                preanims[preanim_name] = preanim
        info["emotes"].append(emote)

    logger.debug("Writing info.json")
    progress(25)

    info_path = path.join(temp_dir, "info.json")
    extra_files.append(("info.json", info_path))

    # Finalize file list
    all_files = [(f, path.join(char_dir, f)) for f in files_list]
    for fp in extra_files:
        files_list.append(fp[0])
        all_files.append(fp)
    all_files = set(all_files)

    with open(info_path, "w") as f:
        json.dump(info, f)

    logger.debug("Hashing files and creating content archive")
    progress(30)

    zip_path = path.join(temp_dir, "content.zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.comment = b"Auto-generated by fantaconvert"
        cur_progress, max_progress = 0, len(all_files)
        for filename, full_path in all_files:
            with open(full_path, "rb") as f:
                pass
            archive.write(full_path, arcname=filename)
            cur_progress += 1
            progress(int(30 + (cur_progress / max_progress) * 55))

    logger.debug("Calculating canonical hash")
    progress(85)

    final_hash = hashlib.sha1()
    with open(zip_path, "rb") as f:
        final_hash.update(f.read())
    hash_str = final_hash.hexdigest()

    os.rename(zip_path, path.join(temp_dir, hash_str + ".zip"))
    zip_path = path.join(temp_dir, hash_str + ".zip")

    logger.debug("Copying final archive")
    progress(95)
    shutil.move(zip_path, target_dir)

    logger.info("-- Conversion complete for {}".format(char_name))
    logger.info("   SHA-1: {}".format(hash_str))
    progress(100)
