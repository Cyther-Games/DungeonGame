"""python-for-android's pygame recipe, with one fix.

The stock recipe builds pygame's `surface` module without its SIMD blitter files, so the
app crashes on launch with "cannot locate symbol alphablit_alpha_sse2_argb_surf_alpha"
(python-for-android issue #3405). This runs the stock recipe unchanged, then adds those
files to the build configuration it wrote. On ARM they compile to the plain fallbacks;
they just have to be there so the symbols exist.
"""
import importlib.util
import os
import re

import pythonforandroid
from pythonforandroid.util import current_directory

# python-for-android loads this file under the stock recipe's module name, so the stock
# recipe is loaded from its file instead of imported
_stock_file = os.path.join(os.path.dirname(pythonforandroid.__file__), "recipes", "pygame", "__init__.py")
_spec = importlib.util.spec_from_file_location("_p4a_stock_pygame_recipe", _stock_file)
_stock = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_stock)

_SIMD = "src_c/simd_blitters_sse2.c src_c/simd_blitters_avx2.c"


class PygameWithSimdRecipe(_stock.Pygame2Recipe):
    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            with open("Setup") as f:
                setup = f.read()
            if "simd_blitters_sse2.c" in setup:
                return
            fixed, n = re.subn(r"^(surface\s+)", r"\g<1>" + _SIMD + " ", setup, count=1, flags=re.M)
            if not n:
                raise RuntimeError("pygame recipe fix: no 'surface' line in Setup")
            with open("Setup", "w") as f:
                f.write(fixed)


recipe = PygameWithSimdRecipe()
