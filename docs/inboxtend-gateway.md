# OrbitMinder read-only gateway / 只读网关

**Status / 状态:** Source implementation only. No live Inboxtend connection, deployment, or manual runtime verification has been completed. / 目前只有源代码，尚未完成真实 Inboxtend 连接、部署或运行验证。

The gateway calls Inboxtend over HTTPS using an owner-scoped, read-only upstream token. Configure the token **in Inboxtend** to allow only the intended account and only task-summary reads. Do not accept owner IDs from query parameters. The separate OrbitMinder API token is for trusted server-side callers, not client-side JavaScript. Put the service behind HTTPS, restrict network access, and rotate credentials as needed.

网关通过 HTTPS 使用限定账户、只读权限的 Inboxtend Token 获取摘要。账户范围必须由 Inboxtend 服务端绑定，不能通过 URL 参数指定。OrbitMinder API Token 仅供可信服务端调用，不应放入浏览器。外层还需 HTTPS、网络访问限制及密钥轮换。

Required private environment variables / 私有环境变量：

```text
ORBITMINDER_API_TOKEN=<separate random high-entropy secret>
INBOXTEND_READONLY_BASE_URL=https://inboxtend.example
INBOXTEND_READONLY_TOKEN=<owner-scoped read-only upstream token>
```

Install and run locally (after configuring secrets) / 配置密钥后启动：

```bash
python -m pip install -e .
python -m uvicorn orbitminder.api:app --host 127.0.0.1 --port 8000
```

`uvicorn` must be installed separately, e.g. `python -m pip install "uvicorn>=0.30,<1"`. No Docker required. The endpoint is `GET /api/v1/inboxtend/tasks?limit=50`; it accepts an optional opaque `cursor` and requires `Authorization: Bearer <ORBITMINDER_API_TOKEN>`. Responses are `private, no-store`. The gateway checks that the upstream uses HTTPS and disables redirects. It returns 503 for missing configuration and 502 for upstream failures or invalid payloads, rather than presenting missing data as an empty task list.

**Limitations / 限制：** Inboxtend must actually implement `GET /integration/v1/tasks` with the v1 payload specified in `docs/inboxtend-readonly-api.md`; otherwise the gateway cannot fetch real tasks. No persistence, incremental sync checkpoint, per-user browser login, scheduler, or bidirectional write operations are implemented in this step. Do not expose this shared-token gateway publicly without further access-control hardening.
