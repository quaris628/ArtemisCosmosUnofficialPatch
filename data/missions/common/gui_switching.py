from sbs_utils.helpers import FrameContext
from sbs_utils.mast.label import label
from sbs_utils.procedural.execution import AWAIT, END, get_variable, task_schedule
from sbs_utils.procedural.gui.navigation import gui_reroute_client, gui_reroute_server
from sbs_utils.procedural.timers import delay_app

# The relationship between (re)drawing a GUI and what task/code the
# redraw is happening on and was triggered by seems VERY fragile.
# https://github.com/artemis-sbs/LegendaryMissions/issues/579
# https://github.com/artemis-sbs/LegendaryMissions/issues/590
# https://github.com/orgs/artemis-sbs/discussions/628
# https://github.com/artemis-sbs/LegendaryMissions/issues/634
# https://github.com/artemis-sbs/LegendaryMissions/issues/635
# So centralize the process of switching between GUIs to this function,
# so that (hopefully) I don't have to keep doing shotgun surgery
# whenever a new gui-switching bug is discovered.

def gui_switch_to(main_gui_label, client_id=None, delay_reroute_workaround=False):
    """
    Switches a client from its current gui to a completely new gui.
    (For example, switch from the console selection screen to the helm screen.)
    
    Args:
        main_gui_label (string | label object): The main entry point for code
            that creates a gui.
        client_id (int | None): Default get_variable("client_id"). The client_id
            whose gui will be switched to main_gui_label.
        delay_reroute_workaround (bool | None): Default False. Adds a small delay
            before switching guis in order to work around this issue
            https://github.com/artemis-sbs/LegendaryMissions/issues/634
    """
    if client_id is None:
        client_id = get_variable("client_id")
    
    if delay_reroute_workaround:
        task_schedule(_gui_switch_to_delay_reroute_workaround, data={"MAIN_GUI_LABEL": main_gui_label, "CLIENT_ID": client_id})
    else:
        reroute(client_id, main_gui_label)

@label()
def _gui_switch_to_delay_reroute_workaround():
    client_id = get_variable("CLIENT_ID")
    main_gui_label = get_variable("MAIN_GUI_LABEL")
    yield AWAIT(delay_app(0.01))
    reroute(client_id, main_gui_label)
    yield END()

def ensure_on_gui_task(main_gui_label):
    """
    Checks whether the current task is the correct task on which to draw a gui.
    If it is, returns True and doesn't do anything else (since everything is fine).
    But if it isn't, returns False and makes the correct gui task switch to the
    passed label. (In this case, code calling this function should probably ->END.)
    
    This function is primarily intended to be called at the beginning of gui code like so:
        ==== main_gui_label ====
            
            if not ensure_on_gui_task(main_gui_label):
                ->END
            
            # insert gui_section(), gui_text(), etc. calls here
            
            await gui()
    
    Args:
        main_gui_label (str): The label to jump the correct gui task to (if necessary).
    
    Returns:
        True if this function was called from the correct task on which to create a gui;
            otherwise False.
    """
    if FrameContext.task == FrameContext.page.gui_task:
        return True
    else:
        gui_switch_to(main_gui_label)
        return False

def reroute(client_id, label_for_both_or_server, label_for_client=None):
    if client_id == 0:
        gui_reroute_server(label_for_both_or_server)
    else:
        if label_for_client is None:
            label_for_client = label_for_both_or_server
        gui_reroute_client(client_id, label_for_client)
