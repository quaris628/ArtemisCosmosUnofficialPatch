from sbs_utils.procedural.execution import get_shared_variable, set_shared_variable
from sbs_utils.procedural.query import to_space_object
import random


def get_defender_name(side="tsn", allow_canuck=True):
    if side == "terran":
        side = "tsn"

    shipname_data = get_shared_variable("SHIP_NAME_DATA")
    if shipname_data is None:
        return "SHIP DATA FAILED"

    tsnname_list = shipname_data.get(side)
    canuck_list = shipname_data.get("canadian")

    name = f"TSN {tsnname_list.pop(random.randrange(len(tsnname_list)))}"
    if allow_canuck and random.randint(1,1867) == 1867: ### This is an inside joke for our Canadian players. 
        name = f"TSN {canuck_list.pop(random.randrange(len(canuck_list)))}"

    return name

def get_location_text(t, tp, defa):
    t = to_space_object(t) 
    if t is not None:
        return t.name
    if tp is not None:
        z = chr(64 + int(tp.z // 20000 + 13) % 26)
        x = int(tp.x // 20000 + 12) % 100

        return f"grid {z}{x:02d}"
        
    return defa

def get_civilian_callsign_and_name():
    CIVILIAN_CALLSIGN_UNIQUE_NUMBER = get_shared_variable("CIVILIAN_CALLSIGN_UNIQUE_NUMBER")
    SHIP_NAME_DATA = get_shared_variable("SHIP_NAME_DATA")
    
    # amount added must be coprime with the total number of possibilities
    # to ensure all possible callsigns are used up before one is repeated
    CIVILIAN_CALLSIGN_UNIQUE_NUMBER = (CIVILIAN_CALLSIGN_UNIQUE_NUMBER + 353) % 1200
    set_shared_variable("CIVILIAN_CALLSIGN_UNIQUE_NUMBER", CIVILIAN_CALLSIGN_UNIQUE_NUMBER)
    
    letter_index, digits = divmod(CIVILIAN_CALLSIGN_UNIQUE_NUMBER, 100)
    letter = "BCFGHJRSUVYZ"[letter_index]
    
    civname_list = SHIP_NAME_DATA.get("civilian")
    name = civname_list.pop(random.randrange(len(civname_list)))
    
    callsign_and_name = f"{letter}{digits:02d} {name}"
    
    return callsign_and_name
