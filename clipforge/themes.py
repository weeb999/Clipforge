"""ASS style presets; colors use ASS BGR order."""
from dataclasses import dataclass

FONTS = ["Montserrat", "Poppins", "Bebas Neue", "Anton", "Oswald", "Bangers", "Roboto Condensed", "Inter", "Playfair Display", "Lobster", "Luckiest Guy", "Archivo Black", "Permanent Marker"]


@dataclass(frozen=True)
class Theme:
    color: str = "&H00FFFFFF"
    highlight: str = "&H0000FFFF"
    outline_color: str = "&H00000000"
    stroke: int = 4
    shadow: int = 2
    alignment: int = 2
    box: bool = False
    animation: str = "pop"


THEMES = {
    "Editorial": Theme(highlight="&H00CBDF95", stroke=2, shadow=1, animation="steady"),
    "Cinema": Theme(color="&H00F4F5FC", highlight="&H009DD2F5", stroke=2, shadow=2, animation="steady"),
    "Minimal": Theme(highlight="&H00FFFFFF", stroke=3, shadow=1, animation="steady"),
    "Classic White": Theme(animation="fade"),
    "Yellow Pop": Theme(color="&H0000FFFF", highlight="&H00FFFFFF"),
    "Neon Glow": Theme(highlight="&H00FF00FF", outline_color="&H00880066", stroke=5, shadow=5, animation="glow"),
    "Minimal Black Box": Theme(box=True, stroke=12, shadow=0, animation="fade"),
    "Gradient Karaoke": Theme(color="&H00FFDD99", highlight="&H00FF66FF", animation="gradient"),
    "Comic Bold": Theme(highlight="&H0000FFFF", stroke=7, shadow=4, alignment=5),
    "Cinematic Lower-Third": Theme(highlight="&H00DDDDDD", stroke=2, shadow=1, animation="slide"),
    "Hormozi-style": Theme(highlight="&H0000FF00", stroke=6, shadow=3),
}
