"""NML helpers shared by all the GRFs in this repo."""
import os


SPRITESET = """spriteset(ss_%(name)s, "gfx/%(file)s.png") {
%(s8)s
}
alternative_sprites(ss_%(name)s, ZOOM_LEVEL_NORMAL, BIT_DEPTH_32BPP, "gfx/%(file)s_1x.png") {
%(s1)s
}
alternative_sprites(ss_%(name)s, ZOOM_LEVEL_IN_2X, BIT_DEPTH_32BPP, "gfx/%(file)s_2x.png") {
%(s2)s
}
alternative_sprites(ss_%(name)s, ZOOM_LEVEL_IN_4X, BIT_DEPTH_32BPP, "gfx/%(file)s_4x.png") {
%(s4)s
}
"""


def write(nml_path, out, lang_dir, lang):
    with open(nml_path, "w") as f:
        f.write("\n".join(out))
    os.makedirs(lang_dir, exist_ok=True)
    with open(os.path.join(lang_dir, "english.lng"), "w") as f:
        f.write("\n".join(lang) + "\n")
