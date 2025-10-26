# space-tracker-weekly

Инструмент для быстрого поиска **какие файлы «съели» место** на диске за последние *N* дней и вывода итогов в **красивом HTML‑отчёте** (с сортировкой по клику, лайв‑поиском, «топ папок» и «топ расширений»).

> Работает оффлайн, без сторонних библиотек. Все команды написаны для Windows PowerShell, но код универсальный. Для генерации отчёта нужен Python 3.8+.

---

## ✨ Возможности
- Сбор списка файлов, **созданных или изменённых** за последние *N* дней (Windows PowerShell‑скрипт).
- Экспорт в CSV/TSV с колонками: `FullName, Length, CreationTime, LastWriteTime`.
- Генерация HTML‑отчёта из готового CSV/TSV:
  - таблица по файлам (сортировка по клику, поиск по пути),
  - **Top folders** (суммарный объём + количество файлов),
  - **Top extensions** (суммарный объём + количество файлов),
  - сводные карточки (кол‑во файлов, общий объём, крупнейший файл).

---

## 🚀 Быстрый старт (Windows PowerShell)

1) **Соберите CSV со «свежими» файлами** (созданными/изменёнными за последние 7 дней).  
   > *Подсказка:* сканировать весь `C:\` может быть долго. Начните с вашего профиля: `C:\Users\<имя>`.

```powershell
$days = 7 # статистика за сколько дней вам нужна
$root = 'C:\' # или сузьте до вашего профиля: "C:\Users\<имя>"
$out  = "$env:USERPROFILE\Desktop\files_last_week.csv" # куда сохранить итоговый CSV
$from = (Get-Date).AddDays(-$days)

$rows = Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -ge $from -or $_.CreationTime -ge $from } |
  Select-Object FullName, Length, CreationTime, LastWriteTime

$rows | Sort-Object Length -Descending | Export-Csv -NoTypeInformation $out
Write-Host "Saved: $out"
```

2) **Сгенерируйте HTML‑отчёт** из CSV с помощью Python‑скрипта:

```powershell
python ПУТЬ_ДО_ФАЙЛА_С_КОДОМ\files_last_week_to_html.py `
       "C:\Users\<имя>\Desktop\files_last_week.csv" `
       -o "C:\Users\<имя>\Desktop\files_last_week_report.html"
```

Откройте получившийся `files_last_week_report.html` в браузере.

---

## ⚙️ Скрипт генерации отчёта

Файл: `files_last_week_to_html.py`  
Назначение: парсит CSV/TSV c колонками `FullName, Length, CreationTime, LastWriteTime` и генерирует HTML‑страницу.

**Пример запуска:**

```powershell
# CSV рядом со скриптом — можно без аргументов
python .\files_last_week_to_html.py

# или явные пути
python .\files_last_week_to_html.py "C:\path\to\files_last_week.csv" -o "C:\path\to\report.html"
```

**Опции:**
```
--top-folders N   # сколько папок показывать в «Top folders» (по умолчанию 30)
--top-ext N       # сколько расширений показывать в «Top extensions» (по умолчанию 20)
```

**Формат входного файла:**
- Требуемые колонки: `FullName` (абсолютный путь), `Length` (в байтах).  
  `CreationTime` и `LastWriteTime` — опционально.
- Разделитель определяется автоматически: запятая `,`, точка с запятой `;` или таб `\t`.
- Служебная строка `__TOTAL_BYTES__` (если присутствует) игнорируется.

---

## 🧭 Что есть в HTML‑отчёте
- **Сводка**: общее число файлов, общий объём, крупнейший файл (с размером и путём).
- **Таблица по файлам**: колонки `Size`, `Bytes`, `FullName`, `CreationTime`, `LastWriteTime`.
  - Сортировка по клику на заголовке.
  - Строка поиска по пути/имени (фильтрует таблицу «на лету»).
- **Top folders**: суммарный объём по папкам + количество файлов (Top N).
- **Top extensions**: суммарный объём по расширениям + количество файлов (Top N).

---

## 🧪 Советы по сбору CSV (Windows)
- **Сужайте область**: вместо `C:\` начните с `C:\Users\<имя>`, это заметно быстрее.
- **Исключайте каталоги** (пример: игры/IDE кэши, временные папки):
  ```powershell
  $exclude = @('C:\Windows', 'C:\Program Files', 'C:\Program Files (x86)', 'C:\$Recycle.Bin')
  Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $exclude -notcontains ($_.DirectoryName) -and ($_.LastWriteTime -ge $from -or $_.CreationTime -ge $from) } |
    Select-Object FullName, Length, CreationTime, LastWriteTime |
    Export-Csv -NoTypeInformation $out
  ```
- **Топ‑100 самых тяжёлых** за период:
  ```powershell
  $rows | Sort-Object Length -Descending | Select-Object -First 100 |
    Export-Csv -NoTypeInformation $out
  ```

---

## 🛠️ Устранение проблем

- **Permission denied / нет прав записи**  
  Сохраните отчёт в доступную папку, например на рабочий стол:  
  `-o "C:\Users\<имя>\Desktop\report.html"`

- **`python` не найден**  
  Используйте лаунчер: `py .\files_last_week_to_html.py ...`

- **CSV открылся в Excel и «занят»**  
  Закройте файл перед повторной генерацией или укажите другое имя отчёта.

- **Слишком много файлов / медленно**  
  Сузьте `$root`. Исключите тяжёлые каталоги (см. выше).

---
