"""Local-only task scanner, Windows 08:30 toast reminder, and .ics exporter.

Read-only on vault Markdown files; uses Python 3.12 standard library only.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import html
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ICS = Path(__file__).resolve().parent / "输出" / "tasks.ics"
TASK_NAME = "PersonalKB-DailyReminder"
BEIJING_TZ = datetime.timezone(datetime.timedelta(hours=8))

EXCLUDED_DIRS = {
    ".git",
    ".obsidian",
    ".qmd",
    "99-系统",
    "09-系统配置",
    "备份",
    "输出",
    "__pycache__",
}

TASK_RE = re.compile(r"^\s*-\s+\[\s\]\s+(?P<body>.+?)\s*$")
DUE_RE = re.compile(r"📅\s*(\d{4}-\d{2}-\d{2})")
SCHED_RE = re.compile(r"⏳\s*(\d{4}-\d{2}-\d{2})")
FENCE_RE = re.compile(r"^\s*(```|~~~)")

PRIORITY_MAP = {
    "⏫": (1, "高", 1),
    "🔼": (2, "中", 5),
    "🔽": (4, "低", 9),
}


@dataclass(frozen=True)
class TaskItem:
    title: str
    due_date: datetime.date
    priority_rank: int
    priority_label: str
    ics_priority: int
    source_rel: str
    line_no: int


def is_excluded(path: Path) -> bool:
    rel_parts = path.relative_to(ROOT).parts
    return any(part in EXCLUDED_DIRS or "备份" in part for part in rel_parts)


def clean_task_title(raw_body: str) -> str:
    cleaned = re.sub(r"[📅⏳🛫➕✅]\s*\d{4}-\d{2}-\d{2}", "", raw_body)
    cleaned = re.sub(r"[⏫🔼🔽🔁]", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def detect_priority(raw_body: str) -> tuple[int, str, int]:
    for marker, values in PRIORITY_MAP.items():
        if marker in raw_body:
            return values
    return (3, "普通", 5)


def scan_dated_tasks() -> list[TaskItem]:
    """Scan vault markdown files for unchecked tasks with an explicit date."""
    tasks: list[TaskItem] = []
    for md_path in sorted(ROOT.rglob("*.md")):
        if is_excluded(md_path):
            continue
        in_fence = False
        try:
            lines = md_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = md_path.relative_to(ROOT).as_posix()
        for idx, line in enumerate(lines, start=1):
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            match = TASK_RE.match(line)
            if not match:
                continue
            body = match.group("body")
            date_match = DUE_RE.search(body) or SCHED_RE.search(body)
            if not date_match:
                continue
            try:
                due = datetime.date.fromisoformat(date_match.group(1))
            except ValueError:
                continue
            rank, label, ics_prio = detect_priority(body)
            title = clean_task_title(body)
            if not title:
                continue
            tasks.append(
                TaskItem(
                    title=title,
                    due_date=due,
                    priority_rank=rank,
                    priority_label=label,
                    ics_priority=ics_prio,
                    source_rel=rel,
                    line_no=idx,
                )
            )
    tasks.sort(key=lambda t: (t.due_date, t.priority_rank, t.source_rel, t.line_no))
    return tasks


def ics_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", r"\,")
        .replace("\n", r"\n")
    )


def export_ics(tasks: list[TaskItem], out_path: Path, event_hour: int = 9) -> Path:
    """Export dated tasks to an RFC 5545 .ics file for OriginOS/Android import."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PersonalKB//DailyTaskExporter//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:个人知识库待办",
    ]
    for idx, task in enumerate(tasks, start=1):
        start_dt = datetime.datetime.combine(
            task.due_date, datetime.time(hour=event_hour, minute=0)
        )
        end_dt = start_dt + datetime.timedelta(minutes=30)
        uid = f"kb-{task.due_date.strftime('%Y%m%d')}-{idx}-{abs(hash((task.source_rel, task.title))) % 10**8}@personalkb.local"
        desc = f"优先级: {task.priority_label}\\n来源: {task.source_rel}:{task.line_no}"
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{ics_escape(f'[{task.priority_label}] {task.title}')}",
                f"DESCRIPTION:{ics_escape(desc)}",
                f"PRIORITY:{task.ics_priority}",
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{ics_escape(task.title)}",
                "TRIGGER:-PT30M",
                "END:VALARM",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    out_path.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
    return out_path


