"""Additive poses for the original prince rig; never repaint its old sheets."""

import math
from dataclasses import replace

import pygame

from rendering.art import prince

NAMES = ("ledge_hang", "vault", "scarf_cast", "scarf_swing", "sand_slide",
         "spin_jump", "land_soft", "land_hard", "wall_kick")


def pose_for(name: str, frame: int, count: int) -> tuple[prince.Pose, float]:
    t = frame / max(1, count - 1)
    wave = math.sin(math.tau * frame / max(1, count))
    if name == "ledge_hang":
        return prince.Pose(lean=9, head_tilt=-8, front_upper=158, front_elbow=-16,
                           back_upper=165, back_elbow=-22, front_thigh=38 + wave * 4,
                           front_knee=64, back_thigh=-12, back_knee=16, hem=-8, plume=12), 0
    if name == "vault":
        lift = math.sin(math.pi * t)
        return prince.Pose(hip_y=35 - 5 * lift, lean=12 + 44 * lift, head_tilt=-20 * lift,
                           front_upper=145 - 180 * t, front_elbow=15 + 50 * lift,
                           back_upper=130 - 155 * t, back_elbow=36,
                           front_thigh=18 + 96 * lift, front_knee=15 + 90 * lift,
                           back_thigh=-10 + 60 * lift, back_knee=20 + 50 * lift,
                           hem=30 * lift, plume=-45 * lift, mouth="smile"), 0
    if name == "scarf_cast":
        return prince.Pose(lean=-12 + 20 * t, head_tilt=-8,
                           front_upper=45 + 126 * t, front_elbow=95 * (1 - t),
                           back_upper=-50, back_elbow=45, front_thigh=35, front_knee=48,
                           back_thigh=-18, back_knee=30, hem=-20, plume=-38, hand_glow=True), 0
    if name == "scarf_swing":
        swing = t * 2 - 1
        return prince.Pose(lean=-15 * swing, head_tilt=-8, front_upper=174, front_elbow=-6,
                           back_upper=-100 - 30 * swing, back_elbow=18,
                           front_thigh=25 + 65 * swing, front_knee=30 + 25 * abs(swing),
                           back_thigh=-10 + 42 * swing, back_knee=32,
                           hem=-25 * swing, plume=-40 * swing, mouth="smile"), 0
    if name == "sand_slide":
        return replace(prince.pose_for("slide", 0, 2), back_upper=-110 + 12 * wave,
                       back_elbow=72, front_upper=58 + 4 * wave, front_elbow=10,
                       hem=-30 + 6 * wave, plume=-70 + 12 * wave), 0
    if name == "spin_jump":
        pose = replace(prince.pose_for("pound", 0, 3), hip_y=30, lean=24,
                       front_thigh=115, back_thigh=100, plume=20, mouth="smile")
        return pose, -360 * frame / count
    if name in ("land_soft", "land_hard"):
        bend = math.sin((1 - t) * math.pi / 2) * (1 if name == "land_hard" else 0.48)
        return prince.Pose(hip_y=35.8 + 5 * bend, lean=30 * bend, head_tilt=-18 * bend,
                           front_thigh=50 * bend, front_knee=95 * bend,
                           back_thigh=10 + 30 * bend, back_knee=75 * bend,
                           front_upper=36 * bend, front_elbow=34,
                           back_upper=-45 * bend, back_elbow=22, hem=18 * bend, plume=30 * bend), 0
    return prince.Pose(lean=-18 * (1 - t), head_tilt=8, front_thigh=82 - 50 * t,
                       front_knee=90, back_thigh=-65 + 50 * t, back_knee=4,
                       front_upper=95 - 50 * t, front_elbow=25,
                       back_upper=-65, back_elbow=45, hem=-25, plume=-50), 0


def anchor(name: str, frame: int, count: int) -> tuple[float, float]:
    pose, angle = pose_for(name, frame, count)
    head = prince.skeleton(pose).head
    x, y = head[0] - 5.8 - 24, head[1] - 4.4 - 24
    a = math.radians(angle)
    # pygame rotates counterclockwise in downward-positive image coordinates.
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a) - 24


def painter(palette, counts):
    def paint(surface, name, frame):
        pose, angle = pose_for(name, frame, counts[name])
        image = prince.draw_pose(pose, palette)
        if angle:
            image = pygame.transform.rotate(image, angle)
        surface.blit(image, image.get_rect(center=(24, 24)))
    return paint
