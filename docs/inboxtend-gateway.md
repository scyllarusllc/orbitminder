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

## Reviewed AgentSteers observation import / 经审核的 Agent 事件导入

An optional **operator-only** importer accepts a private local JSON document and writes a bounded batch of independently observed events into the additive v3 `agent_activity_events` table. It requires `ORBITMINDER_OWNER_ID` and `ORBITMINDER_DB_PATH` in the operator's private environment. The database must already have migrations applied and the matching `agent_activities` job record (including its `mock` or `real` mode). This does **not** connect to AgentSteers or certify an event's authenticity: review provenance before importing. Do not feed untrusted emails or model output directly to this command.

```json
{
  "schema_version": 1,
  "observations": [
    {
      "external_job_id": "EXISTING_VERIFIED_JOB_ID",
      "event_key": "STABLE_SOURCE_EVENT_ID",
      "state": "running",
      "mode": "real",
      "observed_at": "2026-11-21T12:00:00Z"
    }
  ]
}
```

```bash
python3 -m orbitminder.import_agent_events --file /absolute/private/path/reviewed-events.json
```

A batch contains 1–500 events, with a 512 KB file size cap. The import is atomic: unknown jobs, mismatched modes, invalid times, or conflicting replays reject the whole batch. Identical replays are idempotent. The existing Dashboard timeline reads these stored events separately from the current per-job status snapshots. No API writes, browser submission, background schedule, Agent dispatch, tests, deployment or live integration were added.

可选的**仅管理员使用**的本地 JSON 导入命令，可将人工确认来源的 AgentSteers 事件批量写入 v3 事件表。要求任务所属用户与已存 Job 完全匹配，`real` / `mock` 模式一致；重复事件不会重复存入，冲突则整批拒绝。**此命令不能证明文件来源真实**，必须由管理员先确认记录真实性。它不提供浏览器写入接口、不自动执行 Agent，也没有进行运行测试或联调。

## Optional signed event envelopes / 可选签名事件文件

Set the private server/operator environment variable `ORBITMINDER_AGENT_EVENT_SIGNING_KEY` to a dedicated random secret of **at least 32 UTF-8 bytes** to **require HMAC-SHA256 on every event import**. The importer rejects unsigned, wrongly signed, wrongly scoped, and unrecognized-field envelopes when this key is present. Do not put the key in the JSON file, Git, or a browser.

设置私有环境变量 `ORBITMINDER_AGENT_EVENT_SIGNING_KEY` 为至少 32 字节的随机密钥，即强制每次事件导入执行 HMAC-SHA256 校验。启用后无签名、签名不符、用户标识不符或含额外字段的文件都会被拒绝。密钥不得放入 JSON 文件、Git 或浏览器。

The signed JSON envelope has exactly four top-level fields: `schema_version` (integer 1), `owner_id` (same operator-configured `ORBITMINDER_OWNER_ID`), `observations` (same array as above), and `signature` (64 lowercase hex characters). Compute the HMAC using the signing key's UTF-8 bytes and **exact canonical bytes** produced by `orbitminder.agent_event_signing.canonical_observations(owner_id, observations)`: sorted JSON keys, no extra spaces, UTF-8, and non-ASCII characters unescaped. A trusted producer must create this signature outside the untrusted transport.

签名 JSON 顶层需恰好有 `schema_version`、`owner_id`、`observations` 和 `signature` 四个字段。由可信生产方使用 `canonical_observations` 的标准化 UTF-8 字节签名，输出 64 位小写十六进制 HMAC 值，接收方按固定 owner 验证。

**Security qualification:** HMAC proves only possession of the shared key, **not** that AgentSteers itself issued a particular event; configure key distribution and event provenance separately. Without this environment variable, the older unsigned *manually reviewed* format remains accepted. No live AgentSteers connector, runtime test, or deployment verification was performed.

## Event consistency hardening / 事件一致性加固

Both single-event and batch observation writes now share the same strict path: a matching owner-scoped stored AgentSteers job is required, the stored `mock`/`real` mode must match, and the event key cannot be reused with altered content. Future-dated observation timestamps are rejected. Previously stored events are not rewritten and no Agent state transitions or dispatches are inferred from imported observations.

单条与批量事件写入现在都使用同一套严格校验：必须存在相同用户下的 AgentSteers Job，`mock`/`real` 模式必须匹配；同一事件标识不能对应不同内容，未来时间戳也会被拒绝。不会修改旧事件、推断 Agent 状态迁移或触发执行。以上均为代码提交，没有运行测试或联调。

