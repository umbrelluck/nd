# ███╗   ██╗██████╗ 
# ████╗  ██║██╔══██╗
# ██╔██╗ ██║██║  ██║
# ██║╚██╗██║██║  ██║
# ██║ ╚████║██████╔╝
# ╚═╝  ╚═══╝╚═════╝ 
# 
# “Commons Clause” License Condition v1.0
# 
# See LICENSE for license details. If you did not receive a copy of the license,
# it may be obtained at https://github.com/hugemenace/nd/blob/main/LICENSE.
# 
# Software: ND Blender Addon
# License: MIT
# Licensor: T.S. & I.J. (HugeMenace)
# 
# ---
# Contributors: Tristo (HM)
# ---

import bpy
import bmesh
from math import radians
from .. lib.base_operator import BaseOperator
from .. lib.overlay import init_overlay, register_draw_handler, unregister_draw_handler, draw_header, draw_property, draw_hint
from .. lib.events import capture_modifier_keys, pressed
from .. lib.preferences import get_preferences, get_scene_unit_factor
from .. lib.numeric_input import update_stream, no_stream, get_stream_value, new_stream
from .. lib.modifiers import new_modifier, remove_modifiers_ending_with


mod_displace = "Offset — ND SOL"
mod_solidify = "Thickness — ND SOL"
mod_summon_list = [mod_displace, mod_solidify]


