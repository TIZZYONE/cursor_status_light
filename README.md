# Cursor 状态红绿灯

在 Windows 桌面显示一个可拖动的「红绿灯」，实时反映 Cursor Agent 的工作状态。

## 灯色含义

| 灯 | 状态 | 说明 |
|----|------|------|
| 黄 | 执行中 | 发消息、用工具、改文件、思考等 |
| 绿 | 完成 | 任务结束或空闲 |
| 红 | 失败 | 工具执行失败 |

**多窗口**：每个 Cursor 会话单独记录状态，任意一个在忙就显示黄灯，全部结束才绿灯。

## 环境要求

- Windows 10/11
- [Python 3.8+](https://www.python.org/downloads/)（安装时勾选 *Add to PATH*）
- [Cursor](https://cursor.com/) 支持 Hooks 的版本

## 一键安装（推荐，首次使用）

1. 克隆本仓库
2. **双击 `install.bat`**（安装依赖 + 复制文件到 `%USERPROFILE%\.cursor`）
3. **完全退出并重启 Cursor**
4. 双击 **「Cursor红绿灯-启动」** 或 `run_cursor_light.bat`

## 改代码后同步到 Cursor 目录

| 场景 | 操作 |
|------|------|
| 只改了 `.py` / `.ps1` / `hooks.json` | 双击 **`sync.bat`**（快，不重装依赖） |
| 首次安装 / 换了电脑 | 双击 **`install.bat`** |
| 改了 `hooks.json` | `sync.bat` 后 **重启 Cursor** |
| 只改了界面逻辑 | `sync.bat` 后 **重启红绿灯**（`stop` → `run`） |

关闭：双击 **「Cursor红绿灯-关闭」**，或托盘右键 → 退出。

## 手动使用

| 操作 | 文件 |
|------|------|
| 安装 | `install.bat` |
| 启动 | `run_cursor_light.bat` |
| 关闭 | `stop_cursor_light.bat` |

安装后文件位于：`%USERPROFILE%\.cursor\`

## 托盘菜单

- **切换置顶**：窗口是否始终在最前
- **窗口透明度**：30%～100%
- **退出**

## 项目结构

```
cursor_rc/
├── README.md              # 说明文档
├── install.bat / install.ps1
├── requirements.txt
├── cursor_light.py        # 主程序：读状态、窗口、托盘
├── cursor_light_ui.py     # 视觉绘制（改外观只改这个）
├── hooks.json             # Cursor Hook 配置
├── hooks/set-status.ps1   # 写入状态文件
├── run_cursor_light.bat
└── stop_cursor_light.bat
```

## 状态文件

运行时数据（勿提交 Git）：

- `%USERPROFILE%\.cursor\status\*.json` — 各会话状态
- `%USERPROFILE%\.cursor\status\hook.log` — Hook 调试日志
- `%USERPROFILE%\.cursor\cursor_light_config.json` — 置顶/透明度设置

## 给他人使用

1. 分享本仓库地址
2. 对方执行 `install.bat` → 重启 Cursor → 启动红绿灯

## 常见问题

**一直是绿灯？**  
→ 确认已重启 Cursor；看 `status\hook.log` 是否有 `busy` 记录。

**黄灯闪一下变绿又变黄？**  
→ 已用心跳保持：30 秒内有过 busy/thinking 会一直保持黄灯；请 `sync.bat` 更新后重启红绿灯。

**多开 Cursor 状态乱跳？**  
→ 已按会话分文件聚合；若仍异常，把 `hook.log` 最后几行发 Issue。

**看不到托盘图标？**  
→ 点击任务栏右下角 `^` 展开隐藏图标。

## 开发说明

- 状态轮询：**0.3 秒**
- busy 时黄灯**常亮**（不闪烁）
- 修改外观：编辑 `cursor_light_ui.py`
- 修改状态规则：编辑 `cursor_light.py` 与 `hooks.json`
