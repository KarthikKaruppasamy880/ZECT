# Ollama Local LLM Guide for ZECT

## What is Ollama?

Ollama is a tool that runs open-source LLMs **entirely on your local machine**. No API keys, no cloud, no network — everything stays on your computer.

---

## Security

| Concern | Answer |
|---------|--------|
| **Data leaves my machine?** | **NO** — all processing happens locally. Zero network calls. |
| **Corporate firewall issues?** | **None** — no external API calls, Zscaler won't block anything |
| **Code/prompts stored externally?** | **NO** — everything stays on your disk |
| **Audit-friendly?** | **YES** — no third-party data processing agreements needed |
| **Open source?** | **YES** — Ollama is MIT licensed, models are open-weight |

**Bottom line: Ollama is the most secure option possible.** Your code and prompts never leave your machine.

---

## System Requirements

### Minimum (for 7B models like Llama 3.1 8B, Mistral 7B)
| Resource | Requirement |
|----------|-------------|
| **RAM** | 8 GB minimum, 16 GB recommended |
| **Disk Space** | ~5 GB per model (one-time download) |
| **CPU** | Any modern CPU (Intel i5/i7, AMD Ryzen) |
| **GPU** | Optional but speeds things up 5-10x |
| **OS** | Windows 10/11, macOS, Linux |

### Recommended (for better models like Llama 3.1 70B)
| Resource | Requirement |
|----------|-------------|
| **RAM** | 32 GB+ |
| **Disk Space** | ~40 GB per large model |
| **GPU** | NVIDIA RTX 3060+ with 8GB+ VRAM |

### What fits on a typical Zinnia laptop (16GB RAM)?
- Llama 3.1 8B — **YES** (best quality for the size, ~4.7 GB)
- Mistral 7B — **YES** (fast, good for code, ~4.1 GB)
- CodeLlama 7B — **YES** (specialized for code, ~3.8 GB)
- Gemma 2 9B — **YES** (Google's model, ~5.4 GB)
- Phi-3 Mini 3.8B — **YES** (Microsoft's small model, ~2.3 GB, fastest)
- Llama 3.1 70B — **NO** (needs 40GB+ RAM)

---

## Installation Steps (Windows)

### Step 1: Download Ollama
Go to **https://ollama.com/download** and download the Windows installer (~50 MB).

> This site should NOT be blocked by Zscaler — it's a developer tool site, not an AI/ML API.

### Step 2: Install
Run the installer. It installs to `C:\Users\<you>\AppData\Local\Programs\Ollama`.

### Step 3: Download a Model
Open **PowerShell** or **Command Prompt** and run:

```powershell
# Download Llama 3.1 8B (recommended — best quality, ~4.7 GB download)
ollama pull llama3.1

# OR download Mistral 7B (faster, good for code, ~4.1 GB)
ollama pull mistral

# OR download Microsoft Phi-3 (smallest, fastest, ~2.3 GB)
ollama pull phi3
```

**First download takes 5-10 minutes** depending on your internet speed. After that, it's cached locally.

### Step 4: Verify It Works
```powershell
# Start a quick chat to test
ollama run llama3.1 "What is a REST API?"
```

You should see a response generated locally — no internet needed!

### Step 5: Start Ollama Server
Ollama runs a local API server on `http://localhost:11434` automatically when installed. Verify:

```powershell
curl http://localhost:11434/api/tags
```

This returns a list of your downloaded models.

---

## How ZECT Connects to Ollama

Once I add Ollama support to ZECT, here's how it works:

### Configuration (in your `.env` file)
```env
# Enable Ollama (local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

### How It Works
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   ZECT UI   │────>│ ZECT Backend │────>│   Ollama    │
│ (Browser)   │     │ (port 8000)  │     │ (port 11434)│
│             │<────│              │<────│  LOCAL ONLY  │
└─────────────┘     └──────────────┘     └─────────────┘
       All on localhost — nothing leaves your machine
```

1. You type a question in ZECT's Ask/Plan/Build mode
2. ZECT backend sends it to Ollama at `localhost:11434`
3. Ollama processes it using your CPU/GPU
4. Response comes back — **zero network calls**

### Model Selection in ZECT UI
A new "Local (Ollama)" section will appear in the model dropdown:
- Llama 3.1 8B (Local)
- Mistral 7B (Local)
- Phi-3 Mini (Local)
- Any other model you've downloaded

---

## Performance Expectations

| Model | Speed (16GB RAM, no GPU) | Speed (with GPU) | Quality |
|-------|--------------------------|-------------------|---------|
| Phi-3 Mini 3.8B | ~15 tokens/sec | ~40 tokens/sec | Good for simple tasks |
| Mistral 7B | ~8 tokens/sec | ~30 tokens/sec | Good for code |
| Llama 3.1 8B | ~6 tokens/sec | ~25 tokens/sec | Best overall quality |
| Gemma 2 9B | ~5 tokens/sec | ~20 tokens/sec | Good for reasoning |

**For comparison:** Cloud APIs like GPT-4o return ~50-80 tokens/sec, but they send your data to external servers.

---

## Pros vs Cons

### Pros
- **100% private** — code never leaves your machine
- **100% free** — no API costs ever
- **No corporate approval needed** — it's just software on your laptop
- **No Zscaler/firewall issues** — no external network calls
- **Works offline** — use on flights, VPN-free, anywhere

### Cons
- **Slower than cloud APIs** — depends on your hardware
- **Model quality** — 7B/8B models are good but not GPT-4 level
- **RAM usage** — models consume 4-8 GB RAM while running
- **Initial download** — 4-5 GB per model (one-time)
- **No GPU = slower** — CPU-only runs at ~6-15 tokens/sec

---

## Recommended Setup for Zinnia Developers

```powershell
# 1. Install Ollama from https://ollama.com/download

# 2. Download recommended models
ollama pull llama3.1      # Best quality (4.7 GB)
ollama pull mistral       # Fast code assistant (4.1 GB)

# 3. Configure ZECT
# Add to your C:\Users\karuppk\Downloads\ZECT\backend\.env:
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3.1

# 4. Start ZECT
cd C:\Users\karuppk\Downloads\ZECT\frontend
npm run dev

# 5. Select "Llama 3.1 (Local)" from the model dropdown
```

**Total disk space needed: ~10 GB** (Ollama + 2 models)
**Total cost: $0** — forever

---

## FAQ

**Q: Can I use both Ollama and cloud APIs?**
A: Yes! ZECT's model selector lets you switch between local (Ollama) and cloud (OpenAI/OpenRouter) per-request.

**Q: Do I need admin rights to install?**
A: No, Ollama installs to your user directory. No admin needed.

**Q: Will it slow down my laptop?**
A: Only while generating a response. When idle, Ollama uses minimal resources. You can stop it anytime.

**Q: Can the whole team share one Ollama server?**
A: Yes — install on a team server and point everyone's ZECT to `http://server-ip:11434`. But for security, local is better.

**Q: Is Ollama.com blocked by Zscaler?**
A: Unlikely — it's a developer tools site, not classified as AI/ML API. But if it is, download the installer on your phone and transfer via USB.