class ND_OT_solidify(BaseOperator):
    bl_idname = "nd.solidify"
    bl_label = "Solidify"
    bl_description = """Adds a solidify modifier, and enables smoothing
CTRL — Remove existing modifiers"""


    def do_modal(self, context, event):
        if self.key_numeric_input:
            if self.key_no_modifiers:
                self.thickness_input_stream = update_stream(self.thickness_input_stream, event.type)
                self.thickness = get_stream_value(self.thickness_input_stream, self.unit_scaled_factor)
                self.dirty = True
            elif self.key_ctrl:
                self.offset_input_stream = update_stream(self.offset_input_stream, event.type)
                self.offset = get_stream_value(self.offset_input_stream, self.unit_scaled_factor)
                self.dirty = True

        if self.key_reset:
            if self.key_no_modifiers:
                self.thickness_input_stream = new_stream()
                self.thickness = 0
                self.dirty = True
            elif self.key_ctrl:
                self.offset_input_stream = new_stream()
                self.offset = 0
                self.dirty = True

        if pressed(event, {'W'}):
            self.weighting = self.weighting + 1 if self.weighting < 1 else -1
            self.dirty = True
        
        if pressed(event, {'M'}):
            self.complex_mode = not self.complex_mode
            self.dirty = True

        if self.key_step_up:
            if no_stream(self.thickness_input_stream) and self.key_no_modifiers:
                self.thickness += self.step_size
                self.dirty = True
            elif no_stream(self.offset_input_stream) and self.key_ctrl:
                self.offset += self.step_size
                self.dirty = True
            
        if self.key_step_down:
            if no_stream(self.thickness_input_stream) and self.key_no_modifiers:
                self.thickness = max(0, self.thickness - self.step_size)
                self.dirty = True
            elif no_stream(self.offset_input_stream) and self.key_ctrl:
                self.offset -= self.step_size
                self.dirty = True
        
        if self.key_confirm:
            self.finish(context)

            return {'FINISHED'}

        if self.key_movement_passthrough:
            return {'PASS_THROUGH'}

        if get_preferences().enable_mouse_values:
            if no_stream(self.thickness_input_stream) and self.key_no_modifiers:
                self.thickness = max(0, self.thickness + self.mouse_value)
                self.dirty = True
            elif no_stream(self.offset_input_stream) and self.key_ctrl:
                self.offset += self.mouse_value
                self.dirty = True


    def do_invoke(self, context, event):
        if event.ctrl:
            remove_modifiers_ending_with(context.selected_objects, ' — ND SOL')
            return {'FINISHED'}

        self.dirty = False
        self.complex_mode = False

        self.thickness_input_stream = new_stream()
        self.offset_input_stream = new_stream()

        mods = context.active_object.modifiers
        mod_names = list(map(lambda x: x.name, mods))
        previous_op = all(m in mod_names for m in mod_summon_list)

        if previous_op:
            self.summon_old_operator(context, mods)
        else:
            self.prepare_new_operator(context)

        self.operate(context)

        capture_modifier_keys(self, None, event.mouse_x)

        init_overlay(self, event)
        register_draw_handler(self, draw_text_callback)

        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return len(context.selected_objects) == 1 and context.active_object.type == 'MESH'

    
    def prepare_new_operator(self, context):
        self.summoned = False

        self.thickness = 0
        self.weighting = 0
        self.offset = 0

        self.add_smooth_shading(context)
        self.add_displace_modifier(context)
        self.add_solidify_modifier(context)


    def summon_old_operator(self, context, mods):
        self.summoned = True

        self.solidify = mods[mod_solidify]
        self.displace = mods[mod_displace]

        self.thickness_prev = self.thickness = self.solidify.thickness
        self.weighting_prev = self.weighting = self.solidify.offset
        self.complex_mode_prev = self.complex_mode = (self.solidify.solidify_mode == 'NON_MANIFOLD')
        self.offset_prev = self.offset = self.displace.strength


    def add_smooth_shading(self, context):
        bpy.ops.object.shade_smooth()
        context.active_object.data.use_auto_smooth = True
        context.active_object.data.auto_smooth_angle = radians(float(get_preferences().default_smoothing_angle))


    def add_displace_modifier(self, context):
        displace = new_modifier(context.active_object, mod_displace, 'DISPLACE', rectify=True)
        displace.mid_level = 0

        self.displace = displace


    def add_solidify_modifier(self, context):
        solidify = new_modifier(context.active_object, mod_solidify, 'SOLIDIFY', rectify=True)
        solidify.use_even_offset = True
        solidify.nonmanifold_thickness_mode = 'CONSTRAINTS'
        solidify.use_quality_normals = True

        self.solidify = solidify
    

    def operate(self, context):
        self.solidify.thickness = self.thickness
        self.solidify.offset = self.weighting
        self.solidify.solidify_mode = 'NON_MANIFOLD' if self.complex_mode else 'EXTRUDE'
        self.displace.strength = self.offset

        self.dirty = False


    def finish(self, context):
        unregister_draw_handler()


    def revert(self, context):
        if not self.summoned:
            bpy.ops.object.modifier_remove(modifier=self.displace.name)
            bpy.ops.object.modifier_remove(modifier=self.solidify.name)

        if self.summoned:
            self.solidify.thickness = self.thickness_prev
            self.solidify.offset = self.weighting_prev
            self.solidify.solidify_mode = 'NON_MANIFOLD' if self.complex_mode_prev else 'EXTRUDE'
            self.displace.strength = self.offset_prev
        
        unregister_draw_handler()


def draw_text_callback(self):
    draw_header(self)

    draw_property(
        self, 
        f"Thickness: {(self.thickness * self.display_unit_scale):.2f}{self.unit_suffix}", 
        self.unit_step_hint,
        active=self.key_no_modifiers,
        alt_mode=self.key_shift_no_modifiers,
        mouse_value=True,
        input_stream=self.thickness_input_stream)

    draw_property(
        self,
        f"Offset: {(self.offset * self.display_unit_scale):.2f}{self.unit_suffix}",
        self.generate_key_hint("Ctrl", self.unit_step_hint),
        active=self.key_ctrl,
        alt_mode=self.key_shift_ctrl,
        mouse_value=True,
        input_stream=self.offset_input_stream)

    draw_hint(
        self,
        "Weighting [W]: {}".format(['Negative', 'Neutral', 'Positive'][1 + round(self.weighting)]),
        "Negative, Neutral, Positive")

    draw_hint(
        self,
        "Mode [M]: {}".format("Complex" if self.complex_mode else "Simple"),
        "Extrusion Algorithm (Simple, Complex)")


def register():
    bpy.utils.register_class(ND_OT_solidify)


def unregister():
    bpy.utils.unregister_class(ND_OT_solidify)
    unregister_draw_handler()
