"""python-for-android's SDL2 recipe, always compiled with optimisation.

`buildozer android debug` makes python-for-android build SDL2 - and with it SDL2_ttf
(FreeType), SDL2_image and SDL2_mixer - with NDK_DEBUG=1, i.e. unoptimised (-O0). SDL does
the game's pixel work (copying pictures, filling, drawing text, handing frames to the
screen), so a debug APK ran that part some 30x slower than a PC while the Python side was
only about 2x slower: 2-7 frames a second. This runs the stock recipe with NDK_DEBUG=0, so
a debug APK (still installable without a signing key) gets the fast libraries.
"""
import importlib.util
import os
from os.path import join

import pythonforandroid
import sh
from pythonforandroid.toolchain import current_directory, shprint

# python-for-android loads this file under the stock recipe's module name, so the stock
# recipe is loaded from its file instead of imported
_stock_file = os.path.join(os.path.dirname(pythonforandroid.__file__), "recipes", "sdl2", "__init__.py")
_spec = importlib.util.spec_from_file_location("_p4a_stock_sdl2_recipe", _stock_file)
_stock = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_stock)


class OptimisedSDL2Recipe(_stock.LibSDL2Recipe):
    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        with current_directory(self.get_jni_dir()):
            shprint(sh.Command(join(self.ctx.ndk_dir, "ndk-build")), "V=1", "NDK_DEBUG=0",
                    "APP_OPTIM=release", _env=env)


recipe = OptimisedSDL2Recipe()
