import bpy
import bmesh
from math import radians
from .. lib.overlay import update_overlay, init_overlay, toggle_pin_overlay, register_draw_handler, unregister_draw_handler, draw_header, draw_property
from .. lib.events import capture_modifier_keys


class ND_OT_screw(bpy.types.Operator):
    bl_idname = "nd.screw"
    bl_label = "Screw"
    bl_description = "Adds a screw modifier tuned for converting a sketch into a cylindrical object"
    bl_options = {'UNDO'}


    def modal(self, context, event):
        capture_modifier_keys(self, event)

        segment_factor = 1 if self.key_shift else 2
        angle_factor = 1 if self.key_shift else 10
        offset_factor = (self.base_offset_factor / 10.0) if self.key_shift else self.base_offset_factor

        if self.key_toggle_pin_overlay:
            toggle_pin_overlay(self)

        elif self.key_increase_factor:
            if self.key_ctrl_alt:
                self.base_offset_factor = min(1, self.base_offset_factor * 10.0)

        elif self.key_decrease_factor:
            if self.key_ctrl_alt:
                self.base_offset_factor = max(0.001, self.base_offset_factor / 10.0)

        elif self.key_step_up:
            if self.key_ctrl_alt:
                self.offset += offset_factor
            elif self.key_alt:
                if self.key_shift:
                    self.offset_axis = (self.offset_axis + 1) % 3
                else:
                    self.screw_axis = (self.screw_axis + 1) % 3
            elif self.key_ctrl:
                self.angle = min(360, self.angle + angle_factor)
            else:
                self.segments = 4 if self.segments == 3 else self.segments + segment_factor
            
        elif self.key_step_down:
            if self.key_ctrl_alt:
                self.offset -= offset_factor
            elif self.key_alt:
                if self.key_shift:
                    self.offset_axis = (self.offset_axis + 1) % 3
                else:
                    self.screw_axis = (self.screw_axis + 1) % 3
            elif self.key_ctrl:
                self.angle = max(0, self.angle - angle_factor)
            else:
                self.segments = max(3, self.segments - segment_factor)
        
        elif self.key_confirm:
            self.finish(context)

            return {'FINISHED'}

        elif self.key_cancel:
            self.revert(context)

            return {'CANCELLED'}

        elif self.key_movement_passthrough:
            return {'PASS_THROUGH'}

        self.operate(context)
        update_overlay(self, context, event, x_offset=360, lines=4)

        return {'RUNNING_MODAL'}


    def invoke(self, context, event):
        self.base_offset_factor = 0.01

        self.screw_axis = 2 # X (0), Y (1), Z (2)
        self.offset_axis = 1 # X (0), Y (1), Z (2)
        self.segments = 3
        self.angle = 360
        self.offset = 0

        self.add_smooth_shading(context)
        self.add_displace_modifier(context)
        self.add_screw_modifier(context)

        capture_modifier_keys(self)

        init_overlay(self, event)
        register_draw_handler(self, draw_text_callback)

        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return len(context.selected_objects) == 1


    def add_smooth_shading(self, context):
        bpy.ops.object.shade_smooth()
        context.object.data.use_auto_smooth = True
        context.object.data.auto_smooth_angle = radians(30)


    def add_displace_modifier(self, context):
        displace = context.object.modifiers.new("ND — Offset", 'DISPLACE')
        displace.mid_level = 0.5
        displace.strength = self.offset
        displace.space = 'LOCAL'
        displace.direction = ['X', 'Y', 'Z'][self.offset_axis]
        
        self.displace = displace


    def add_screw_modifier(self, context):
        screw = context.object.modifiers.new("ND — Screw", 'SCREW')
        screw.angle = radians(self.angle)
        screw.screw_offset = 0
        screw.axis = ['X', 'Y', 'Z'][self.screw_axis]
        screw.steps = self.segments
        screw.render_steps = self.segments
        screw.use_merge_vertices = True 
        screw.merge_threshold = 0.0001

        self.screw = screw
    

    def operate(self, context):
        self.displace.strength = self.offset
        self.displace.direction = ['X', 'Y', 'Z'][self.offset_axis]

        self.screw.axis = ['X', 'Y', 'Z'][self.screw_axis]
        self.screw.steps = self.segments
        self.screw.render_steps = self.segments
        self.screw.angle = radians(self.angle)


    def finish(self, context):
        unregister_draw_handler()


    def revert(self, context):
        bpy.ops.object.modifier_remove(modifier=self.screw.name)
        bpy.ops.object.modifier_remove(modifier=self.displace.name)
        unregister_draw_handler()


def draw_text_callback(self):
    draw_header(self)

    draw_property(
        self,
        "Segments: {}".format(self.segments),
        "(±2)  |  Shift (±1)",
        active=self.key_no_modifiers,
        alt_mode=self.key_shift_no_modifiers)
    
    draw_property(
        self,
        "Screw Axis: {} ~ Offset Axis: {}".format(['X', 'Y', 'Z'][self.screw_axis], ['X', 'Y', 'Z'][self.offset_axis]),
        "Alt (Screw X, Y, Z)  |  Shift + Alt (Offset X, Y, Z)",
        active=self.key_alt,
        alt_mode=self.key_shift_alt)

    draw_property(
        self,
        "Angle: {0:.0f}°".format(self.angle),
        "Ctrl (±10)  |  Shift + Ctrl (±1)",
        active=self.key_ctrl,
        alt_mode=self.key_shift_ctrl)

    draw_property(
        self,
        "Offset: {0:.3f}".format(self.offset),
        "Ctrl + Alt (±{0:.1f})  |  Shift + Ctrl + Alt (±{1:.1f})".format(self.base_offset_factor * 1000, (self.base_offset_factor / 10) * 1000),
        active=self.key_ctrl_alt,
        alt_mode=self.key_shift_ctrl_alt)


def menu_func(self, context):
    self.layout.operator(ND_OT_screw.bl_idname, text=ND_OT_screw.bl_label)


def register():
    bpy.utils.register_class(ND_OT_screw)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(ND_OT_screw)
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    unregister_draw_handler(self, ND_OT_screw.bl_label)