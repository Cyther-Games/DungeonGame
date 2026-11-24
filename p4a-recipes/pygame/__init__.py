"""python-for-android's pygame recipe, with two fixes.

1. pygame 2.6.1 instead of the stock 2.1.0, whose pre-generated C code no longer compiles
   with current Python ("longintrepr.h file not found"). 2.6.1's Android build template
   has the same placeholders, so the stock recipe's build steps still fit.
2. The stock recipe builds pygame's `surface` module without its SIMD blitter files, so
   the app crashes on launch with "cannot locate symbol alphablit_alpha_sse2_argb_surf_alpha"
   (python-for-android issue #3405). This runs the stock recipe unchanged, then adds those
   files to the build configuration it wrote. (On 64-bit ARM they hold the NEON versions.)
"""
import importlib.util
import os
import re

import pythonforandroid
from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory

# python-for-android loads this file under the stock recipe's module name, so the stock
# recipe is loaded from its file instead of imported
_stock_file = os.path.join(os.path.dirname(pythonforandroid.__file__), "recipes", "pygame", "__init__.py")
_spec = importlib.util.spec_from_file_location("_p4a_stock_pygame_recipe", _stock_file)
_stock = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_stock)

_SIMD = "src_c/simd_blitters_sse2.c src_c/simd_blitters_avx2.c"


class PygameWithSimdRecipe(_stock.Pygame2Recipe):
    version = "2.6.1"
    # pygame's source (unlike 2.1.0's) leaves its Cython modules to be generated at build
    # time, so the build's own Python needs Cython - the 3.0 series 2.6.1 was released with
    hostpython_prerequisites = ["setuptools", "Cython>=3.0.10,<3.1"]

    def get_recipe_env(self, arch):
        # pygame does its own pixel work (blending, scaling): make sure it's compiled
        # optimised whatever flags the build's Python hands down
        env = super().get_recipe_env(arch)
        env["CFLAGS"] = (env.get("CFLAGS", "") + " -O3 -DNDEBUG").strip()
        return env

    def build_compiled_components(self, arch):
        # install Cython just before compiling; the build's Python is only set up by now
        if getattr(self, "_host_recipe", None) is None:
            self._host_recipe = Recipe.get_recipe("hostpython3", self.ctx)
        self.install_hostpython_prerequisites()
        super().build_compiled_components(arch)

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
