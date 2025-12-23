from PIL.ImageFile import ImageFile
from inky.auto import auto


class InkyRenderer:
    def __init__(self) -> None:
        self._display = auto()
        self._print_screen_info()

    def _print_screen_info(self):
        print(f"Inky Display: {self._display.resolution} Color: {self._display.colour}")

    def render(self, img: ImageFile, saturation: float, contrast: float):
        # Convert color palette to something Inky better understands
        self._display.set_image(img, saturation=saturation)
        self._display.show()
