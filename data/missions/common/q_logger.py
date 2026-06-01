from datetime import datetime
import os
from pathlib import Path
from time import time

from sbs_utils.fs import get_mission_name
from sbs_utils.procedural.execution import logger, log
from sbs_utils.procedural.query import to_space_object, to_grid_object


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

def qlog(level, message, player_ship_id=None, client_id=None, non_player_ship_id=None, grid_object_id=None):
    client_id_prefix = ""
    player_ship_prefix = ""
    non_player_ship_prefix = ""
    grid_object_prefix = ""
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
    
    # Try to minimize how many intermediate string values are created, for performance
    if level in {qlog_level_critical(), qlog_level_error(), qlog_level_warn()}:
        message = f"[{level}] {client_id_prefix}{player_ship_prefix}{non_player_ship_prefix}{grid_object_prefix}{message}"
        print(message)
        full_message = f"[{datetime.now()}] {message}"
    else:
        full_message = f"[{datetime.now()}] [{level}] {client_id_prefix}{player_ship_prefix}{non_player_ship_prefix}{grid_object_prefix}{message}"
    log(message=full_message, name=_QLOG_LOGGER_NAME)

# Problem. The sim cannot possibly continue
def qlog_level_critical():
    return "CRIT"

# Problem. The sim can continue
def qlog_level_error():
    return "ERRO"

# Likely or potential problem. The sim can continue
def qlog_level_warn():
    return "WARN"

# Not a problem
def qlog_level_info():
    return "INFO"

# Very small details for targeted bug investigations
# I don't anticpate this being used much; you probably want print() instead,
# unless you're not able to reproduce in your development working copy.
def qlog_level_debug():
    return "DEBG"


# ----- private -----

_QLOG_LOGGER_NAME = "qlog"

def _qlog_get_new_log_filepath_relative_to_mission_folder():
    cleaned_timestamp = _qlog_clean_timestamp(str(datetime.now()))
    
    return f"q_logs/q-log {cleaned_timestamp}.txt"

def _qlog_get_logs_folder_filepath_relative_to_artemis_cosmos_folder():
    return f"data\\missions\\{get_mission_name()}\\q_logs\\"

def _qlog_clean_timestamp(timestamp):
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
