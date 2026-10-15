# Windows 界面操作

先使用当前宿主允许的 Computer Use 工具。在明确允许独立 Win32 自动化的环境中，
以下 pywinauto 方法可处理旧式 Delphi 窗口；不能把它当成绕过宿主 GUI 限制的备用通道。

## 1. 找进程，不把进程等同于主窗口

```powershell
Get-Process -Name Client99SE -ErrorAction SilentlyContinue |
    Select-Object Id,Path,MainWindowTitle,Responding
```

空的 `MainWindowTitle` 并不能证明没有界面。原操作曾通过 PID 枚举找到有效窗口，而普通主窗口
检测没有找到。可选只读工具：

```powershell
python -X utf8 protel99se_ui.py --pid 1234
python -X utf8 protel99se_ui.py --pid 1234 --handle 5678 --details
```

这里数字只是占位，必须换成当次观察结果。它不启动程序、不关闭窗口、不点菜单、不保存设计。
不存在窗口、工具不可用或访问被拒绝时，保留诊断；不要终止未确认归属的进程。

## 2. 绑定准确窗口

独立环境中可使用下面的方式连接。`observed_pid`、`observed_handle` 都来自当前探测：

```python
from pywinauto import Application
app = Application(backend="win32").connect(process=observed_pid, timeout=10)
window = app.window(handle=observed_handle)
print(window.window_text(), window.class_name())
print(window.menu().get_properties())
window.print_control_identifiers(depth=2)
```

原环境出现过 `Protel Document Window`、`TListView`、`TSaveCopyAsDialog`、`TEdit`、
`TComboBox`、`TButton`，但不能假设另一台机器的每个对话框都一样。
优先读取实际菜单文本，不硬编码菜单序号；汉化后文本可能包含英文、中文和 `&`。
读取控件树仍可能包含项目名称和路径，诊断结果不要直接发布。

## 3. 打开工程与文档

1. 通过观察到的 File/Open 菜单打开目标副本的 `.ddb`。
2. 检查出现的文件对话框，确认标题、文件名输入框和打开按钮后再填写。
3. 工程打开后列出文档项，确认目标 `.SCH` 或 `.PCB` 存在。
4. 存在多个列表时，限定到目标 `Protel Document Window`，而不是使用全局第一个 `TListView`。

对已观察到的 Delphi 列表，原操作使用过标准 ListView 包装器：

```python
from pywinauto.controls.common_controls import ListViewWrapper
document = window.child_window(title=observed_document_title,
                               class_name="Protel Document Window")
control = document.child_window(class_name="TListView", visible_only=True)
items = ListViewWrapper(control.wrapper_object().element_info)
print(items.texts())
# 确认目标项目后，且当前宿主允许该操作时执行：
items.get_item(observed_filename).select()
items.set_focus()
items.type_keys("{ENTER}", set_foreground=False)
```

确认激活的是相应编辑器，再使用观察到的适合全部对象/板图显示命令。截图需要出现真实对象，
不能用空白主界面或文件列表证明设计打开成功。截图和控件状态均应重新观察，不能复用旧坐标。

## 4. 原生另存与回读

先确定目标新文件不存在、源文件已备份，观察 Save Copy As 对话框中的格式选项。
原操作使用 `TSaveCopyAsDialog` 的 `TEdit` 文件名字段和 `TComboBox` 格式列表。
不同编辑器的保存格式不同，必须读取实际选项；不要对覆盖确认弹窗盲按 Enter。

完成后检查新文件实际生成，再关闭目标文档并重开保存文件。重新读取保存后的连接和几何，
因为原生程序可能量化坐标、重新编号或写入额外记录。重开不能省略，解析成功也不能替代它。

## 5. 常见边界

- 等待可见、可用的明确状态，使用有限超时；不要长时间无条件循环发送按键。
- 模态框优先处理；不要向被阻塞的主窗口继续发命令。
- 对已确认窗口才能恢复或聚焦；不要批量关闭所有同名窗口。
- 若桌面锁定、会话隔离、权限不一致或用户按停止键，停止 UI 修改并报告具体阻碍。
- 管理员授权和许可激活由用户按软件要求完成，不降低安全设置以追求自动化。
