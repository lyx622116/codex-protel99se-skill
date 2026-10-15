# 来源与权利说明

核对日期：2026-10-15。

本包来自维护者与 Codex 实际操作 Protel 99 SE 的方法整理。公开内容重新去项目化编写，
不发布私人对话原文、真实电路设计、客户信息、安装资源和会话标识。

## 参考工具

| 来源 | 本包借鉴内容 | 分发情况 |
| --- | --- | --- |
| [pywinauto](https://github.com/pywinauto/pywinauto) / [How To](https://pywinauto.readthedocs.io/en/latest/HowTo.html) | Win32 进程/窗口定位、控件树、菜单、ListView | 外部依赖，不捆绑源码；原环境 0.6.9，BSD-3-Clause |
| [protel2kicad](https://github.com/einergehtnochrein/protel2kicad) | 旧 SCH/PCB 的解析及交叉核对思路；注意其转换方向和限制 | 外部参考，不捆绑解析器；[MIT](https://github.com/einergehtnochrein/protel2kicad/blob/main/LICENSE) |
| [MDBTools](https://github.com/mdbtools/mdbtools) / [Windows 构建](https://github.com/lsgunth/mdbtools-win) | 数据库式 DDB 只读提取线索 | 不分发可执行文件；各组件许可按对应上游文件核对 |
| [Altium 格式兼容说明](https://www.altium.com/documentation/altium-designer/design-tools-interfacing/altium-design-software-import-export) | 旧格式另存、数据库与 Windows File System 工程区分 | 文档引用，不复制商业软件/手册 |
| [KiCad CLI](https://docs.kicad.org/10.0/en/cli/cli.html) | 源网表、ERC/DRC 与制造输出的独立核验途径 | 外部工具，不捆绑；具体版本按用户环境核验 |

原操作中的项目专用写出器参考了 MIT 的 protel2kicad 读取布局，但没有作为本公开包的通用转换器
分发。本包文件工具和只读探测器重新编写；其合成测试不含商业软件示例或真实客户数据。

## 版权边界

本包原创内容的非商业许可不改变上述第三方许可证已经授予的权利。
来源引用不代表第三方背书，也不保证其当前版本完全兼容本机安装。
使用者应合法取得 Protel；本包不包含安装程序、补丁、注册码、模板库或汉化模块。

维护者：[@lyx622116](https://github.com/lyx622116)。商业授权与权利事项：lyx_ac@163.com。