## Stored event provenance / 已存事件来源标记

Migration `0004_agent_event_provenance.sql` adds `verification_method` to each persisted event. Existing records are marked `legacy_unknown`, never automatically promoted. Operator-reviewed unsigned imports are labeled `operator_reviewed`; imports that pass configured HMAC verification are labeled `shared_key_hmac`. The same event key cannot be silently replayed with a different provenance label. The Dashboard displays these labels with a warning that shared-key HMAC **does not authenticate AgentSteers as the source**. This labels local verification performed by OrbitMinder, not an end-to-end attestation.

v4 迁移为已存事件增加来源标记：旧记录为 `legacy_unknown`，人工审核未签名文件为 `operator_reviewed`，通过配置密钥 HMAC 校验的文件为 `shared_key_hmac`。即使通过共享密钥签名，也**不能直接认定记录确由 AgentSteers 发出**。同一个事件 ID 的来源标记不一致时，会拒绝重放。以上仅代码提交，未运行测试、联调或部署。

## Full-snapshot task presence / 完整快照中的任务存在性

The additive SQLite v5 migration adds `presence_state` and `last_seen_snapshot` to the private Inboxtend cache. **Only a fully validated, completed owner-scoped paginated task fetch** updates presence in the same transaction as task upserts. Received task IDs are `present`; previously cached IDs absent from that complete snapshot become `not_returned`, not deleted. Legacy records remain `unverified` until a complete sync. A failed/partial fetch never marks tasks absent. An older snapshot is rejected rather than rolling task presence back.

The Dashboard excludes `not_returned` tasks from ordinary task counts by default, displays source-presence counts, and offers an explicit option to include missing-from-snapshot historical task rows. **Not returned is not proof of deletion:** source visibility, policy, filtering and account changes may also explain it. Existing Agent event history remains stored. This is code-only; no live integration, tests or deployment verification were run.

SQLite v5 新增 `presence_state` 与 `last_seen_snapshot`。只有完整、通过校验的同一账号分页同步，才会在同一事务里更新任务存在性。已返回的任务标为 `present`，本轮未返回的旧任务标为 `not_returned`，不会删除。旧数据保持 `unverified`，失败或未完成的同步不会误标记缺失；比已处理快照更旧的快照将被拒绝。Dashboard 默认不把 `not_returned` 计入正常任务数量，但允许手动查看历史行。**未返回不等于已删除。** 以上代码尚未运行测试、联调或部署。

## Snapshot checkpoint and current-task ordering / 快照检查点与任务排序

Migration `0006_inboxtend_snapshot_checkpoint.sql` records the last accepted complete source snapshot for each owner/account, even when the source legitimately returns zero tasks. A later replay with an identical or older snapshot timestamp is rejected rather than changing presence flags. The checkpoint and presence changes commit in the same SQLite transaction. Legacy presence timestamps are imported into the checkpoint during migration.

The cached-task reader sorts `present` rows first, then `unverified`, then `not_returned` before applying the result limit. This reduces the chance of historical rows displacing current tasks in the first 100 returned. The list remains bounded and does **not** guarantee full coverage of all source tasks. No tests, live sync, or deployment were executed.

SQLite v6 为每个用户与 Inboxtend 账号记录最后一次完整快照时间，包括上游返回零条任务的情况。相同或更旧时间的快照会被拒绝，避免覆盖已保存的任务存在性判断。检查点和任务存在性在同一事务中写入。缓存查询优先返回 `present`，其次 `unverified`，最后 `not_returned`，降低历史任务挤占前 100 条列表的可能性，但有限条列表不能代表完整任务全集。未运行测试、联调或部署。

## Clock-skew guard / 快照时间防护

A complete source snapshot with a timestamp later than the trusted OrbitMinder server clock is rejected **before** the checkpoint or cached task presence is changed. This prevents a future-dated checkpoint from blocking subsequent valid source snapshots. Check the upstream clock if an operator sees this rejection; do not silently rewrite source timestamps. A source response is not considered a successful live sync merely because the code path exists.

完整来源快照若时间晚于 OrbitMinder 服务器的当前时间，将在更新检查点和任务存在性之前被拒绝，避免未来时间锁住后续合法同步。出现此错误时应核对上游时钟，不应静默改写来源时间。该代码尚未经过测试、联调或部署验证。
