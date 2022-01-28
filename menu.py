import bpy
from . import bl_info

keys = []

class ND_MT_menu(bpy.types.Menu):
    bl_label = "ND v%s" % ('.'.join([str(v) for v in bl_info['version']]))
    bl_idname = "nd.menu"


    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("nd.view_align", icon='FACESEL')
        layout.operator("nd.new_sketch", icon='GREASEPENCIL')
        layout.operator("nd.sketch_bevel", icon='MOD_BEVEL')
        layout.separator()
        layout.operator("nd.faux_bevel", icon='MOD_BEVEL')
        layout.operator("nd.thickener", icon='MOD_SOLIDIFY')
        layout.operator("nd.spinner", icon='MOD_SCREW')
        layout.separator()
        layout.operator("nd.bolt", icon='MESH_CYLINDER')


def draw_item(self, context):
    layout = self.layout
    layout.menu(ND_MT_menu.bl_idname)


def register():
    bpy.utils.register_class(ND_MT_menu)
    bpy.types.INFO_HT_header.append(draw_item)
   
    keymap = bpy.context.window_manager.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    entry = keymap.keymap_items.new("wm.call_menu", 'TWO', 'PRESS', shift = True)
    entry.properties.name = "nd.menu"

    keys.append((keymap, entry))


def unregister():
    for keymap, entry in keys:
        keymap.keymap_items.remove(entry)

    keys.clear()

    bpy.utils.unregister_class(ND_MT_menu)
    bpy.types.INFO_HT_header.remove(draw_item)


if __name__ == "__main__":
    register()