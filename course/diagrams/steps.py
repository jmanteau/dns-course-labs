"""Export full-dns-sequence.drawio one step at a time, for the step-by-step slide.

Step n shows the messages of steps 1..n; later messages are made transparent rather
than deleted, so every PNG keeps the same bounding box and the images stack exactly.
Usage: python3 diagrams/steps.py <drawio binary>
"""
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

SOURCE = "diagrams/full-dns-sequence.drawio"
STEPS = [[], ["s0", "start"], ["s1"], ["s2"], ["s3"], ["s4"], ["s5"], ["s6"], ["end", "s7"]]
HIDDEN = ";opacity=0;textOpacity=0;labelBackgroundColor=none;"

drawio = sys.argv[1]
for n in range(len(STEPS)):
    later = {cell for step in STEPS[n + 1:] for cell in step}
    tree = ET.parse(SOURCE)
    for cell in tree.iter("mxCell"):
        if cell.get("id") in later:
            cell.set("style", cell.get("style", "") + HIDDEN)
    with tempfile.NamedTemporaryFile("wb", suffix=".drawio", delete=False) as tmp:
        tree.write(tmp, encoding="utf-8", xml_declaration=True)
    output = f"images/full-dns-sequence-step{n}.png"
    subprocess.run([drawio, "-x", "-f", "png", "-s", "2", "-o", output, tmp.name], check=True)
    os.unlink(tmp.name)
