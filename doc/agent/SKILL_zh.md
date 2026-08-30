---
name: filelib-agent
description: '使用 filelib 执行路径扫描、路径判等、文件移动/复制/删除、资源下载与图片损坏检测。适用于批处理文件任务、清理脚本、数据集整理、下载落盘和图片完整性检查。'
argument-hint: '描述你的文件处理目标，例如：递归扫描并移动重复文件，或检测目录内损坏图片'
user-invocable: true
---

# Filelib Agent Skill

## 适用场景
- 需要扫描目录并按规则筛选文件。
- 需要移动、复制、删除文件或目录，并控制覆盖策略。
- 需要判断两个路径是否指向同一真实位置。
- 需要比较文件或文件夹是否完全相同。
- 需要下载文件到本地。
- 需要检测常见图片文件是否损坏。

## 模块能力地图
- `filelib.scanner`
  - `ls(...)`: 目录扫描与过滤，支持递归与多种返回路径格式。
  - `is_empty_dir(...)`: 当前是占位实现（`...`），不要在自动流程里使用。
- `filelib.resolver`
  - `is_same_path(path1, path2)`: 通过 `Path.resolve()` 比较是否同一路径。
- `filelib.checker`
  - `is_same_file(file1, file2, mode='hash')`: 通过哈希或逐字节比较两个文件。
  - `is_same_folder(folder1, folder2, match_func=None, file_compare_mode='hash')`: 递归检查两个文件夹是否包含相同的文件。
- `filelib.operator`
  - `remove(...)`: 删除文件/目录，支持 `dry_run`、`run_log`、`recursive`。
  - `move(...)`: 移动文件/目录，支持 `exist_policy`、`make_dir`、`dry_run`。
  - `copy(...)`: 复制文件/目录，支持 `exist_policy`、`make_dir`、`dry_run`。
  - `merge_folders(src, dst, dry_run=False, run_log=False)`: 将 `src` 单向合并进 `dst`；永不覆盖（SHA-256 相同跳过，冲突自动改名）；返回 `{'copied', 'skipped', 'renamed'}` 统计。
- `filelib.downloader`
  - `download_response(...)`: HTTP 下载到本地文件，返回状态码。
- `filelib.identifier`
  - `get_mime_magic(...)`: 基于文件内容识别 MIME。
  - `get_mime_extension(...)`: 基于扩展名识别 MIME。
  - `is_file_corrupted(...)`: 检查图片是否损坏（jpeg/png/gif/bmp/webp）。
- `filelib.printer`
  - `Printer`: 给 operator 系列函数提供 dry-run/run-log/warning 输出行为。

## 关键行为约束
- `scanner.ls` 的 `path_type` 实际默认值是 `abs_full_path`。
- `scanner.ls` 的 `follow_symlinks` 默认值是 `True`。
- `scanner.ls` 仅在递归扫描时才会跟随目录符号链接。
- `scanner.ls` 在 `path_type='file_only'` 时可能出现重名冲突。
- `operator.remove` 的 `recursive` 支持 `True | False | 'skip'`。
- `operator.move/copy` 的 `exist_policy` 只支持 `default | overwrite | rename`。
- `operator.move/copy` 在目标父目录不存在时，需显式设置 `make_dir=True`。
- `identifier.is_file_corrupted` 的返回语义是:
  - `True`: 文件损坏
  - `False`: 文件完整
  - `None` 或自定义值: 遇到不支持 MIME 且采用 `unsupported_policy='return'`
- `downloader.download_response` 不会自动创建父目录。
- `checker.is_same_file` 支持 `mode` 参数：`hash | full`。
  - `'hash'`（默认）：用 SHA256 哈希比较，适配所有文件类型和大小。
  - `'full'`：逐字节比较，更慢但完全准确。
- `checker.is_same_folder` 递归比较两个文件夹内的所有文件。
  - 文件按相对路径配对；相对路径要完全匹配。
  - `match_func` 是可选过滤函数，只比较过滤后的文件。
  - 空目录或被完全过滤的目录视为相同。
