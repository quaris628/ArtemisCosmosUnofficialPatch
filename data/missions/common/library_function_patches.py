import re

from sbs_utils.gui import get_client_aspect_ratio
from sbs_utils.helpers import FakeEvent, FrameContext, FrameContextOverride
from sbs_utils.mast.label import label
from sbs_utils.pages.layout.blank import Blank
from sbs_utils.pages.layout.button import Button
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.pages.layout.row import Row
from sbs_utils.procedural.execution import AWAIT, END, get_variable, gui_task_jump, task_schedule
from sbs_utils.procedural.gui import ButtonPromise
from sbs_utils.procedural.gui.navigation import gui_reroute_client, gui_reroute_server
from sbs_utils.procedural.gui.property_listbox import _gui_properties_items
from sbs_utils.procedural.style import apply_control_styles
from sbs_utils.procedural.timers import delay_app

# ----- switching GUIs -----

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

# sbs_utils/procedural/gui/gui.py function gui()
# It should assert that it should run on FrameContext.page.gui_task, not FrameContext.client_task
# https://github.com/orgs/artemis-sbs/discussions/628#discussioncomment-16919456
def gui_patched(buttons=None, timeout=None):
    """present the gui that has been queued up
    
    Args:
        buttons (dict, optional): _description_. Defaults to None.
        timeout (promise, optional): A promise that ends the gui. Typically a timeout. Defaults to None.
    
    Returns:
        Promise: The promise for the gui, promise is done when a button is selected
    """
    page = FrameContext.page
    task = FrameContext.task
    
    #gui_task = FrameContext.client_task # bad
    gui_task = FrameContext.page.gui_task # patch
    
    ret = GuiPromise(page, timeout)
    if buttons is not None:
        for k in buttons:
            ret.buttons.append(Button(k, label=buttons[k],loc=0))
    
    if task != gui_task:
        print("await gui() was not called in gui's main task. Consider using gui_task_jump.")
    else:
        page.swap_gui_promise(ret)
    return ret

# sbs_utils/procedural/gui/gui.py class GuiPromise
# Not edited from its original form.
# Copied here only because it apparently can't be imported from sbs_utils.
class GuiPromise(ButtonPromise):
    button_height_px = 40

    def __init__(self, page, timeout=None) -> None:
        path = page.get_path()
        super().__init__(path, page.gui_task, timeout)

        self.page = page
        self.button_layout = None

    def initial_poll(self):
        if self._initial_poll:
            return
        
        super().initial_poll()
        self.show_buttons()
        self.page.set_button_layout(self.button_layout, self)

    #
    # This
    #
    def show_buttons(self):
        if self.task is None: # pylint: disable=access-member-before-definition
            self.task = self.page.gui_task # pylint: disable=attribute-defined-outside-init
            # First run could have no gui_task
            if self.task is None:
                self.task = FrameContext.task # pylint: disable=attribute-defined-outside-init
        task = self.task
        aspect_ratio = get_client_aspect_ratio(task.main.page.client_id)

        #
        # Create button Row
        #
        top = ((aspect_ratio.y - GuiPromise.button_height_px)/aspect_ratio.y)*100

        button_layout = Layout(None, None, 0,top,100,100)
        button_layout.tag = task.main.page.get_tag()

        active = 0
        index = 0
        layout_row: Row
        layout_row = Row()
        layout_row.tag = task.main.page.get_tag()

        buttons = self.get_expanded_buttons()
        
        if len(buttons) == 0:
            return
        
        
        for button in buttons:
            match button.__class__.__name__:
                case "Button":
                    value = True
                    #button.end_await_node = node.end_await_node
                    if button.code is not None:
                        value = task.eval_code(button.code)
                    if value and button.should_present(0):#task.main.client_id):
                        runtime_node = ChoiceButtonRuntimeNode(self, button, task.main.page.get_tag())
                        #runtime_node.enter(mast, task, button)
                        msg = task.format_string(button.message)
                        layout_button = Button(runtime_node.tag, msg)
                        button.layout_item = layout_button
                        layout_row.add(layout_button)

                        apply_control_styles(".choice", None, layout_button, task)
                        
                        # After style could change tag
                        task.main.page.add_tag(layout_button, runtime_node)
                        active += 1
                case "Separator":
                    # Handle face expression
                    layout_row.add(Blank())
            index+=1
        
        if active>0:
            button_layout.add(layout_row)
            self.button_layout = button_layout
            #task.main.page.set_button_layout(button_layout)
        else:
            self.button_layout = None
            #task.main.page.set_button_layout(None)

        self.active_buttons = active # pylint: disable=attribute-defined-outside-init
        self.buttons = buttons # pylint: disable=attribute-defined-outside-init
        self.button = None # pylint: disable=attribute-defined-outside-init

# sbs_utils/procedural/gui/gui.py class ChoiceButtonRuntimeNode
# Not edited from its original form.
# Copied here only because it apparently can't be imported from sbs_utils.
class ChoiceButtonRuntimeNode: # pylint: disable=too-few-public-methods
    def __init__(self, promise, button, tag):
        self.promise = promise
        self.button = button
        self.tag = tag
    
    def on_message(self, event):
        #
        # The 'right' page already filtered
        # event to know it is for this client
        #
        if event.sub_tag == self.tag:
            self.promise.press_button(self.button)

