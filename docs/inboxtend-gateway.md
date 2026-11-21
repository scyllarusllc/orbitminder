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

## Source import milestone / 摘要导入进展

`orbitminder/inboxtend_import.py` implements a **server-side-only** paginated import helper. A trusted caller supplies the authenticated owner ID, account key, and a validated page fetcher. It checks stable snapshots, repeated cursors, duplicate task IDs and the page bound before writing cached summaries to the existing owner/account-scoped SQLite `source_records` table. Fetch errors preserve the old cache and log a failed sync. Interrupted writes are marked partial. No deletions are inferred.

`orbitminder/inboxtend_import.py` 已提供**仅服务端使用**的分页摘要导入逻辑。由可信调用方提供已认证用户、账户标识及已校验的分页读取函数；它检查快照一致性、重复游标、重复任务 ID 和页数上限。读取失败时保留旧缓存并记为失败，写入中断时记为部分完成，不根据缺失结果删除记录。

**Not yet connected / 尚未接通：** The HTTP gateway does not call the importer automatically. The current cache only stores task title, source URL and verification timestamps; status, priority, revision, due dates and Agent state are **not persisted**. A versioned migration and authenticated Dashboard read path are required before claiming a full task sync. No live Inboxtend connection or runtime verification has been performed.

## Inboxtend-side source available / Inboxtend 源代码已加入

Inboxtend now contains the versioned read-only route in source at [`integration_feed.py`](https://github.com/scyllarusllc/inboxtend/blob/main/integration_feed.py), registered by `app.py`. The bilingual setup is at [Inboxtend integration guide](https://github.com/scyllarusllc/inboxtend/blob/main/docs/orbitminder-integration.md).

Inboxtend 源代码已加入只读接口，配置说明见上方 Inboxtend 文档。OrbitMinder 的 `INBOXTEND_READONLY_TOKEN` 必须匹配 Inboxtend 的 `INBOX_TEND_INTEGRATION_TOKEN`。浏览器不可持有任一服务端令牌。

**Current gate / 当前阻塞：** source is committed but no deployed HTTPS origin, private tokens or actual live task response were available in this development session. No end-to-end run or production verification can be claimed. Follow the existing no-automated-test rule; manually check an authorized request, an unauthorized request, pagination, owner restriction, and failure handling after private configuration.

## Cached task snapshots (source implementation, 2026-11-21) / 任务快照缓存

An additive SQLite v2 migration (`migrations/0002_inboxtend_tasks.sql`) adds `inboxtend_tasks` without replacing existing tables. `ProjectStore.initialize()` applies unapplied migrations; `save_inboxtend_tasks()` saves a validated batch atomically with revision-aware upserts. `import_task_summaries()` uses this storage after complete pagination. The authenticated `GET /api/v1/inboxtend/cached-tasks?limit=100` returns cached metadata and sync state; it does not automatically trigger a live fetch.

新增 SQLite v2 迁移（`inboxtend_tasks` 表），不重建旧表。任务导入完成分页读取后，将完整摘要以原子事务保存；旧版本不会覆盖更新的版本。受保护的 `GET /api/v1/inboxtend/cached-tasks` 可读取缓存及同步状态，但不会自动触发同步。

Set these additional **server-only** values / 另需配置仅服务端环境变量：
```text
ORBITMINDER_DB_PATH=/absolute/private/path/orbitminder.sqlite3
ORBITMINDER_OWNER_ID=<trusted authenticated owner identifier>
INBOXTEND_ACCOUNT_KEY=<private source installation/account key>
```

Call `ProjectStore(absolute_path).initialize()` in a controlled initialization path before using the cache endpoint. Only deploy behind TLS with restricted server-to-server callers; one shared API bearer token does **not** provide multi-user isolation by itself. No live integration, initialization, migration execution, tests, or runtime verification has been performed for this milestone. Existing Gmail and Agent execution flows are unchanged.

## Explicit server sync command / 服务端手动同步命令

The operator can invoke the new source-only CLI after private configuration:

```bash
python3 -m orbitminder.sync_inboxtend --page-limit 50 --max-pages 100
```

Required server-side environment: `ORBITMINDER_DB_PATH` (absolute path), `ORBITMINDER_OWNER_ID` (the **same authenticated Google subject** used by the Next.js Dashboard), `INBOXTEND_ACCOUNT_KEY` (same key as the Dashboard), `INBOXTEND_READONLY_BASE_URL` (HTTPS origin only), and `INBOXTEND_READONLY_TOKEN` (matches the upstream owner-scoped token). The CLI initializes existing additive migrations, fetches version-1 pages, validates them and imports into the owner-scoped SQLite snapshot table. It reports non-sensitive counts on success and a generic error on failure.

配置上述服务端私有变量后，管理员可以执行命令手动同步。特别注意：`ORBITMINDER_OWNER_ID` 必须和 Next.js 登录会话中的 Google 用户标识一致，否则页面读不到已导入任务。同步命令不会保存邮件正文或附件，也不会执行 Agent。

**Not automatic / 非自动功能：** Dashboard reload reads cache only. There is no public sync trigger, no automatic scheduler and no production verification. The last sync state and checked count appear in the task panel. Per the owner's current direction, no tests or live integration were run for this code change.
