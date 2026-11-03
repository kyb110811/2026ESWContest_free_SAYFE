"""Fetch pinned upstream code and audio-only dependencies inside this folder."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from AudioDetection.settings import UPSTREAM_COMMIT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',choices=['frame_mn06','frame_mn10'],default='frame_mn06')
    args = parser.parse_args()
    repo = ROOT/'vendor'/'PretrainedSED'
    if not repo.exists():
        repo.parent.mkdir(exist_ok=True)
        subprocess.run(['git','clone','https://github.com/fschmid56/PretrainedSED.git',str(repo)],check=True)
        subprocess.run(['git','-C',str(repo),'checkout',UPSTREAM_COMMIT],check=True)
    revision = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if revision!=UPSTREAM_COMMIT:
        raise RuntimeError('Unexpected vendor revision: '+revision)
    deps = ROOT/'.deps'
    version = subprocess.check_output([sys.executable,'-s','-B','-c',
                                      'import torch; print(torch.__version__.split("+")[0])'],text=True).strip()
    if not (deps/'torchaudio').exists():
        subprocess.run([sys.executable,'-s','-B','-m','pip','install','--no-cache-dir','--no-deps',
                        '--target',str(deps),'torchaudio=='+version,
                        '--index-url','https://download.pytorch.org/whl/cpu'],check=True)
    folder = ROOT/'resources'
    folder.mkdir(exist_ok=True)
    name = args.model+'_strong_1.pt'
    target = folder/name
    if not target.exists():
        temporary = folder/(name+'.download')
        urlretrieve('https://github.com/fschmid56/PretrainedSED/releases/download/v0.0.1/'+name,temporary)
        temporary.replace(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if args.model=='frame_mn06' and digest!='5b8be0664ee194c0413010ae0c6886560f4fd98a9ca1a0c2825e409dfdf33472':
        raise RuntimeError('frame_mn06 checkpoint checksum mismatch')
    (folder/(name+'.json')).write_text(json.dumps(dict(upstream_commit=revision,sha256=digest,
                                                       checkpoint=name,torchaudio_version=version),indent=2))
    print('Ready. Run ./run.sh --check-model, then ./run.sh')


if __name__=='__main__':
    main()