# ----- reroute -----

def reroute(client_id, label_for_both_or_server, label_for_client=None):
    if client_id == 0:
        gui_reroute_server(label_for_both_or_server)
    else:
        if label_for_client is None:
            label_for_client = label_for_both_or_server
        gui_reroute_client(client_id, label_for_client)

# ----- text input -----

# Fixes serious input sanitization issues present for any text input box:
# https://github.com/artemis-sbs/LegendaryMissions/issues/569
# And fixes an issue with the ` character being present when it should be blank
# https://github.com/artemis-sbs/LegendaryMissions/issues/641
# Any text inputs that are inside a list box must pass listbox_container
# to work around not being able to be individually re-presented:

# https://github.com/artemis-sbs/LegendaryMissions/issues/349
# Unfortunately the above ^ workaround for text inputs inside listboxes
# seems to not work all the time and have bugs with old characters persisting
# and overlapping with new text, especially when spamming invalid characters.
# I still think this is overall an improvement; occasional visual bugs in
# exchange for preventing data corruption seems like a good deal to me.

# sbs_utils/procedural/gui/input.py function gui_input
def gui_input(props, style=None, var=None, data=None, listbox_container=None):
    """ Draw a text type in

    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    

    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    if props is not None:
        props = task.compile_and_format_string(props)
    else:
        props = ""

    val = ""
    if var is not None:
        val = task.get_variable(var, "")

    if "$text:" not in props:
        #props = f"$text:`{val}`;{props}" # Bad
        # vvv Patch vvv
        sanitized_text = re.sub(r"[^A-Za-z0-9 \-_']", "", val)
        if var is not None and sanitized_text != val:
            task.set_variable(var, sanitized_text)
        props = f"$text:{sanitized_text};{props}"
        # ^^^ Patch ^^^

    layout_item = TextInput(tag, props, listbox_container)
    layout_item.data = data # pylint: disable=attribute-defined-outside-init
    if var is not None:
        layout_item.var_name = var # pylint: disable=attribute-defined-outside-init
        layout_item.var_scope_id = task.get_id() # pylint: disable=attribute-defined-outside-init

    apply_control_styles(".input", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

# sbs_utils/pages/layout/text_input.py class TextInput
class TextInput(Column):
    def __init__(self, tag, props, listbox_container) -> None:
        super().__init__()
        self._value = ""
        if "text:" in props:
            #TODO: Need to parse out value # pylint: disable=fixme
            #     
            text = re.search(r"\$?text:(?P<text>.*);", props).group('text')
            if text:
                self._value = text

            fix_props = re.sub(r'\$?text:\s*.*;', "", props)
            props = fix_props

        self.tag = tag
        self.props = props
        self.listbox_container = listbox_container

    def _present(self, event):
        ctx = FrameContext.context
        props = f"$text:{self._value};"
        props += self.props
        props += self.get_cascade_props(True, True, True)
        ctx.sbs.send_gui_typein(event.client_id, self.region_tag,
            self.tag, props,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    def on_message(self, event):
        if event.sub_tag == self.tag:
            #self.value = event.value_tag # Bad
            # vvv Patch vvv
            sanitized_text = re.sub(r"[^A-Za-z0-9 \-_']", "", event.value_tag)
            self.value = sanitized_text
            if sanitized_text != event.value_tag:
                self.mark_visual_dirty()
                if self.listbox_container is not None:
                    self.listbox_container.mark_visual_dirty()
            # ^^^ Patch ^^^
        super().on_message(event)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value= v
        self.update_variable()

# ----- properties list box -----

# https://github.com/artemis-sbs/LegendaryMissions/issues/575
# This was making it impossible to show the options list box
# for the game setup screen

def gui_properties_set_patched(listbox_object, p=None):
    # 
    # This is confusing because of COMMS
    # Comms runs on the sever task, but the GUI needs 
    # to be the client for the comms operations
    # So COMMS is setting the page to the client
    # and the server task is the task
    #
    gui_task = FrameContext.client_task
    #gui_page = FrameContext.client_page
    event = FrameContext.context.event
    if gui_task is None:
        raise Exception("EDGE CASE: Did you set END or Yield the last GUI Task?")  # pylint: disable=broad-exception-raised
        
    # This happens in a follow_route_select_comms
    # And it runs on the server not a true comms console
    if event is None:# or event.tag == "gui_present":
        return
    changes = set(gui_task.get_variable("__PROP_CHANGES__", []))
    gui_task.on_change_items = [change for change in gui_task.on_change_items if change not in changes]
    gui_task.set_variable("__PROP_CHANGES__", [])

    with FrameContextOverride(FrameContext.client_task, FrameContext.client_page):
        listbox_object.items = _gui_properties_items(p)
        # Clear the on changes
        gui_represent_patched(listbox_object)

# ----- gui re-present -----

# https://github.com/artemis-sbs/LegendaryMissions/issues/571
# Caused the ship type ui elements to sometimes not be
# re-presented when the ship type is changed by another client

# sbs_utils/procedural/gui/update.py gui_represent()
def gui_represent_patched(layout_item):
    layout_item.represent(FakeEvent(get_variable("client_id")))
