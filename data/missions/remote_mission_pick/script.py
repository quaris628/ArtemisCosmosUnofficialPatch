try:
    import sbslibs
    import sbs
    

    
    from sbs_utils.handlerhooks import *
    
    from sbs_utils.gui import Gui
    
    
    from sbs_utils.mast.maststorypage import StoryPage
    from sbs_utils.mast.maststory import MastStory


    from sbs_utils.mast.mast import Mast
    from sbs_utils.mast.mast_node import MastDataObject
    from sbs_utils.mast.pollresults import PollResults
    from sbs_utils.mast.label import label
    from sbs_utils.mast_sbs import mast_sbs_procedural

    from sbs_utils.procedural.gui import gui_row, gui_icon, gui, gui_section, gui_text, gui_update, gui_blank, gui_list_box, gui_message_callback
    from sbs_utils.procedural.execution import AWAIT, get_shared_variable, jump, set_shared_variable
    from sbs_utils.procedural.timers import timeout
    from sbs_utils.procedural.cosmos import sim_create, sim_resume
    from sbs_utils.procedural.query import safe_int
    import os
    from sbs_utils.fs import get_missions_dir, get_mission_name


    def get_mission_list():
        this_mission = get_mission_name()
        missions = []
        dir = get_missions_dir()
        file_list = os.listdir(dir)
        for file in file_list:
            if not os.path.isdir(os.path.join(dir, file)):
                continue
            if file == this_mission:
                continue
            if os.path.isfile(os.path.join(dir, file, "description.txt")):
                file1 = open(os.path.join(dir, file, "description.txt"), 'r')
                lines = file1.readlines()
                while len(lines) < 3:
                    lines.append("")
                mission = {"name": file, 
                        "category":lines[0],
                        "desc":lines[1],
                        "icons":[] }
                for i in lines[2:]:
                    i = i.split()
                    
                    if len(i)>=2:
                        icon = {"index": safe_int(i[0]), "color": i[1]}
                        #icon = f"icon_index:{safe_int(i[0])};color:{i[1]};"
                        mission["icons"].append(icon)

                missions.append(MastDataObject(mission))
        return missions

    def template_mission_item(item):

        
        text = item.get("name", "Error no name")
        gui_row("row-height: 1.2em;padding:13px;")
        #print(item.icons)
    

        gui_blank(1,"col-width:10px;")
        gui_text(f"$text:{text};justify: left;")
        for icon_obj in item.icons:
            icon = icon_obj.get("icon_index")
            color = icon_obj.get("color")
            gui_icon(f"icon_index:{icon};color:{color};")
        gui_row("row-height: 0.2em;")
        gui_blank()

                    


    @label()
    def main_gui():
        #yield PollResults.OK_RUN_AGAIN
        # gui_reroute_server(server_start)


        lb_sec = gui_section("area: 0,15,40,100-50px")
        sbs.suppress_client_connect_dialog(0)
        sim_create()
        sim_resume()
        
        missions = get_mission_list()
        mission_name = missions[0].name 
        set_shared_variable('mission', mission_name)
        lb_missions = gui_list_box(missions, "", item_template=template_mission_item, select=True)

        def select(event, sender):
            # print("SELECT")
            mission_sel = lb_missions.get_selected_index()
            if mission_sel is None:
                return
            if mission_sel < len(missions):
                mission = missions[mission_sel]
                set_shared_variable("mission", mission.get('name', "none"))
                #update_icons(mission)
                gui_update("cat", f"$text: {mission.get('category', 'none')};")
                gui_update("desc", f"$text: {mission.get('desc','')}")
        #
        # New in v1.1.0 can set a callback
        #
        gui_message_callback(lb_missions, select)
        #
        # Property column
        #
        gui_section("area: 45,15,100,100")

        cat = missions[0].category if len(missions)!=0 else "no missions"
        desc = missions[0].desc if len(missions)!=0 else "no missions"

        gui_row(style="row-height: 45px")
        gui_text(f"$text: {cat}", style="tag:cat;")
        gui_row(style="row-height: 45px")
        
        # create_icons(missions[0])

        

        gui_row()
        gui_text(f"$text: {desc}", style="tag:desc;padding:0,20px;")
        
        yield AWAIT(gui({"start": start}))

    def update_icons(mis):
        for c in range(6):
            if c < len(mis['icons']):
                i = mis['icons'][c]
                gui_update(f"icon-{c}", f"icon_index: {i['index']};color:{i['color']};")
            else:
                gui_update(f"icon-{c}", f"icon_index:1000;color:#0000;")

    def create_icons(mis):
        for c in range(6):
            if c < len(mis['icons']):
                i = mis['icons'][c]
            #    gui_icon(f"icon_index: {i['index']};color:{i['color']};",style=f"tag: icon-{c};")
            else:
                i = {"index": 1000, "color": "#0000"}
            #     gui_text(f"",style=f"tag: icon-{c};")
            gui_icon(i,style=f"tag: icon-{c};")
        


    @label()
    def start():
        mission = get_shared_variable("mission")
        if mission is not None:
            sbs.run_next_mission(mission)

        yield AWAIT(gui({"back": main_gui}, timeout=timeout(10)))
        yield jump(main_gui)
        


    class SimpleAiPage(StoryPage):
        story = MastStory()
        main_server = main_gui
        main_client = main_gui



    Mast.include_code = True
    
    Gui.server_start_page_class(SimpleAiPage)
    Gui.client_start_page_class(SimpleAiPage)
except Exception as e:
    print("OUTS")