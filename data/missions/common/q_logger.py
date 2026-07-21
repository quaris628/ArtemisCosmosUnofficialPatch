import atexit
from datetime import datetime
import faulthandler
import os
from pathlib import Path
from time import time

from sbs_utils.fs import get_mission_name
from sbs_utils.procedural.execution import logger, log
from sbs_utils.procedural.query import to_space_object, to_grid_object

# ----- constants -----

# Log levels can't be an enum b/c enums aren't accessible in mast

# Problem. The sim cannot possibly continue
def qlog_level_critical():
    return 5

# Problem. The sim can continue
def qlog_level_error():
    return 4

# Likely or potential problem. The sim can continue
def qlog_level_warn():
    return 3

# Not a problem
def qlog_level_info():
    return 2

# Very small details for targeted bug investigations
def qlog_level_debug():
    return 1

def qlog_get_level_abbrev(level):
    return {
        5: "CRIT",
        4: "ERRO",
        3: "WARN",
        2: "INFO",
        1: "DEBG",
    }[level]

# Only information at or above this level will be logged
_QLOG_LOWEST_LEVEL = qlog_level_info()

# ----- public -----

def initialize_qlog():
    # Working directory for this is where the artemis cosmos exe is
    if not os.path.exists(_qlog_get_logs_folder_filepath_relative_to_artemis_cosmos_folder()):
        os.makedirs(_qlog_get_logs_folder_filepath_relative_to_artemis_cosmos_folder())
    # Working directory for this is the currently-running-mission's folder
    logger(name=_QLOG_LOGGER_NAME, file=_qlog_get_new_log_filepath_relative_to_mission_folder())
    # for determining when the log is old enough to be automatically deleted
    log(message=str(time()), name=_QLOG_LOGGER_NAME)
    _qlog_delete_old_logs()
    
    hard_crash_stack_trace_filepath = _qlog_get_hard_crash_stack_trace_filepath_relative_to_artemis_cosmos_folder()
    qlog(qlog_level_info(), f"Opening hard-server-crash-stack-trace file '{hard_crash_stack_trace_filepath}'")
    stack_trace_file = open(hard_crash_stack_trace_filepath, "w+")
    stack_trace_file.write(f"{time()}\nIf the server hard crashes, then a python stack trace might be written to this file. If the currently-running mission script ends normally, then this file should get deleted. (It might not get deleted if the game server is closed forcefully.)\n")
    faulthandler.enable(file=stack_trace_file)
    
    @atexit.register
    def cleanup_faulthandler():
        qlog(qlog_level_info(), f"Attempting to close hard-server-crash-stack-trace file")
        faulthandler.disable()
        stack_trace_file.close()
        qlog(qlog_level_info(), f"Successfully closed hard-server-crash-stack-trace file")
        # If a hard crash actually happened, this cleanup code should never even run.
        # But still, just in case, verify the file is empty (besides the timestamp on
        # the first line and description on the second).
        with open(hard_crash_stack_trace_filepath, "r") as f:
            f.readline()
            f.readline()
            has_third_line = 0 < len(f.read(1))
        if not has_third_line:
            qlog(qlog_level_info(), f"Deleting hard-server-crash-stack-trace file")
            Path(hard_crash_stack_trace_filepath).unlink(missing_ok=True)
        else:
            qlog(qlog_level_info(), f"Will NOT delete hard-server-crash-stack-trace file because it appears to contain some data")

