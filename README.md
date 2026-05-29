# Cursor 状态红绿灯

在 Windows 桌面显示一个可拖动的「红绿灯」，实时反映 Cursor Agent 的工作状态。

## 灯色含义

| 灯 | 状态 | 说明 |
|----|------|------|
| 黄 | 执行中 | 发消息、用工具、改文件、思考等 |
| 绿 | 完成 | 任务结束或空闲 |
| 红 | 失败 | 工具执行失败（持续约 1 秒以上才亮红，避免重试时闪一下） |

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

鼠标悬停在红绿灯上时，**滚轮**可缩放大小（60%～200%，会写入配置）。

**双击绿灯**可打开或聚焦 Cursor。若开了多个窗口，会优先聚焦**最近更新状态的那个工程**（按 Hook 里的工作区路径匹配窗口标题）；对不上则聚焦当前任意一个 Cursor 窗口。

## 项目结构

```
cursor_rc/
├── README.md              # 说明文档
├── install.bat / install.ps1
├── requirements.txt
├── cursor_light.py        # 主程序：读状态、窗口、托盘
├── cursor_light_ui.py     # 视觉绘制（改外观只改这个）
├── hooks.json             # Cursor Hook 配置
├── hooks/set-status.py    # Hook 写状态（主）
├── hooks/set-status.ps1   # 薄封装，便于手动测试
├── sync.bat               # 日常同步到 ~/.cursor（不提交也可本地用）
├── run_cursor_light.bat
└── stop_cursor_light.bat
```

## 状态文件

运行时数据（勿提交 Git）：

- `%USERPROFILE%\.cursor\status\*.json` — 各会话状态
- `%USERPROFILE%\.cursor\status\hook.log` — Hook 调试日志
- `%USERPROFILE%\.cursor\cursor_light_config.json` — 置顶/透明度/缩放

## 给他人使用

1. 分享本仓库地址
2. 对方执行 `install.bat` → 重启 Cursor → 启动红绿灯

## 常见问题

**一直是绿灯？**  
→ 确认已重启 Cursor；看 `status\hook.log` 是否有 `busy` 记录。

**任务结束还黄很久？**  
→ 需 **重启 Cursor** 加载新 `hooks.json`（`afterAgentResponse` 写绿灯，已去掉 `postToolUse` 反复写 busy）。  
→ 超过约 45 秒无新的 busy 事件会自动视为完成；`default.json` 陈旧 busy 会在 success 时同步清除。

**偶尔闪一下红灯？**  
→ 多为 `postToolUseFailure`（某次工具失败但 Agent 立刻重试）。现已加约 **0.85 秒** 防抖，瞬时失败不会亮红；若工具真的失败停住，红灯会持续亮。

**多开 Cursor 状态乱跳？**  
→ 已按会话分文件聚合；若仍异常，把 `hook.log` 最后几行发 Issue。

**看不到托盘图标？**  
→ 点击任务栏右下角 `^` 展开隐藏图标。

## 信号逻辑（简表）

| Hook 事件 | 写入 | 灯 |
|-----------|------|-----|
| beforeSubmitPrompt / preToolUse / subagentStart | busy | 黄 |
| afterAgentThought | thinking→busy | 黄 |
| afterAgentResponse / stop / sessionEnd | success | 绿 |
| postToolUseFailure | error | 红（≥0.85s 才显示） |

**不挂钩**：`postToolUse`（结束后又写 busy 会常黄）、`subagentStop`（子任务结束≠主任务结束）。

**聚合**（`read_aggregate`）：多会话取 `error > busy > success`；busy/error 过久或心跳过期则忽略；无会话时靠 30s 心跳补黄。

## 开发说明

- 状态轮询：**约 0.08 秒**（文件变更立即刷新，约 1 秒兜底刷新时间类状态）
- Hook 使用 **Python** 写状态
- 修改外观：`cursor_light_ui.py`；规则：`cursor_light.py`、`hooks.json`、`hooks/set-status.py`