def build_summary(tasks: list[TaskItem], today: datetime.date) -> tuple[str, str]:
    overdue = [t for t in tasks if t.due_date < today]
    due_today = [t for t in tasks if t.due_date == today]
    upcoming = [
        t for t in tasks if today < t.due_date <= today + datetime.timedelta(days=3)
    ]

    headline = f"知识库早间提醒 ({today.isoformat()})"
    lines: list[str] = []
    if overdue:
        lines.append(f"逾期 {len(overdue)} 项：" + "；".join(t.title for t in overdue[:2]))
    if due_today:
        lines.append(
            f"今日到期 {len(due_today)} 项：" + "；".join(t.title for t in due_today[:3])
        )
    if upcoming and not (overdue or due_today):
        lines.append(
            f"未来3天待办 {len(upcoming)} 项："
            + "；".join(f"{t.due_date.strftime('%m-%d')} {t.title}" for t in upcoming[:2])
        )
    if not lines:
        lines.append("今日暂无带日期的到期任务，按周课表节奏专注科研主线即可。")
    return headline, "\n".join(lines)


def show_windows_toast(title: str, body: str) -> int:
    """Display a native Windows 10/11 Toast notification via PowerShell WinRT."""
    safe_title = html.escape(title)
    safe_body = html.escape(body)
    ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml(@"
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>{safe_title}</text>
      <text>{safe_body}</text>
    </binding>
  </visual>
</toast>
"@)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Windows PowerShell")
$notifier.Show($toast)
"""
    encoded = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
    res = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-WindowStyle",
            "Hidden",
            "-EncodedCommand",
            encoded,
        ],
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if res.returncode != 0 and res.stderr:
        sys.stderr.write(res.stderr.decode("gbk", errors="replace"))
    return res.returncode


def register_daily_task(time_hhmm: str = "08:30") -> int:
    """Register or update the daily Windows Task Scheduler reminder."""
    py_exe = Path(sys.executable)
    pythonw = py_exe.with_name("pythonw.exe")
    runner = pythonw if pythonw.is_file() else py_exe
    script_path = Path(__file__).resolve()
    cmd = f'"{runner}" "{script_path}" --toast'
    res = subprocess.run(
        [
            "schtasks",
            "/Create",
            "/F",
            "/SC",
            "DAILY",
            "/ST",
            time_hhmm,
            "/TN",
            TASK_NAME,
            "/TR",
            cmd,
        ],
        capture_output=True,
    )
    if res.stdout:
        print(res.stdout.decode("gbk", errors="replace").strip())
    if res.stderr:
        sys.stderr.write(res.stderr.decode("gbk", errors="replace"))
    return res.returncode


def print_report(tasks: list[TaskItem], today: datetime.date, ics_path: Path) -> None:
    overdue = [t for t in tasks if t.due_date < today]
    due_today = [t for t in tasks if t.due_date == today]
    upcoming = [t for t in tasks if t.due_date > today]
    print(f"扫描完成（{today.isoformat()}）：共发现 {len(tasks)} 条带日期未完成任务")
    for label, group in [("逾期", overdue), ("今日到期", due_today), ("未来计划", upcoming)]:
        if not group:
            continue
        print(f"\n[{label}] ({len(group)})")
        for t in group:
            print(f"  - {t.due_date.isoformat()} [{t.priority_label}] {t.title}  ({t.source_rel}:{t.line_no})")
    print(f"\n已导出日历文件: {ics_path}")


def main() -> int:
    if not (ROOT / ".obsidian").is_dir():
        raise RuntimeError("请从 D:\\个人知识库\\99-系统\\系统文档\\工具 目录运行本脚本")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ics", type=Path, default=DEFAULT_ICS, help="输出 .ics 路径")
    parser.add_argument("--toast", action="store_true", help="发送 Windows 桌面通知")
    parser.add_argument(
        "--register-task",
        nargs="?",
        const="08:30",
        metavar="HH:MM",
        help="注册 Windows 每日定时提醒任务（默认 08:30）",
    )
    args = parser.parse_args()

    if args.register_task:
        return register_daily_task(args.register_task)

    today = datetime.datetime.now(BEIJING_TZ).date()
    tasks = scan_dated_tasks()
    ics_path = export_ics(tasks, args.ics)
    print_report(tasks, today, ics_path)

    if args.toast:
        title, body = build_summary(tasks, today)
        return show_windows_toast(title, body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
