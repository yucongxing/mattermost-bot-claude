# Mattermost Agent Gateway — Phase 1

一个最小可运行的常驻 Agent Gateway：

```text
Mattermost @dev-agent
        |
        | WebSocket posted event
        v
Python/FastAPI Gateway
        |
        +--> codex exec ...
        +--> claude -p ...
        +--> OpenAI-compatible local LLM
        |
        v
Mattermost thread reply
```

## Phase 1 边界

这个版本刻意保持简单：

- 通过 Mattermost Bot Account 常驻监听 `@dev-agent`。
- 默认把任务发送给 Codex；可以用 `claude:` / `llm:` 显式切换执行器。
- Codex / Claude Code 作为一次性子进程执行。
- 执行结果回复到原消息 Thread。
- 任务状态只保存在进程内存中。
- 所有 coding task 暂时共享一个 `AGENT_WORKDIR`。

下一阶段再加入 PostgreSQL、Redis 队列、git worktree、RBAC 和审批。

## 1. Mattermost 准备

由 Mattermost 管理员创建一个 Bot Account，例如：

```text
username: dev-agent
```

把 Bot 加进需要使用的 team/channel，并保存 Bot Access Token。

Gateway 用 Bot token 调用 REST API，并通过 `/api/v4/websocket` 接收实时事件。

## 2. 安装

要求 Python 3.11+，以及服务器上已经能直接运行你要使用的执行器：

```bash
codex --version
claude --version
```

创建环境：

```bash
cd mattermost-agent-gateway
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## 3. 配置

```bash
cp .env.example .env
vim .env
```

至少修改：

```dotenv
MATTERMOST_URL=https://mattermost.example.internal
MATTERMOST_BOT_TOKEN=...
MATTERMOST_BOT_USERNAME=dev-agent
AGENT_WORKDIR=/srv/repos/project-a
```

如果公司内网 Mattermost 使用自签名证书，测试阶段可临时：

```dotenv
MATTERMOST_VERIFY_TLS=false
```

生产环境更推荐把企业 CA 加入系统信任链，然后保持 `true`。

## 4. 启动

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8088
```

检查：

```bash
curl http://127.0.0.1:8088/healthz
```

## 5. Mattermost 使用

默认执行器：

```text
@dev-agent 检查当前项目最近的修改，分析潜在 C++ 内存问题
```

强制使用 Codex：

```text
@dev-agent codex: 检查 parser 模块并给出修改建议
```

强制使用 Claude Code：

```text
@dev-agent claude: review 最近一次 commit
```

调用本地 OpenAI-compatible LLM：

```text
@dev-agent llm: std::vector 扩容机制是什么？
```

Bot 会先回复：

```text
🟡 TASK-XXXXXXXX 已接收，执行器：codex。
```

完成后继续在同一 Thread 回复结果。

## 6. Codex / Claude Code 权限

Gateway 不替执行器绕过权限机制。

Codex 实际执行：

```bash
codex exec "<prompt>"
```

Claude Code 实际执行：

```bash
claude -p "<prompt>" --output-format text
```

请先在服务器上手工验证这些命令，以及你希望它们具有的文件、Shell、Git 权限。第一阶段建议从测试仓库开始。

## 7. Local LLM

Gateway 假设本地模型暴露 OpenAI-compatible endpoint：

```text
POST /v1/chat/completions
```

例如 vLLM：

```dotenv
LOCAL_LLM_BASE_URL=http://127.0.0.1:8000/v1
LOCAL_LLM_API_KEY=local
LOCAL_LLM_MODEL=/path/or/model-name
```

## 8. 运行测试

```bash
pytest -q
```

## 9. systemd 常驻

仓库提供：

```text
systemd/mattermost-agent-gateway.service
```

假设部署目录：

```text
/opt/mattermost-agent-gateway
```

创建专用用户、复制代码并安装后：

```bash
sudo cp systemd/mattermost-agent-gateway.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mattermost-agent-gateway
sudo systemctl status mattermost-agent-gateway
```

实时日志：

```bash
journalctl -u mattermost-agent-gateway -f
```

## 10. 当前版本最重要的限制

1. Gateway 重启会丢失 `/tasks` 中的状态。
2. 多任务共享 `AGENT_WORKDIR`，所以第一阶段建议 `MAX_CONCURRENT_TASKS=1`；验证流程后再加入 git worktree 隔离。
3. 没有 RBAC，任何能 @Bot 的成员都能创建任务。
4. 没有审批节点，写代码、执行 shell 的权限完全取决于 Codex / Claude Code 自身配置。
5. 没有 Redis，因此只适合单 Gateway 实例。

第一阶段上线测试时建议：

```dotenv
MAX_CONCURRENT_TASKS=1
AGENT_WORKDIR=/srv/repos/agent-sandbox
```

使用专门的测试仓库验证完整链路，再进入 Phase 2。