- `operator.merge_folders` 永不覆盖目标已有文件。
  - 相对路径相同且 SHA-256 相同：跳过；内容不同或目标不是文件：以 `stem_0.ext` / `stem_1.ext` 改名复制。
  - 源中空目录不会被创建；目标多出的文件不受影响。
  - `dry_run=True` 仍会计算哈希，返回的统计是准确的。
  - 抛出 `FileNotFoundError`（路径缺失）/ `ValueError`（非目录、同一文件夹或 `dst` 在 `src` 内）。

## Agent 工作流程
1. 明确任务类型。
- 扫描类任务优先用 `scanner.ls`。
- 文件/文件夹比较用 `checker.is_same_file` 或 `checker.is_same_folder`。
- 路径比较优先用 `resolver.is_same_path`。
- 文件变更优先用 `operator.*`。
- 不覆盖式文件夹合并用 `operator.merge_folders`。
- 下载任务用 `downloader.download_response`。
- 图片健康检查用 `identifier.is_file_corrupted`。

2. 先做安全预演。
- 对变更类任务先执行 `dry_run=True`。
- 同时开启 `run_log=True` 便于审计。

3. 处理目标冲突。
- 如果目标可能存在同名文件，优先 `exist_policy='rename'`。
- 如果明确允许覆盖，再使用 `exist_policy='overwrite'`。

4. 处理目录问题。
- 目标父目录不一定存在时，设置 `make_dir=True`。
- 删除非空目录时，明确选择:
  - `recursive=True` 直接删除
  - `recursive='skip'` 跳过
  - `recursive=False` 抛错

5. 执行与复核。
- 实际执行后再次用 `scanner.ls` 或 `Path.exists()` 复核结果。

## 常用配方

### 1) 扫描目录中的图片文件
```python
from filelib.scanner import ls

files = ls(
    directory='data/images',
    match_func=lambda f: f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')),
    recursive=True,
    path_type='abs_full_path',
    follow_symlinks=True,
)
```

### 1b) 递归扫描但不跟随目录符号链接
```python
from filelib.scanner import ls

files = ls(
    directory='data/images',
    recursive=True,
    path_type='rel_path',
    follow_symlinks=False,
)
```

### 2) 识别并收集损坏图片
```python
from filelib.identifier import is_file_corrupted

corrupted = []
for p in files:
    # True 表示损坏
    if is_file_corrupted(p, mime_method='magic', unsupported_policy='return', unsupported_return=None):
        corrupted.append(p)
```

### 3) 安全移动文件（先 dry-run，再执行）
```python
from filelib.operator import move

# 预演
move('a/source.txt', 'b/target.txt', dry_run=True, run_log=True, exist_policy='rename', make_dir=True)

# 真正执行
move('a/source.txt', 'b/target.txt', dry_run=False, run_log=True, exist_policy='rename', make_dir=True)
```

### 4) 删除目录时避免误删
```python
from filelib.operator import remove

# 跳过非空目录，保守模式
remove('tmp/cache', recursive='skip', dry_run=False, run_log=True)
```

### 5) 下载并保留已有文件
```python
from filelib.downloader import download_response

status = download_response(
    url='https://example.com/archive.zip',
    filename='downloads/archive.zip',
    force=False,
    verbose=True,
    timeout=30
)
```

### 6) 合并目录且不覆盖
```python
from filelib.operator import merge_folders

stats = merge_folders('incoming', 'archive', dry_run=True)   # 预演
stats = merge_folders('incoming', 'archive', run_log=True)   # 执行
print(stats)
```

## 失败处理建议
- 出现 `FileNotFoundError`:
  - 检查源路径是否存在。
  - 对 `move/copy` 增加 `make_dir=True`。
- 出现 `ValueError: exist_policy must be ...`:
  - 使用 `default | overwrite | rename` 之一。
- 出现 `Invalid path_type`:
  - 使用 `file_only | raw_full_path | abs_full_path | rel_path`。
- 出现不支持 MIME:
  - 改为 `unsupported_policy='return'` 并设置 `unsupported_return`，或先按扩展名过滤。
- 出现 `ValueError: Source and destination must be different folders`:
  - 选用互不嵌套的 `src`/`dst` 目录。

## 注意事项
- 本 skill 基于当前仓库实现，不假设额外封装层。
- `scanner.is_empty_dir` 尚未实现，若需要请先补全该函数后再纳入自动流程。
- 如需让 VS Code 自动发现该 skill，建议同步放置到 `.github/skills/filelib-agent/SKILL.md`。
