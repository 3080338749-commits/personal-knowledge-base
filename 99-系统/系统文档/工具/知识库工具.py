"""Local-only vault maintenance. Python standard library; never changes source material."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess,sys

ROOT=Path(__file__).resolve().parents[3]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def inventory(root):
    result={}
    for p in root.rglob('*'):
        if p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()):raise RuntimeError('Refuse link/junction: '+str(p))
        if p.is_file():result[p.relative_to(root).as_posix()]={'bytes':p.stat().st_size,'sha256':sha(p)}
    return result
def backup(destination):
    parent=Path(destination).expanduser().resolve()
    if parent==ROOT or ROOT in parent.parents:raise ValueError('Backup must be outside the vault')
    parent.mkdir(parents=True,exist_ok=True)
    before=inventory(ROOT)
    size=sum(v['bytes'] for v in before.values())
    if shutil.disk_usage(parent).free<size*2+1024**3:raise RuntimeError('Insufficient backup headroom')
    stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y%m%d-%H%M%S-%f')
    target=parent/ROOT.name/stamp/'vault'
    shutil.copytree(ROOT,target)
    after=inventory(target)
    if before!=after or before!=inventory(ROOT):raise RuntimeError('Backup mismatch/concurrent writes; keep copy for inspection, do not mark verified')
    report={'source':str(ROOT),'backup':str(target),'time':stamp,'files':len(before),'bytes':size,'all_hashes_verified':True,'manifest':before}
    (target.parent/'backup-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='manifest'},ensure_ascii=False,indent=2))
def check():
    baseline=json.loads((ROOT/'99-系统/系统文档/部署前文件基线.json').read_text(encoding='utf-8'))
    content=[x for x in baseline['manifest'] if not x['path'].startswith('.obsidian/')]
    failures=[x['path'] for x in content if not (ROOT/x['path']).is_file() or sha(ROOT/x['path'])!=x['sha256']]
    print(json.dumps({'original_content_files':len(content),'changed_or_missing':failures,'note':'基线用于部署验收；日后有授权编辑时，差异是提示，须结合Git核实，不能自动恢复覆盖。'},ensure_ascii=False,indent=2))
    return 1 if failures else 0
def main():
    if not (ROOT/'.obsidian').is_dir():raise RuntimeError('Run the copy stored inside 系统文档/工具')
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='cmd',required=True)
    b=sub.add_parser('backup');b.add_argument('--destination',required=True)
    sub.add_parser('check')
    sub.add_parser('qmd-update')
    args=parser.parse_args()
    if args.cmd=='backup':backup(args.destination)
    elif args.cmd=='check':return check()
    elif args.cmd=='qmd-update':
        executable=shutil.which('qmd.cmd') or shutil.which('qmd')
        if not executable:raise RuntimeError('QMD not on PATH; install/check npm prefix')
        return subprocess.run([executable,'--index','personal-kb','update'],cwd=ROOT).returncode
    return 0
if __name__=='__main__':sys.exit(main())
