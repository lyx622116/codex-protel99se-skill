# Codex Protel 99 SE Skill

让 Codex 在 Windows 上按可复查的方法操作 Protel 99 SE：找到真正的编辑窗口、打开文件夹式工程、
保存原生 SCH/PCB、检查转换损失，并整理可编辑交付文件。

**这是一套操作与核验 skill，附带轻量辅助工具；不是 Protel 安装包，也不是通用的一键反向转换器。**

## 能解决什么

| 问题 | 本包的方法 |
| --- | --- |
| 有进程，但工具报告找不到窗口 | 进程内窗口枚举、Win32 后端、模态窗口与权限诊断 |
| 中文菜单和 Delphi 控件难定位 | 读取当前菜单，限定文档窗口，处理 `TListView` |
| 交付 DDB 后对方打开空白 | 区分数据库容器和文件夹索引，核查完整同目录文件 |
| 文件改后缀了却不能编辑 | 候选转换、原生另存、重开和保存后回读 |
| 转换后看着一样但连接有误 | 引脚集合分组、显式网络名称、层/孔/规则检查 |
| 中文乱码、说明错位 | 字节编码、长度限制、字体测量与原生图面复核 |
| 文本微调造成整板误改 | 非文字对象保持核验，按实际影响范围检查 |

## 安装 skill

下载本仓库，将目录命名为 `protel99se-automation`，放入本机 Codex 的用户技能目录，例如：

```text
%USERPROFILE%/.codex/skills/protel99se-automation/SKILL.md
```

保留目录中的其他文件。也可让已配置的 skill 安装器从本仓库根目录安装。
刷新技能列表或在新任务中确认识别到 `protel99se-automation`。

可直接提出：

> 使用 protel99se-automation，检查我的 99SE 工程能否打开。先保护原件，再在副本上另存和重开；
> 核对最终文件，不修改电路设计。

> 使用 protel99se-automation，制定这套 KiCad 工程到 99SE 的迁移路线。
> 先说明实际可用的转换途径及不支持对象，再做原生回读和连接/几何核验。

## 运行条件

- Windows 上已合法安装并能运行的 Protel 99 SE；真实桌面会话用于最终原生验证。
- 当前 AI 宿主可用且获准的桌面操作能力。阅读 skill 不会自动开启工具或提升权限。
- Python 3.10+ 可运行文件工具及测试，无额外依赖。
- 独立 Win32 探测器可选安装 `requirements-ui.txt`，原操作记录使用 pywinauto 0.6.9。
  宿主若限定 GUI 工具，本探测器及文档中的独立 UI 示例不应绕过该限制。

```powershell
python -m unittest -v test_toolkit.py
python -X utf8 protel99se_toolkit.py --help
# 可选；使用单独环境，不改系统级依赖
python -m venv .venv-ui
.venv-ui/Scripts/python -m pip install -r requirements-ui.txt
```

## 文件工具示例

先将真正的原生或候选 `Main.SCH`、`Main.PCB` 放在自己的工作目录。下面仅创建索引：

```powershell
python -X utf8 protel99se_toolkit.py make-ddb C:/work/native/Design.ddb --entry Main.SCH=Sch --entry Main.PCB=PCB
python -X utf8 protel99se_toolkit.py inspect C:/work/native/Design.ddb
```

符号库条目用 `Symbols.LIB=SchLib`；封装库用 `Footprints.LIB=PCBLib`。
文件名使用可移植的 ASCII 名称，拒绝路径跳转、缺失成员和覆盖已有 DDB。
检测器返回类型线索、SHA-256 和索引成员状态，**不以扩展名或文件头保证真实可用性**。

网络核验使用 [verification.md](verification.md) 中的 JSON 结构。由真实导出或已核验的解析器生成
输入，再运行 `compare-nets`。不要人为编造“预期”和“实际”两份相同输入当作工程验证。

## 操作资料

- [SKILL.md](SKILL.md)：AI 执行入口。
- [windows-ui.md](windows-ui.md)：窗口、菜单、文档列表、原生保存。
- [formats-and-roundtrip.md](formats-and-roundtrip.md)：DDB、转换方向、编码和回读。
- [verification.md](verification.md)：电气、几何、复合焊盘、文字与制造检查。
- [troubleshooting.md](troubleshooting.md)：启动、虚拟化配置、汉化、异常定位。
- [SOURCES.md](SOURCES.md)：依赖、引用及来源边界。
- [VALIDATION.md](VALIDATION.md)：历史方法与本次工具测试的区别。

## 明确不包含

真实客户的 PCB、原理图、BOM、固件、截图、私人聊天记录、安装目录、注册码和软件安装包。
项目专用 KiCad 到 Protel 写出器没有当作通用转换产品发布。复杂转换需要结合目标对象适配，
不能从“一个项目曾成功”推断所有版本、层叠和器件都支持。

## 版权与使用

原创整理和代码采用 [非商业使用许可](LICENSE)。非商业学习、教学、研究可在保留声明的条件下使用；
未经书面同意不得用于商用，联系 **lyx_ac@163.com**。
第三方项目保留各自许可；本仓库公开可读，但不是 OSI 定义的开源许可项目。
Protel、Altium、KiCad 等名称归各权利人所有，本项目不是其官方产品。
