class BaseView:
    def __init__(self, config):
        self.config = config

    def update(self, events, current_time):
        """
        Processes pygame events and updates view/widget state.
        """
        pass

    def draw(self, screen):
        """
        Renders the view layout onto the screen.
        """
        pass
