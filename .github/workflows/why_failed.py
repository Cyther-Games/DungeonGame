"""Turn a failed buildozer log into GitHub annotations, which (unlike build logs) anyone
can read on a public repository. Used by android.yml when the build fails."""
import re
import sys

ESC = re.compile(r"\x1b\[[0-9;]*m")
lines = [ESC.sub("", l.rstrip()) for l in open(sys.argv[1], errors="replace")]
stop = next((i for i, l in enumerate(lines) if "Command failed" in l or "Buildozer failed" in l), len(lines))
before = lines[:stop]

ran = [l.strip() for l in before if "RAN:" in l][-1:]
noise = ("grpmodule", "optional modules", "Checking for", "Emscripten", "lld not found", "build-tools folder")
errors = [l for l in before
          if re.search(r"error:|Error:|Exception|fatal|undefined reference|cannot find|No such file|not found", l)
          and not any(n in l for n in noise)]
seen, uniq = set(), []
for l in reversed(errors):
    key = l[-120:]
    if key not in seen:
        seen.add(key)
        uniq.append(l)
uniq.reverse()

text = ([r[:400] for r in ran]
        + ["--- error lines (last 15) ---"] + uniq[-15:]
        + ["--- the 45 lines before it stopped (line %d) ---" % stop] + before[-45:])
text = [l[:240] for l in text]

# one annotation holds about 4 KB; split into up to 8
chunks, cur = [], ""
for l in text:
    if len(cur) + len(l) + 1 > 3800:
        chunks.append(cur)
        cur = ""
    cur += l + "\n"
chunks.append(cur)
for n, c in enumerate(chunks[:8], 1):
    msg = c.replace("%", "%25").replace("\r", "").replace("\n", "%0A")
    print("::error title=Android build failed (%d/%d)::%s" % (n, min(len(chunks), 8), msg))
