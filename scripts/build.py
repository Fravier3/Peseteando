"""Publish only public app files; omit source scripts, tests and repository metadata."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
DIST.mkdir(exist_ok=True)
for name in ['index.html','styles.css','app.js','catalog.mjs','manifest.webmanifest','sw.js','offers.json','assets']:
    source=ROOT/name
    if source.is_dir(): shutil.copytree(source,DIST/name,dirs_exist_ok=True)
    else: shutil.copy2(source,DIST/name)
(DIST/'.nojekyll').touch()
print('App preparada en dist/')
