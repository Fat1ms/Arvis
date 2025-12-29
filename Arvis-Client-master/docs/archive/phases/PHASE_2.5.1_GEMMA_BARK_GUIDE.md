# 🚀 Phase 2.5: Gemma 2b + Bark Integration Guide

**Status**: Phase 2.5 Implementation  
**Date**: October 21, 2025  
**Version**: 1.0  
**Providers**: Gemma 2b LLM, Bark TTS  

---

## 📋 Quick Overview

Phase 2.5 adds two powerful new providers:

### 🤖 Gemma 2b LLM Provider
- **Lightweight**: 2B parameters (CPU-friendly)
- **Fast**: Optimized inference pipeline
- **Local**: Runs via Ollama
- **Feature**: Streaming responses, context management

### 🎙️ Bark TTS Provider
- **High-Quality**: Natural speech synthesis
- **Customizable**: Multiple voices, prosody control
- **Optional**: Can disable in settings
- **Fast**: Real-time streaming support

---

## 🔧 Installation Guide

### Step 1: Install Gemma 2b (via Ollama)

#### Option A: Windows with Ollama GUI (Recommended)

1. **Download Ollama**
   ```
   https://ollama.ai/download/windows
   ```

2. **Install & Start Ollama**
   - Run installer
   - Service starts automatically
   - Check: Open `http://localhost:11434/api/tags` in browser

3. **Pull Gemma 2b Model**
   ```bash
   ollama pull gemma:2b
   ```
   
   This downloads ~1.5 GB (first time takes 5-10 minutes)

4. **Verify Installation**
   ```bash
   ollama run gemma:2b "Hello"
   ```

#### Option B: Manual Installation

```bash
# 1. Download Ollama from https://ollama.ai/
# 2. Extract to Program Files
# 3. Add to PATH

# 4. Pull model
ollama pull gemma:2b

# 5. Start server (if not auto-started)
ollama serve
```

#### Option C: Docker (Advanced)

```dockerfile
FROM ollama/ollama
RUN ollama pull gemma:2b
```

```bash
docker run -d --name ollama -p 11434:11434 ollama
```

### Step 2: Install Bark TTS

#### Option A: Via Pip (Recommended)

```bash
# Activate your virtual environment
.venv\Scripts\activate

# Install Bark
pip install bark-voice==1.0.0

# Or install from requirements file
pip install -r requirements-bark.txt
```

#### Option B: GPU Support

If you have NVIDIA GPU:

```bash
# Install GPU version
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install bark-voice==1.0.0
```

#### Option C: From Source

```bash
git clone https://github.com/suno-ai/bark.git
cd bark
pip install -e .
```

### Step 3: Create Requirements File (if needed)

Create `requirements-bark.txt`:

```
bark-voice==1.0.0
torch>=2.0.0
numpy>=1.21.0
scipy>=1.7.0
```

---

## ⚙️ Configuration Guide

### Update config.json

Add these sections to `config/config.json`:

```json
{
  "llm": {
    "default_model": "gemma",
    "gemma": {
      "model": "gemma:2b",
      "temperature": 0.7,
      "top_p": 0.9,
      "context_window": 4096,
      "stream_buffer_size": 20,
      "use_gpu": false
    },
    "ollama": {
      "url": "http://127.0.0.1:11434",
      "timeout": 30
    }
  },
  "tts": {
    "default_engine": "silero",
    "bark_enabled": true,
    "bark_voice": "v2/en_speaker_6",
    "bark_use_gpu": false,
    "bark_temperature": 0.75,
    "bark_stream_buffer_ms": 500,
    "bark_use_small": false,
    "bark_cache": true
  }
}
```

### Configuration Options

#### Gemma 2b Options

| Option | Type | Default | Notes |
|--------|------|---------|-------|
| `model` | str | "gemma:2b" | Model identifier in Ollama |
| `temperature` | float | 0.7 | Randomness (0.0-1.0, higher = more creative) |
| `top_p` | float | 0.9 | Nucleus sampling |
| `context_window` | int | 4096 | Max context tokens |
| `stream_buffer_size` | int | 20 | Min characters before streaming |
| `use_gpu` | bool | false | Enable GPU if available |

#### Bark TTS Options

