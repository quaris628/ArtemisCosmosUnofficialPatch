import re

from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.column import Column
from sbs_utils.procedural.style import apply_control_styles

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
