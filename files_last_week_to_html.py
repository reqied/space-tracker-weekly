"""
csv -> html отчёт по файлам за последнюю неделю
Ожидаемые колонки CSV: FullName, Length, CreationTime, LastWriteTime
(разделитель определяется автоматически: запятая/точка с запятой)
"""

import argparse
import csv
import os
import sys
from collections import defaultdict
from datetime import datetime

TOTAL_MARKERS = {"__TOTAL_BYTES__", "__TOTAL__"}

def human_size(n: int) -> str:
    """Печатает размер в B/KB/MB/GB/... с понятным округлением."""
    if n is None:
        return "0 B"
    neg = n < 0
    v = float(abs(n))
    units = ("B", "KB", "MB", "GB", "TB", "PB")

    for u in units:
        if v < 1024.0 or u == units[-1]:
            if u == "B":
                txt = f"{int(v)}"
            elif v >= 100:
                txt = f"{v:.0f}"
            elif v >= 10:
                txt = f"{v:.1f}"
            else:
                txt = f"{v:.2f}"
            return ("-" if neg else "") + f"{txt} {u}"
        v /= 1024.0

def detect_delimiter(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        sample = f.read(4096)
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=[",", ";", "\t"])
        return dialect.delimiter
    except Exception:
        return ","

def read_rows(path: str):
    if not os.path.exists(path):
        print(f"Файл не найден: {path}", file=sys.stderr)
        sys.exit(2)

    delim = detect_delimiter(path)
    rows = []
    with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        # нормализуем имена колонок
        fieldmap = {k.lower(): k for k in reader.fieldnames or []}
        def col(name):  # найти реальное имя колонки, нечувствительно к регистру
            return fieldmap.get(name.lower(), name)

        fn_col = col("FullName")
        ln_col = col("Length")
        ct_col = col("CreationTime")
        lt_col = col("LastWriteTime")

        for r in reader:
            full = r.get(fn_col, "") or ""
            if full in TOTAL_MARKERS:
                continue
            try:
                length = int(float((r.get(ln_col) or "0").strip()))
            except Exception:
                length = 0
            ct = r.get(ct_col) if ct_col in r else ""
            lt = r.get(lt_col) if lt_col in r else ""
            rows.append({
                "FullName": full,
                "Length": length,
                "CreationTime": ct or "",
                "LastWriteTime": lt or "",
            })
    rows.sort(key=lambda x: x["Length"], reverse=True)
    return rows

def aggregate_by_folder(rows, top_n=30):
    acc = defaultdict(lambda: {"TotalBytes": 0, "Files": 0})
    for r in rows:
        folder = os.path.dirname(r["FullName"]) or "."
        acc[folder]["TotalBytes"] += r["Length"]
        acc[folder]["Files"] += 1
    items = [
        {"Folder": k, "TotalBytes": v["TotalBytes"], "Files": v["Files"]}
        for k, v in acc.items()
    ]
    items.sort(key=lambda x: x["TotalBytes"], reverse=True)
    return items[:top_n]

def aggregate_by_ext(rows, top_n=20):
    acc = defaultdict(lambda: {"TotalBytes": 0, "Files": 0})
    for r in rows:
        _, ext = os.path.splitext(r["FullName"])
        ext = (ext.lower() if ext else "(no ext)")
        acc[ext]["TotalBytes"] += r["Length"]
        acc[ext]["Files"] += 1
    items = [
        {"Extension": k, "TotalBytes": v["TotalBytes"], "Files": v["Files"]}
        for k, v in acc.items()
    ]
    items.sort(key=lambda x: x["TotalBytes"], reverse=True)
    return items[:top_n]

def html_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))

def render_table(headers, rows, table_id):
    # headers: [(key, title, is_bytes)]
    thead = "".join(f"<th>{html_escape(title)}</th>" for _, title, _ in headers)
    body = []
    for r in rows:
        tds = []
        for key, _, is_bytes in headers:
            val = r.get(key, "")
            if is_bytes:
                tds.append(f"<td data-bytes='{int(val)}'>{html_escape(human_size(int(val)))} <span class='small'>({int(val)})</span></td>")
            else:
                tds.append(f"<td>{html_escape(str(val))}</td>")
        body.append(f"<tr>{''.join(tds)}</tr>")
    tbody = "".join(body)
    return f"<table id='{table_id}'><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>"