| Option | Type | Default | Notes |
|--------|------|---------|-------|
| `enabled` | bool | true | Enable/disable Bark |
| `voice` | str | "v2/en_speaker_6" | Voice preset |
| `use_gpu` | bool | false | GPU acceleration |
| `temperature` | float | 0.75 | Voice variation (0.0-1.0) |
| `stream_buffer_ms` | int | 500 | Chunk size in milliseconds |
| `use_small` | bool | false | Use smaller, faster model |
| `cache` | bool | true | Cache synthesized speech |

### Available Bark Voices

```python
{
    "friendly": "v2/en_speaker_9",      # Warm, conversational
    "professional": "v2/en_speaker_3",  # Formal, clear
    "calm": "v2/en_speaker_1",          # Slow, measured
    "energetic": "v2/en_speaker_5",     # Fast, enthusiastic
    "default": "v2/en_speaker_6",       # Neutral default
}
```

---

## 🚀 Usage Examples

### Gemma 2b LLM

```python
from utils.providers.llm.gemma_provider import GemmaLLMProvider
from config.config import Config

# Initialize
config = Config()
gemma = GemmaLLMProvider(config)
gemma.initialize()

# Simple response
response = gemma.generate_response("What is Python?")
print(response)

# Streaming
for chunk in gemma.stream_response("Explain machine learning"):
    print(chunk, end="", flush=True)

# With custom parameters
response = gemma.generate_response(
    "Be creative",
    temperature=0.9,  # More creative
    max_tokens=512
)
```

### Bark TTS

```python
from utils.providers.tts.bark_provider import BarkTTSProvider
from config.config import Config

# Initialize
config = Config()
bark = BarkTTSProvider(config)
bark.initialize()

# Simple synthesis
audio = bark.synthesize("Hello world")

# Different voice
audio = bark.synthesize(
    "Custom voice",
    voice_preset="v2/en_speaker_5"  # Energetic
)

# Streaming (for real-time playback)
for audio_chunk in bark.stream_synthesize("Long text..."):
    play_audio(audio_chunk)

# Get available voices
voices = bark.get_available_voices()
for name, preset in voices.items():
    print(f"{name}: {preset}")
```

### Integration with FallbackManager

```python
from utils.operation_mode_manager import OperationModeManager
from utils.providers.llm.gemma_provider import GemmaLLMProvider
from utils.providers.tts.bark_provider import BarkTTSProvider

manager = OperationModeManager(config)

# Register providers
manager.register_provider(GemmaLLMProvider(config))
manager.register_provider(BarkTTSProvider(config))

manager.initialize_mode()

# Use with automatic fallback
response = manager.llm_fallback.execute(
    lambda p: p.generate_response("Hi"),
    operation_name="llm_generation"
)

# TTS with fallback
audio = manager.tts_fallback.execute(
    lambda p: p.synthesize("Speaking text"),
    operation_name="tts_synthesis"
)
```

---

## 📊 Performance Optimization

### Gemma 2b Optimization Tips

**For Speed:**
```json
{
  "llm": {
    "gemma": {
      "temperature": 0.1,        // Faster (less creative)
      "stream_buffer_size": 50,  // Larger chunks
      "context_window": 2048     // Smaller context
    }
  }
}
```

**For Quality:**
```json
{
  "llm": {
    "gemma": {
      "temperature": 0.9,        // More creative
      "stream_buffer_size": 10,  // Smaller chunks
      "context_window": 4096     // Full context
    }
  }
}
```

**GPU Acceleration:**
```json
{
  "llm": {
    "gemma": {
      "use_gpu": true            // Enable CUDA if available
    }
  }
}
```

### Bark TTS Optimization Tips

**For Speed:**
```json
{
  "tts": {
    "bark_enabled": true,
    "bark_use_small": true,           // Faster model
    "bark_stream_buffer_ms": 1000,    // Larger chunks
    "bark_temperature": 0.5           // Less variation
  }
}
```

**For Quality:**
```json
{
  "tts": {
    "bark_enabled": true,
    "bark_use_small": false,          // Full model
    "bark_stream_buffer_ms": 250,     // Smaller chunks
    "bark_temperature": 0.75          // Natural variation
  }
}
```

**Memory Management:**
```json
{
  "tts": {
    "bark_cache": true,               // Cache results
    "bark_use_gpu": true              // GPU memory
  }
}
```

---

## 🐛 Troubleshooting

### Gemma 2b Issues

**Issue**: "Ollama server not available"
```bash
# Solution: Start Ollama
ollama serve

# Or check if it's running
curl http://127.0.0.1:11434/api/tags
```

