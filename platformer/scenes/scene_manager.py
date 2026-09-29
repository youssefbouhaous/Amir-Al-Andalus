import pygame

from scenes.scene import Scene


class SceneManager:
    """A stack of scenes. Only the top one updates; overlays draw on top.

    push:    open something on top (pause menu over gameplay)
    pop:     close it and return to the scene below
    replace: swap the top scene (menu -> level intro -> gameplay)
    reset:   clear everything and start fresh (back to the main menu)
    """

    def __init__(self) -> None:
        self._stack: list[Scene] = []
        self.running = True

    @property
    def top(self) -> Scene | None:
        return self._stack[-1] if self._stack else None

    def push(self, scene: Scene) -> None:
        self._stack.append(scene)
        scene.on_enter()

    def pop(self) -> None:
        if self._stack:
            self._stack.pop()
        if self._stack:
            self._stack[-1].on_resume()

    def replace(self, scene: Scene) -> None:
        if self._stack:
            self._stack.pop()
        self.push(scene)

    def reset(self, scene: Scene) -> None:
        self._stack.clear()
        self.push(scene)

    def quit(self) -> None:
        self.running = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.top is not None:
            self.top.handle_event(event)

    def update(self, dt: float) -> None:
        if self.top is not None:
            self.top.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        # Draw from the topmost non-overlay scene upwards.
        start = 0
        for index in range(len(self._stack) - 1, -1, -1):
            if not self._stack[index].is_overlay:
                start = index
                break
        for scene in self._stack[start:]:
            scene.draw(surface)
