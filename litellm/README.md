# LiteLLM key-rotation proxy for Claude Code

A local [LiteLLM](https://docs.litellm.ai/) proxy that sits between Claude Code
and your upstream gateway (`llm.onerouter.pro`) and gives you what Claude Code
itself doesn't have:

- **3 API keys (up to 4), load-balanced with automatic failover** — requests
  are spread across keys, and when one key hits its rate limit (the gateway
  allows **2 requests/min per key**), the request is automatically retried on
  the next key. 3 keys ≈ 6 req/min effective.
- **Dead-alias fix** — `claude-opus-4`, `qwen3.5-397b-a17b` and `cc/claude-haik`
  currently have no providers upstream (the `503 No available providers`
  errors). Every Claude Code tier is mapped to the one live model:
  `qwen/qwen3.8-max-preview:free`.
- **One place to manage keys** — edit `.env`, re-run `./start.sh`.

```
Claude Code ──/v1/messages──▶ LiteLLM proxy (localhost:4000)
                                  │  rotates & retries across:
                                  ├─ KEY_1 ─▶ llm.onerouter.pro (qwen/qwen3.8-max-preview:free)
                                  ├─ KEY_2 ─▶ llm.onerouter.pro (qwen/qwen3.8-max-preview:free)
                                  └─ KEY_3 ─▶ llm.onerouter.pro (qwen/qwen3.8-max-preview:free)
```

## Quick start

```bash
cd litellm
./start.sh          # installs deps (first run), generates config.yaml, starts proxy
```

Then, in the shell you launch Claude Code from:

```bash
source litellm/use-litellm.env
claude
```

To go back to the gateway directly:

```bash
unset ANTHROPIC_BASE_URL ANTHROPIC_DEFAULT_FABLE_MODEL ANTHROPIC_DEFAULT_SONNET_MODEL \
      ANTHROPIC_DEFAULT_OPUS_MODEL ANTHROPIC_DEFAULT_HAIKU_MODEL ANTHROPIC_SMALL_FAST_MODEL
export ANTHROPIC_AUTH_TOKEN=<your original gateway token>
```

## Adding / changing keys

Edit `litellm/.env`:

```bash
GATEWAY_API_KEY_1=...   # required
GATEWAY_API_KEY_2=...   # optional
GATEWAY_API_KEY_3=...   # optional
GATEWAY_API_KEY_4=...   # optional
```

Then `./start.sh` again (it regenerates `config.yaml` and restarts the proxy).
Blank keys are skipped.

## Model mapping

All tiers → one model group `claude-main` → `qwen/qwen3.8-max-preview:free`,
rotated across all keys:

| Claude Code tier | Env var (set by `use-litellm.env`) | Served as |
|---|---|---|
| main (fable) | `ANTHROPIC_DEFAULT_FABLE_MODEL` | `claude-main` |
| sonnet | `ANTHROPIC_DEFAULT_SONNET_MODEL` | `claude-main` |
| opus | `ANTHROPIC_DEFAULT_OPUS_MODEL` | `claude-main` |
| haiku | `ANTHROPIC_DEFAULT_HAIKU_MODEL` / `ANTHROPIC_SMALL_FAST_MODEL` | `claude-main` |

## Files

| File | Purpose | Committed? |
|---|---|---|
| `.env.example` | template for secrets | ✅ |
| `.env` | your keys + master key | ❌ (gitignored) |
| `gen_config.py` | generates `config.yaml` from `.env` | ✅ |
| `config.yaml` | generated LiteLLM config | ❌ (gitignored) |
| `start.sh` / `stop.sh` | manage the proxy | ✅ |
| `use-litellm.env` | env vars for your Claude Code shell | ✅ |
| `proxy.log` / `proxy.pid` | runtime artifacts | ❌ (gitignored) |

## Notes

- **GitHub Codespaces:** `localhost` is correct — the proxy runs inside the
  same VM as Claude Code, so `http://localhost:4000` resolves locally (no
  port-forwarding needed). The only failure mode is the proxy dying when the
  codespace restarts; an auto-start hook in `~/.bashrc` re-launches it on the
  next shell (or run `./start.sh` manually).
- **Why `extra_headers` in config.yaml:** the gateway only accepts
  `Authorization: Bearer` (Anthropic-style `x-api-key` → 429) and only serves
  `/v1/messages` (`/chat/completions` → 405). The generated config handles both.
- **Prompt caching:** depends on whether the gateway forwards `cache_control`.
  Expect more cache misses through an aggregator than through Anthropic directly.
- **Routing strategy:** `usage-based-routing-v2` in `config.yaml`; alternatives:
  `simple-shuffle`, `least-busy`, `latency-based-routing`.
- **Ops:** `./stop.sh` stops the proxy; logs in `proxy.log`; health at
  `http://localhost:4000/health/liveliness`.