def build_html(rows, by_folder, by_ext, title="Files last week report"):
    total_bytes = sum(r["Length"] for r in rows)
    file_count = len(rows)
    largest = rows[0] if rows else {"FullName": "-", "Length": 0}

    files_headers = [
        ("Length", "Size", True),
        ("FullName", "FullName", False),
        ("CreationTime", "CreationTime", False),
        ("LastWriteTime", "LastWriteTime", False),
    ]
    files_table = render_table(files_headers, rows, "files")

    folders_headers = [
        ("TotalBytes", "Size", True),
        ("Files", "Files", False),
        ("Folder", "Folder", False),
    ]
    folders_table = render_table(folders_headers, by_folder, "folders")

    ext_headers = [
        ("TotalBytes", "Size", True),
        ("Files", "Files", False),
        ("Extension", "Extension", False),
    ]
    ext_table = render_table(ext_headers, by_ext, "exts")

    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    head = f"""
<meta charset="utf-8">
<style>
body{{font-family:Segoe UI,system-ui,-apple-system,Arial;padding:22px;background:#fff;color:#222}}
h1,h2{{margin:10px 0 12px}}
.small{{opacity:.7;font-size:12px}}
table{{border-collapse:collapse;width:100%;margin:10px 0 24px}}
th,td{{border:1px solid #e6e6e6;padding:8px 10px;font-size:12.5px;vertical-align:top}}
th{{background:#f7f7f7;position:sticky;top:0;cursor:pointer}}
tr:nth-child(even){{background:#fbfbfb}}
.code{{font-family:ui-monospace,Consolas,Menlo,monospace;word-break:break-all}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin:8px 0 16px}}
.card{{background:#f7f7ff;border:1px solid #e5e5ff;border-radius:10px;padding:12px 14px;min-width:230px}}
.card .k{{opacity:.75;font-size:12px;margin-bottom:6px}}
.card .v{{font-weight:600}}
.searchbox{{margin:8px 0 12px}}
.searchbox input{{width:100%;max-width:560px;padding:8px 10px;border:1px solid #ddd;border-radius:8px;font-size:13px}}
footer{{margin-top:24px;opacity:.7;font-size:12px}}
</style>
<script>
// универсальная сортировка: если в ячейке есть data-bytes — сортируем по нему, иначе по тексту
function makeSortable(table){{
  const ths = table.querySelectorAll('th');
  ths.forEach((th,i)=>{{
    let asc=true;
    th.addEventListener('click',()=>{{
      const tbody=table.tBodies[0];
      const rows=[...tbody.rows];
      const key = (tr)=>{{
        const cell = tr.cells[i];
        const bytes = cell.getAttribute('data-bytes');
        if(bytes!==null) return parseFloat(bytes);
        const txt = cell.innerText.trim();
        const num = parseFloat(txt.replace(/[^0-9.-]/g,''));
        return isNaN(num)?txt.toLowerCase():num;
      }};
      rows.sort((a,b)=>{{ const va=key(a), vb=key(b); return (va>vb?1:va<vb?-1:0) * (asc?1:-1); }});
      asc=!asc; rows.forEach(r=>tbody.appendChild(r));
    }});
  }});
}}
function wireSearch(){{
  const box=document.getElementById('q');
  const table=document.getElementById('files');
  const head=Array.from(table.tHead.rows[0].cells).map(th=>th.innerText.toLowerCase());
  const pathIndex=head.indexOf('fullname');
  box.addEventListener('input',()=>{{
    const q=box.value.toLowerCase();
    Array.from(table.tBodies[0].rows).forEach(tr=>{{
      const txt=tr.cells[pathIndex].innerText.toLowerCase();
      tr.style.display = txt.includes(q)?'':'none';
    }});
  }});
}}
document.addEventListener('DOMContentLoaded',()=>{{
  document.querySelectorAll('table').forEach(makeSortable);
  wireSearch();
}});
</script>
"""
    summary = f"""
<div class='cards'>
  <div class='card'><div class='k'>Всего файлов</div><div class='v'>{file_count}</div></div>
  <div class='card'><div class='k'>Итоговый объём</div><div class='v'>{human_size(total_bytes)} <span class='small'>({total_bytes} bytes)</span></div></div>
  <div class='card'><div class='k'>Крупнейший файл</div><div class='v'>{human_size(largest['Length'])}</div><div class='small code'>{html_escape(largest['FullName'])}</div></div>
</div>
"""
    searchbox = """
<div class='searchbox'>
  <label>Поиск по пути (фильтр):</label><br/>
  <input id="q" type="text" placeholder="Начните вводить часть пути или имени файла..." />
</div>
"""
    html = f"""<!doctype html>
<html><head><title>{html_escape(title)}</title>{head}</head>
<body>
  <h1>{html_escape(title)}</h1>
  {summary}
  {searchbox}
  <h2>По файлам</h2>
  {files_table}
  <h2>Топ папок по объёму (Top 30)</h2>
  {folders_table}
  <h2>Топ расширений по объёму (Top 20)</h2>
  {ext_table}
  <footer>Сгенерировано: {generated}</footer>
</body></html>
"""
    return html

def main():
    p = argparse.ArgumentParser(description="Преобразовать files_last_week.csv в HTML-отчёт.")
    p.add_argument("csv", nargs="?", default="files_last_week.csv", help="Путь к CSV (по умолчанию ./files_last_week.csv)")
    p.add_argument("-o", "--out", default="files_last_week_report.html", help="Путь к HTML (по умолчанию ./files_last_week_report.html)")
    p.add_argument("--top-folders", type=int, default=30, help="Сколько папок показывать в топе (по умолчанию 30)")
    p.add_argument("--top-ext", type=int, default=20, help="Сколько расширений показывать в топе (по умолчанию 20)")
    args = p.parse_args()

    rows = read_rows(args.csv)
    by_folder = aggregate_by_folder(rows, top_n=args.top_folders)
    by_ext = aggregate_by_ext(rows, top_n=args.top_ext)
    title = f"Files last week report — {os.path.abspath(args.csv)}"

    html = build_html(rows, by_folder, by_ext, title=title)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)

    print(args.out)

if __name__ == "__main__":
    main()
