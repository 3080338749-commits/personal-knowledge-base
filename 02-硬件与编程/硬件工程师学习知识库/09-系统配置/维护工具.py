"""硬件知识库维护：仅标准库。默认只读 check；refresh/commit 明确写入。"""
from pathlib import Path
from datetime import datetime,date,timedelta,timezone
import json,hashlib,re,os,shutil,argparse,sys
ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/'09-系统配置'
BACKUP_BASE=Path(r'D:\obsidian\backups\硬件工程师学习知识库_历史版本备份库')
STATE=CFG/'学习状态.json'
TZ=timezone(timedelta(hours=9))  # Asia/Tokyo，2026-11-03 起；此前 +08:00
START='<!-- hardware-managed:start -->'
END='<!-- hardware-managed:end -->'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,text):
 tmp=p.with_name(p.name+'.tmp');tmp.write_text(text,encoding='utf-8');os.replace(tmp,p)
def valid(s,cat):
 errors=[];ids={c['id'] for c in cat}
 if s.get('schema_version')!=1:errors.append('schema_version必须为1')
 if set(s.get('units',{}))!=ids:errors.append('章节ID集合与课程目录不符')
 for id,u in s.get('units',{}).items():
  if u.get('status') not in ['未开始','学习中','内容学完待测验','已完成']:errors.append(id+'状态非法')
  if u.get('status')=='已完成' and (not u.get('evidence') or not u.get('completed_at')):errors.append(id+'完成缺少证据或日期')
  if u.get('note') and not (ROOT/u['note']).is_file():errors.append(id+'章节笔记不存在')
 for key in ['current_unit_id','next_unit_id']:
  if s.get(key) is not None and s[key] not in ids:errors.append(key+'引用不存在')
 for key in ['knowledge','questions','errors','sessions','reviews','tasks']:
  items=s.get(key,[]);itemids=[x.get('id') for x in items]
  if len(itemids)!=len(set(itemids)) or None in itemids:errors.append(key+'缺少ID或重复ID')
 kids={k['id'] for k in s.get('knowledge',[])}
 for k in s.get('knowledge',[]):
  if k.get('level') not in [None,0,1,2,3,4]:errors.append(k['id']+'等级非法')
  if k.get('level') is not None and k['level']>0 and not k.get('evidence'):errors.append(k['id']+'等级缺评估证据')
  for field in ['due','learned_at']:
   if k.get(field):
    try:date.fromisoformat(k[field])
    except ValueError:errors.append(k['id']+field+'日期非法')
  if k.get('due') and not k.get('learned_at'):errors.append(k['id']+'未学习却安排复习')
  if k.get('due') and k.get('learned_at') and k['due']<k['learned_at']:errors.append(k['id']+'复习早于学习日期')
  if k.get('unit_id') not in ids:errors.append(k['id']+'缺少有效章节ID')
  if not k.get('note'):errors.append(k['id']+'缺少知识笔记路径')
 for key in ['errors','reviews']:
  for item in s.get(key,[]):
   if item.get('knowledge_id') not in kids:errors.append(item['id']+'知识ID不存在')
 for x in s.get('sessions',[]):
  if x.get('unit_id') not in ids:errors.append(x['id']+'章节ID不存在')
 q=s.get('quiz')
 if q:
  if q.get('unit_id') not in ids:errors.append('测验章节ID无效')
  if q.get('status') not in ['进行中','已完成','已中断']:errors.append('测验状态非法')
  for a in q.get('answers',[]):
   if not a.get('user_answer') or not a.get('question'):errors.append('测验作答缺原文')
 for key in ['knowledge','sessions']:
  for x in s.get(key,[]):
   if x.get('note') and not (ROOT/x['note']).is_file():errors.append('笔记不存在:'+x['note'])
 if errors:raise ValueError('\n'.join(errors))