**Issue**: "Failed to pull model gemma:2b"
```bash
# Solution: Manual pull
ollama pull gemma:2b

# Check available models
ollama list
```

**Issue**: Slow responses
```json
{
  "llm": {
    "gemma": {
      "temperature": 0.1,        // Less creative
      "stream_buffer_size": 100  // Larger chunks
    }
  }
}
```

### Bark TTS Issues

**Issue**: "Bark not installed"
```bash
pip install bark-voice==1.0.0
```

**Issue**: CUDA out of memory
```json
{
  "tts": {
    "bark_use_gpu": false,      // Disable GPU
    "bark_use_small": true      // Smaller model
  }
}
```

**Issue**: Very slow synthesis
```bash
# Check if running on CPU
# In Python:
import torch
print(torch.cuda.is_available())

# If False, install GPU support:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## 📈 Resource Requirements

### Gemma 2b

**Minimum:**
- RAM: 4 GB
- Disk: 3 GB
- CPU: Dual-core
- Time: ~5 seconds per response

**Recommended:**
- RAM: 8+ GB
- Disk: 10 GB
- CPU: Quad-core
- GPU: Optional (10x faster)
- Time: ~1-2 seconds per response

### Bark TTS

**Minimum:**
- RAM: 2 GB
- Disk: 2 GB
- CPU: Dual-core
- Time: ~3-5 seconds per synthesis

**Recommended:**
- RAM: 4+ GB
- Disk: 5 GB
- CPU: Quad-core
- GPU: Optional (3-5x faster)
- Time: ~0.5-1 second per synthesis

---

## ✅ Verification Checklist

After installation, verify everything works:

### Gemma 2b

```bash
# 1. Check Ollama
curl http://127.0.0.1:11434/api/tags

# 2. Test model
ollama run gemma:2b "Hello"

# 3. Python test
python -c "
from utils.providers.llm.gemma_provider import GemmaLLMProvider
from config.config import Config
config = Config()
provider = GemmaLLMProvider(config)
if provider.initialize():
    print('✅ Gemma 2b ready')
    print(provider.generate_response('Hi'))
else:
    print('❌ Gemma 2b failed')
"
```

### Bark TTS

```bash
# 1. Check installation
python -c "import bark; print('✅ Bark installed')"

# 2. Test synthesis
python -c "
from utils.providers.tts.bark_provider import BarkTTSProvider
from config.config import Config
config = Config()
provider = BarkTTSProvider(config)
if provider.initialize():
    print('✅ Bark ready')
    audio = provider.synthesize('Hello')
    print(f'Generated {len(audio)} audio samples')
else:
    print('❌ Bark failed')
"
```

---

## 🔗 Useful Links

### Gemma 2b
- **Model Card**: https://huggingface.co/google/gemma-2b
- **Ollama Docs**: https://github.com/ollama/ollama
- **Ollama Models**: https://ollama.ai/library

### Bark TTS
- **GitHub**: https://github.com/suno-ai/bark
- **Model Card**: https://huggingface.co/suno/bark
- **Docs**: https://github.com/suno-ai/bark/blob/main/README.md

### Arvis Documentation
- **Phase 2.5 Guide**: This file
- **Provider Framework**: `docs/HYBRID_ARCHITECTURE_DESIGN.md`
- **Usage Examples**: `docs/OPERATION_MODES_USAGE.md`

---

## 📞 Support

### Common Questions

**Q: Which should I use, Ollama or Gemma provider directly?**
A: Use Ollama provider - it's more flexible and supports multiple models.

**Q: Can I use Bark without GPU?**
A: Yes, but it will be slow (~3-5 seconds). GPU recommended for real-time use.

**Q: How do I switch between voices?**
A: Configure in `config.json` or pass `voice_preset` parameter to `synthesize()`.

**Q: Can I use these in cloud mode?**
A: These are local providers. In cloud mode, use cloud providers (OpenAI API, etc.).

**Q: How much space do I need?**
A: ~5 GB (3 GB Gemma + 2 GB Bark + cache)

---

## 🎉 Next Steps

1. ✅ Install Ollama and Gemma 2b
2. ✅ Install Bark TTS
3. ✅ Update `config.json`
4. ✅ Run verification tests
5. ➡️ **Phase 2.5.2**: PyQt6/Customtkinter research

See **PHASE_2.5.2_GUI_RESEARCH.md** for GUI framework migration.

---

**Version**: 1.0  
**Status**: 🟢 Complete  
**Last Updated**: October 21, 2025
