from sbs_utils.procedural.execution import gui_get_variable, gui_set_variable

# ----- setter/getter wrappers -----

def set_comms_options_property_list_box(options_property_list_box):
    gui_set_variable(_COMMS_OPTIONS_PROPERTY_LIST_BOX_VAR_NAME, options_property_list_box)

def get_comms_options_property_list_box():
    return gui_get_variable(_COMMS_OPTIONS_PROPERTY_LIST_BOX_VAR_NAME)

_COMMS_OPTIONS_PROPERTY_LIST_BOX_VAR_NAME = "_comms_options_property_list_box"