def wt(p,title,body):
 p=ROOT/p;block=START+'\n'+body.strip()+'\n'+END
 if p.exists():
  old=p.read_text('utf-8')
  if START not in old or END not in old:raise ValueError('缺少派生区标记，拒绝覆盖:'+str(p))
  new=old[:old.index(START)]+block+old[old.index(END)+len(END):]
 else:new=f'---\ntitle: "{title}"\ntype: generated-view\ncreated: 2026-10-16\ntags: [硬件学习]\n---\n\n# {title}\n\n'+block+'\n\n## 我的补充\n\n此区可自由补充，刷新时保留。\n'
 if p.name in ['学习仪表盘.md','硬件学习主页.md'] and 'hardware-study-dashboard' not in new.split('---',2)[1]:
  new=new.replace('type: generated-view\n','type: generated-view\ncssclasses: [hardware-study-dashboard]\n',1)
 atomic(p,new)
def table(headers,rs,empty='暂无记录。'):
 def cell(x):
  s=str(x if x is not None else '待评估').replace('\n',' ')
  parts=re.split(r'(\[\[.*?\]\])',s)
  for i in range(0,len(parts),2):parts[i]=parts[i].replace('|','\\|')
  return ''.join(parts)
 return ('| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(cell(x) for x in r)+' |' for r in rs)) if rs else empty
def wiki(path,label=None):
 return '[['+str(path).removesuffix('.md')+(('|'+label) if label else '')+']]'
def dashboard_hub(s,cat,today):
 C={c['id']:c for c in cat};units=s['units'];total=len(cat)
 completed=sum(x['status']=='已完成' for x in units.values())
 learned=[k for k in s['knowledge'] if k.get('learned_at')]
 mastered=[k for k in learned if k.get('level') in [3,4]]
 assessed=[k for k in learned if k.get('level') is not None]
 due=[k for k in learned if k.get('due') and k['due']<=today.isoformat()]
 overdue=[k for k in due if k['due']<today.isoformat()]
 nextid=s.get('current_unit_id') or s.get('next_unit_id')
 target=nextid+' '+C[nextid]['title'] if nextid in C else '全部课程单元已完成'
 rate=completed/total*100 if total else 0
 mastery=f'{len(mastered)} / {len(learned)}' if assessed else '待评估'
 review=f'{len(due)} 项待复习 · 其中 {len(overdue)} 项逾期' if due else '暂无到期复习'
 review_hint='优先薄弱知识与错题，输入“开始今日复习”。' if due else ('按实际学习与答题情况安排下一次复习。' if learned else '完成首次学习与测验后，生成间隔复习计划。')
 subtitle='当前正在学习' if s.get('current_unit_id') else '下一节建议学习'
 source='基础篇-01.pdf · 第 2–12 页' if nextid=='B01' else '打开课程目录查看对应资料与页段。'
 lines=f'''[!hw-hub] 硬件工程师学习中心
课程 · 知识 · 测验 · 复习 · 实践

> [!hw-metrics]
> > [!hw-stat] 课程进度
> > **{rate:.0f}%**
> >
> > 已完成 {completed} / {total} 个学习单元
>
> > [!hw-stat] 知识掌握情况
> > **{mastery}**
> >
> > {'依据实际测验 · 3–4级计确认掌握' if assessed else '依据实际测验 · 尚无评估记录'}

### 今日学习安排

> [!hw-task] {subtitle}
> {target}
>
> {source}

> [!hw-review] 今日知识复习
> {review}
>
> {review_hint}

---

### 知识库导航

- [[00-学习中心/课程路线与总目录|课程路线与总目录]]
- [[00-学习中心/章节进度索引|章节进度索引]]
- [[01-课程知识库/01-基础知识培训/01-基础知识导学与进度|基础知识导学]]
- [[02-核心知识卡片/知识卡片动态索引|核心知识卡片]]
- [[03-复盘与错题集/错题本|疑难与错题]]
- [[03-复盘与错题集/知识掌握情况|掌握情况分析]]
- [[03-复盘与错题集/复习计划|间隔复习计划]]
- [[00-学习中心/知识库使用与维护指南|使用与维护指南]]

统计日期 {today.isoformat()} · 状态版本 {s['revision']} · [[00-学习中心/日常快捷指令|日常指令]]
'''
 return '\n'.join('> '+line if line else '>' for line in lines.splitlines())


def render(s,cat,today):
 C={c['id']:c for c in cat};ks=s['knowledge'];done=[i for i,u in s['units'].items() if u['status']=='已完成'];n=len(cat);rate=len(done)/n*100 if n else 0
 name=lambda id: id+' '+C[id]['title'] if id in C else '未开始'
 target=s.get('current_unit_id') or s.get('next_unit_id');current=name(s.get('current_unit_id'));nextname=name(s.get('next_unit_id'))
 learned=[k for k in ks if k.get('learned_at')];due=[k for k in learned if k.get('due') and k['due']<=today.isoformat()];over=[k for k in due if k['due']<today.isoformat()]
 weak=[k for k in learned if k.get('level') in [0,1]];high=[k for k in learned if k.get('level') in [3,4]]
 unanswered=[q for q in s['questions'] if q.get('status')!='已解决'];repeat=[k for k in ks if sum(1 for e in s['errors'] if e.get('knowledge_id')==k['id'])>=2]
 stamp=f"统计日期：{today.isoformat()}（Asia/Tokyo） · 状态版本：{s['revision']} · 事实更新时间：{s['updated_at']}"
 progress='█'*int(rate/5)+'░'*(20-int(rate/5))+f' {rate:.1f}%'
 krows=lambda items:[[wiki(k['note'],k['title']),k.get('level') if k.get('level') is not None else '待评估',k.get('due') or '尚未安排'] for k in items]
 recent=sorted(s['sessions'],key=lambda x:x.get('date',''),reverse=True)[:5]
 logrows=[[x.get('date'),name(x['unit_id']),x.get('content',''),x.get('quiz_summary','未测验'),x.get('issues','无已记录问题')] for x in recent]
 q=s.get('quiz');qtext=('尚无测验记录' if not q else f"{name(q['unit_id'])}；{q['status']}；已保存{len(q.get('answers',[]))}题；{q.get('summary') or '结果待完成后评估'}")
 reviewrows=[[wiki(k['note'],k['title']),k['due'],'逾期' if k['due']<today.isoformat() else '今日到期'] for k in sorted(due,key=lambda k:(k.get('level') if k.get('level') is not None else 9,k['due']))]
 modules=[[m,sum(s['units'][c['id']]['status']=='已完成' for c in cat if c['module']==m),sum(c['module']==m for c in cat)] for m in dict.fromkeys(c['module'] for c in cat)]
 nav=' · '.join(wiki(t) for t in ['00-学习中心/课程路线与总目录','00-学习中心/章节进度索引','01-课程知识库/01-基础知识培训/01-基础知识导学与进度','02-核心知识卡片/知识卡片动态索引','03-复盘与错题集/错题本','03-复盘与错题集/疑难问题库','03-复盘与错题集/复习计划','03-复盘与错题集/当前学习状态','03-复盘与错题集/学习日志','00-学习中心/知识库使用与维护指南','00-学习中心/日常快捷指令'])
 reason='先了解工程职责与研发流程，再进入电阻器件手册；便于把已有STM32经验放进完整硬件设计流程。' if target=='B01' else '按未完成任务、到期薄弱点及课程前置关系推荐；具体范围在会话开始时确认。'
 points='硬件岗位职责、所需技能、硬件研发流程；基础篇-01.pdf 第2–12页。' if target=='B01' else (('来源：'+', '.join(C[target]['source_ids'])+'；页段：'+str(C[target].get('pages') or '正文待定位')) if target else '全部映射单元已完成，可选择复习或实践。')
 dashboard=f'''> [!tip] 今天从这里开始
> 建议：**{name(target)}**。在Codex项目中输入“继续硬件课程学习”。
> 首次使用先打开 [[知识库使用与维护指南]]。

{stamp}

## 课程总览

`{progress}`

'''+table(['指标','当前值'],[['大模块（已完成/总数）',f'{sum(row[1]==row[2] for row in modules)}/3'],['映射学习单元（已完成/总数）',f'{len(done)}/{n}'],['当前学习章节',current],['已学习知识点',len(learned)],['已确认掌握（3–4级）',len(high)],['到期/逾期待复习',len(due)],['未解决问题',len(unanswered)]])+'''

完成率按70个映射单元等权计算，非时长进度。物联网官方课时表为40节，基础18主题与交换机12主题为讲义映射。

'''+table(['模块','已完成单元','总单元'],modules)+f'''

## 当前学习任务

- 当前章节：{current}
- 最近完成：{s.get('last_completed') or '尚无学习记录'}
- 下一节：{nextname}
- 推荐理由：{reason}
- 本次关键范围：{points}
- 待完成：{'; '.join(t.get('title','') for t in s['tasks'] if t.get('status')!='已完成') or '首次学习尚未开始；暂无遗留任务'}

## 知识掌握

'''+table(['等级','含义','数量'],[[str(l),'未学习' if l==0 else ['','已接触但理解不足','能解释基础概念','能独立回答分析','能综合应用'][l],sum(k.get('level')==l for k in ks)] for l in range(5)]+[['待评估','尚无充分答题证据',sum(k.get('level') is None for k in ks)]])+f'''

知识点数量仅统计已建记录；未拆解的课程主题不虚计为0级知识点。

薄弱知识：{', '.join(wiki(k['note'],k['title']) for k in weak) or '暂无已评估的薄弱知识，整体待评估'}

反复答错：{', '.join(wiki(k['note'],k['title']) for k in repeat) or '暂无已记录的反复错题'}

较高掌握：{', '.join(wiki(k['note'],k['title']) for k in high) or '尚无确认记录'}

## 今日复习

'''+table(['知识点','到期日','状态'],reviewrows,'暂无到期任务；尚未产生学习后的复习安排。')+f'''

逾期：{len(over)}项。优先错题：{', '.join(wiki(k['note'],k['title']) for k in weak if k in due) or '暂无到期薄弱项'}。

最近复习：{s['reviews'][-1].get('result','待评估') if s['reviews'] else '尚无复习记录'}

## 最近测验

{qtext}

## 最近5次学习

'''+table(['日期','章节','内容','测验','问题'],logrows)+f'''

## 快捷入口

{nav}

> [!info] 更新边界
> 这是原生Markdown快照。Codex保存学习数据后会运行维护工具同步计算；跨日需输入“更新学习仪表盘”。Codex关闭后不持续运行，Obsidian本身不会重新计算这些数据。
'''
 dashboard_full=dashboard_hub(s,cat,today)+'\n\n## 日常三步\n\n1. 在Codex本项目输入“继续硬件课程学习”。\n2. 学习后说“今天学完了”，逐题回答测验。\n3. 保存后回到 [[硬件学习主页]] 核对进度。\n\n> [!info]- 展开完整学习数据\n'+'\n'.join('> '+line if line else '>' for line in dashboard.splitlines())
 wt('00-学习中心/硬件学习主页.md','硬件学习主页',dashboard_full)
 wt('00-学习中心/章节进度索引.md','章节进度索引',stamp+'\n\n'+table(['ID','原文标题/主题','状态','完成日期','笔记'],[[c['id'],c['title'],s['units'][c['id']]['status'],s['units'][c['id']].get('completed_at') or '—',wiki(s['units'][c['id']]['note']) if s['units'][c['id']].get('note') else '尚未创建'] for c in cat]))
 wt('03-复盘与错题集/当前学习状态.md','当前学习状态',stamp+'\n\n'+table(['项目','状态'],[['当前学习章节',current],['当前学习状态','未开始' if not s.get('current_unit_id') else s['units'][s['current_unit_id']]['status']],['最近学习时间',s.get('last_learning_at') or '尚无'],['最近完成内容',s.get('last_completed') or '尚无'],['待学习内容',nextname],['待解决问题',len(unanswered)],['当前测验',qtext],['待复习知识点',len(due)],['下一次建议',name(target)],['最新更新',s['updated_at']]])+'\n\n[[00-学习中心/课程路线与总目录|课程路线与总目录]] · [[00-学习中心/硬件学习主页|硬件学习主页]] · [[03-复盘与错题集/复习计划|复习计划]]')
 wt('03-复盘与错题集/学习日志.md','学习日志',stamp+'\n\n初始化操作不计入课程学习日志。\n\n'+table(['日期','章节','内容','测验','问题'],[[x.get('date'),name(x['unit_id']),x.get('content',''),x.get('quiz_summary','未测验'),x.get('issues','无记录')] for x in sorted(s['sessions'],key=lambda x:x.get('date',''),reverse=True)]))
 wt('03-复盘与错题集/知识掌握情况.md','知识掌握情况',stamp+'\n\n等级0未学习，1理解不足，2解释概念，3独立分析，4综合应用；null待评估。3–4计确认掌握。\n\n'+table(['知识笔记','等级','下次复习'],krows(ks),'知识点尚未建立，整体待评估。'))
 wt('03-复盘与错题集/复习计划.md','复习计划',stamp+'\n\n初次实际学习后，按相对学习日的第1、3、7、14、30天安排。具体晋级与重排见 [[09-系统配置/规范文档/知识库维护规则|知识库维护规则]]。无学习记录不生成空任务。\n\n'+table(['知识点','到期日','状态'],reviewrows)+'\n\n全部未来复习：\n\n'+table(['知识笔记','等级','下次复习'],krows([k for k in ks if k.get('due') and k['due']>today.isoformat()]))+'\n\n[[03-复盘与错题集/复习记录|复习记录]]')
 wt('03-复盘与错题集/复习记录.md','复习记录',stamp+'\n\n'+table(['日期','知识ID','实际结果','下一日期'],[[x.get('date'),x.get('knowledge_id'),x.get('result'),x.get('next_due')] for x in s['reviews']]))
 wt('03-复盘与错题集/疑难问题库.md','疑难问题库',stamp+'\n\n'+table(['ID','问题','章节','状态'],[[x['id'],x.get('question'),x.get('unit_id'),x.get('status')] for x in s['questions']]))
 wt('03-复盘与错题集/错题本.md','错题本',stamp+'\n\n只记录真实作答。保留题干、本人回答、引导过程、正确思路、知识ID与来源；重复答错追加事件，不覆盖历史。\n\n'+table(['ID','日期','知识','题干','本人回答','纠正与追问','状态'],[[x['id'],x.get('date'),x.get('knowledge_id'),x.get('question'),x.get('user_answer'),x.get('correction'),x.get('status')] for x in s['errors']]))
 wt('03-复盘与错题集/薄弱知识清单.md','薄弱知识清单',stamp+'\n\n'+table(['知识笔记','等级','复习日期'],krows(weak),'暂无已评估薄弱知识；未测验不等于没有薄弱点。'))
 wt('01-课程知识库/课程笔记动态索引.md','课程笔记动态索引',table(['章节','笔记'],[[name(id),wiki(u['note'])] for id,u in s['units'].items() if u.get('note')]))
 wt('02-核心知识卡片/知识卡片动态索引.md','知识卡片动态索引',table(['知识ID','卡片'],[[k['id'],wiki(k['note'],k['title'])] for k in ks]))
def audit(s,cat,source=False):
 valid(s,cat);broken=[];md=[p for p in ROOT.rglob('*.md') if '备份' not in p.parts and '缓存与归档' not in p.parts and not p.name.startswith('知识库重构')];byname={}
 for p in md:byname.setdefault(p.stem,[]).append(p)
 for p in md:
  t=re.sub(r'```.*?```','',p.read_text('utf-8'),flags=re.S)
  for raw in re.findall(r'\[\[([^\]]+)\]\]',t):
   target=raw.replace('\\|','|').split('|')[0].split('#')[0].strip()
   if target and not (ROOT/(target+'.md')).exists() and not (ROOT/target).exists() and target not in byname:broken.append(str(p.relative_to(ROOT))+': '+target)
 duplicates=[name for name,paths in byname.items() if len(paths)>1]
 changes=[]
 if source:
  inv=read(CFG/'资料清单.json');known={Path(x['path']).resolve():x for x in inv};root=Path(s['source_root'])
  if not root.is_dir():changes.append('原始资料目录失效:'+str(root))
  else:
   for p in root.rglob('*'):
    if p.is_file():
     old=known.pop(p.resolve(),None)
     if not old:changes.append('新增:'+str(p))
     elif digest(p)!=old.get('sha256'):changes.append('内容改变，旧解析作废待重读:'+str(p))
   changes.extend('原文件缺失:'+str(p) for p in known)
 return dict(state_valid=True,markdown_files=len(md),broken_links=broken,duplicate_titles=duplicates,source_changes=changes,state_sha256=digest(STATE))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['check','refresh','commit']);ap.add_argument('--input',type=Path);ap.add_argument('--expected-sha');ap.add_argument('--as-of');ap.add_argument('--sources',action='store_true');args=ap.parse_args()
 s=read(STATE);cat=read(CFG/'课程目录.json');today=date.fromisoformat(args.as_of) if args.as_of else datetime.now(TZ).date()
 if args.action=='check':
  report=audit(s,cat,args.sources);print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(1 if report['broken_links'] or report['duplicate_titles'] else 0)
 lock=CFG/'.maintenance.lock'
 fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
 try:
  pending=CFG/'待恢复事务.json'
  if pending.exists():raise ValueError('存在未完成事务，先读取待恢复事务与备份并核对，禁止覆盖')
  valid(s,cat);oldsha=digest(STATE)
  if args.action=='commit':
   if not args.input or args.expected_sha!=oldsha:raise ValueError('需要候选状态及当前expected-sha；版本不符时重新读取合并')
   candidate=read(args.input);valid(candidate,cat)
   if candidate['revision']!=s['revision']+1:raise ValueError('候选revision必须严格加1')
   s=candidate
  # 备份状态与所有Markdown，保留可恢复的完整派生视图。
  b=BACKUP_BASE/datetime.now(TZ).strftime('%Y%m%d-%H%M%S-%f');b.mkdir(parents=True,exist_ok=True)
  for p in [STATE]+[p for p in ROOT.rglob('*.md') if '缓存与归档' not in p.parts]:
   dest=b/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
  if digest(STATE)!=oldsha:raise ValueError('检测到并发修改，已中止，请合并后重试')
  atomic(pending,json.dumps({'action':args.action,'backup':str(b),'expected_old_sha':oldsha,'target_revision':s['revision']},ensure_ascii=False,indent=2))
  if args.action=='commit':atomic(STATE,json.dumps(s,ensure_ascii=False,indent=2)+'\n')
  render(s,cat,today)
  report=audit(s,cat,args.sources)
  if report['broken_links'] or report['duplicate_titles']:raise ValueError(json.dumps(report,ensure_ascii=False))
  pending.unlink();report['backup']=str(b);print(json.dumps(report,ensure_ascii=False,indent=2))
 finally:lock.unlink(missing_ok=True)
if __name__=='__main__':main()
