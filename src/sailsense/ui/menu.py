class MenuScreen:
    def __init__(self, title, items, parent=None):
        self.title = title
        self.items = items
        self.parent = parent
        self.selected_index = 0

    def move_up(self):
        if not self.items:
            return
        self.selected_index = (self.selected_index - 1) % len(self.items)

    def move_down(self):
        if not self.items:
            return
        self.selected_index = (self.selected_index + 1) % len(self.items)

    def selected_item(self):
        if not self.items:
            return None
        return self.items[self.selected_index]


class MenuItem:
    def __init__(self, label, target=None, action=None):
        self.label = label
        self.target = target
        self.action = action


class MenuController:
    def __init__(self, root_screen, on_render):
        self.root_screen = root_screen
        self.current_screen = root_screen
        self.on_render = on_render
        self.message = None

    def render(self):
        self.on_render(self.current_screen, self.message)
        self.message = None

    def up(self):
        self.current_screen.move_up()
        self.render()

    def down(self):
        self.current_screen.move_down()
        self.render()

    def ok(self):
        item = self.current_screen.selected_item()

        if item is None:
            return

        if item.target is not None:
            self.current_screen = item.target
            self.render()
            return

        if item.action is not None:
            self.message = item.action()
            self.render()

    def back(self):
        if self.current_screen.parent is not None:
            self.current_screen = self.current_screen.parent
        else:
            self.message = "Schon im Hauptmenue"

        self.render()