def qlog(level, message, player_ship_id=None, client_id=None, non_player_ship_id=None, grid_object_id=None, player_craft_id=None):
    if level < _QLOG_LOWEST_LEVEL:
        return
    
    level_abbrev = qlog_get_level_abbrev(level)
    client_id_prefix = ""
    player_ship_prefix = ""
    non_player_ship_prefix = ""
    grid_object_prefix = ""
    player_craft_prefix = ""
    if player_ship_id is not None:
        player_ship_object = to_space_object(player_ship_id)
        player_ship_name = player_ship_object.name if player_ship_object is not None else ""
        player_ship_prefix = f"Player ship {player_ship_name} (id={player_ship_id}) "
    if client_id is not None:
        client_id_prefix = f"Client {client_id} "
    if non_player_ship_id is not None:
        non_player_ship_object = to_space_object(non_player_ship_id)
        non_player_ship_name = non_player_ship_object.name if non_player_ship_object is not None else ""
        non_player_ship_prefix = f"Ship {non_player_ship_name} (id={non_player_ship_id}) "
    if grid_object_id is not None:
        grid_object = to_grid_object(grid_object_id)
        grid_object_name = grid_object.name
        grid_object_prefix = f"Grid object {grid_object_name} (id={grid_object_id}) "
    if player_craft_id is not None:
        player_craft_object = to_space_object(player_craft_id)
        player_craft_name = player_craft_object.name if player_craft_object is not None else ""
        player_craft_prefix = f"Player craft {player_craft_name} (id={player_craft_id}) "
    
    # Try to minimize how many intermediate string values are created, for performance
    if level in {qlog_level_critical(), qlog_level_error(), qlog_level_warn()}:
        message = f"[{level_abbrev}] {client_id_prefix}{player_ship_prefix}{non_player_ship_prefix}{grid_object_prefix}{player_craft_prefix}{message}"
        print(message)
        full_message = f"[{datetime.now()}] {message}"
    else:
        full_message = f"[{datetime.now()}] [{level_abbrev}] {client_id_prefix}{player_ship_prefix}{non_player_ship_prefix}{grid_object_prefix}{player_craft_prefix}{message}"
    log(message=full_message, name=_QLOG_LOGGER_NAME)

# ----- private -----

_QLOG_LOGGER_NAME = "qlog"

def _qlog_get_new_log_filepath_relative_to_mission_folder():
    cleaned_timestamp = _qlog_get_cleaned_timestamp()
    return f"q_logs/q-log {cleaned_timestamp}.txt"

def _qlog_get_logs_folder_filepath_relative_to_artemis_cosmos_folder():
    return f"data\\missions\\{get_mission_name()}\\q_logs\\"

def _qlog_get_hard_crash_stack_trace_filepath_relative_to_artemis_cosmos_folder():
    cleaned_timestamp = _qlog_get_cleaned_timestamp()
    return f"{_qlog_get_logs_folder_filepath_relative_to_artemis_cosmos_folder()}q-log {cleaned_timestamp} hard-server-crash-stack-trace.txt"

def _qlog_get_cleaned_timestamp():
    timestamp = str(datetime.now())
    # remove the decimals at the end
    timestamp = timestamp.split(".", 1)[0]
    # replace : with -
    timestamp = timestamp.replace(":","-")
    # filter out characters that aren't included in this whitelist
    whitelisted_characters = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-")
    return "".join(character for character in timestamp if character in whitelisted_characters)

def _qlog_delete_old_logs():
    # Working directory for this is where the artemis cosmos exe is
    for filepath in _qlog_get_all_filepaths(_qlog_get_logs_folder_filepath_relative_to_artemis_cosmos_folder()):
        if filepath.endswith(".txt") and _qlog_is_log_file_old(filepath):
            qlog(qlog_level_info(), f"Deleting old log file '{filepath}'")
            Path(filepath).unlink(missing_ok=True)

def _qlog_get_all_filepaths(directory):
    # copied from https://stackoverflow.com/questions/3207219/how-do-i-list-all-files-of-a-directory
    return [os.path.join(dirpath, filename) for (dirpath, dirnames, filenames) in os.walk(directory) for filename in filenames]

def _qlog_is_log_file_old(filepath):
    try:
        creation_time = _qlog_extract_creation_time_from_log_file(filepath)
    except:
        qlog(qlog_level_warn(), f"Could not extract log creation timestamp from file '{filepath}'. It will not get deleted automatically. Consider deleting it manually, or move it to a different directory if it's not a log file.")
        return False
    # 60s * 60m * 24h = 86400s in one day
    return creation_time < time() - 86400

def _qlog_extract_creation_time_from_log_file(filepath):
    with open(filepath, "r") as f:
        return float(f.readline())
