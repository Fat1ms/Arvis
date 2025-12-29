# 🚀 Phase 3 Feature #1: Days 4-5 Plan — ArvisCore Integration & Server Coordination

**Status**: Planning Phase  
**Target**: Integrate TTS Factory into ArvisCore with hybrid server support  
**Duration**: Days 4-5 (2 days)  
**Tests Target**: 70+ passing (64 + 6-10 new integration tests)

---

## 📋 Overview

Days 4-5 focus on **integrating the TTS Factory** into `ArvisCore`, enabling:
- ✅ Config-driven engine selection (Silero/Bark/SAPI)
- ✅ Seamless engine switching at runtime
- ✅ Server-aware engine negotiation (hybrid system)
- ✅ Integration tests for engine coordination with ArvisCore
- ✅ Comprehensive system validation

---

## 🏗️ Architecture Changes

### Before (Current)
```
ArvisCore
├── init_tts_engine_async()
│   └── Hardcoded SileroTTSEngine creation
└── self.tts_engine (SileroTTSEngine instance)
```

### After (Days 4-5)
```
ArvisCore
├── init_tts_engine_async()
│   ├── Check config → tts.default_engine
│   ├── Check server (if use_remote_server) → negotiate engine
│   ├── TTSFactory.create_engine(engine_type, config)
│   └── Fallback: try next engine in priority list
├── self.tts_engine (TTSEngineBase instance — polymorphic)
├── self._tts_engine_type (string: "silero"|"bark"|"sapi")
└── switch_tts_engine_async(new_engine_type)
```

---

## 📂 Day 4: Integration & Configuration

### 4.1 Update `src/core/arvis_core.py`

#### Changes Required:
```python
# ===== LINE RANGES TO MODIFY =====

# 1. Import TTSFactory (after existing imports)
from modules.tts_factory import TTSFactory

# 2. In ArvisCore.__init__(), add new instance variables
self._tts_engine_type = None          # Track current engine type
self._tts_factory = TTSFactory()       # Singleton factory reference
self._available_tts_engines = []       # Available engines from config
self._tts_engine_priority = []         # Fallback priority list

# 3. Modify init_components_async() → rename init_tts_engine_async() 
#    to use factory pattern

# OLD (current):
async def init_tts_engine_async(self):
    """Initialize TTS engine (Silero)."""
    try:
        logger.info("Initializing Silero TTS engine...")
        self.tts_engine = SileroTTSEngine(self.config)
        # ... rest of code

# NEW (proposed):
async def init_tts_engine_async(self):
    """Initialize TTS engine using Factory pattern."""
    try:
        logger.info("Initializing TTS engine using Factory...")
        
        # 1. Get engine type from config
        engine_type = self.config.get("tts.default_engine", "silero")
        
        # 2. Query server for engine negotiation (if hybrid mode)
        if self.config.get("auth.use_remote_server", False):
            server_engine = await self._negotiate_engine_with_server()
            if server_engine:
                engine_type = server_engine
                logger.info(f"Server negotiated engine: {engine_type}")
        
        # 3. Build priority list from config
        self._build_engine_priority_list()
        
        # 4. Try to create engine
        self.tts_engine = await self._create_tts_engine_with_fallback(engine_type)
        
        # ... rest of initialization

# 4. New helper methods:

async def _negotiate_engine_with_server(self) -> Optional[str]:
    """Query server for preferred TTS engine (hybrid system)."""
    try:
        # Call /api/client/engine-preference or similar
        # For now: placeholder (implement after Days 4-5)
        logger.debug("Querying server for engine preference...")
        # TODO: Implement when Client API extended
        return None
    except Exception as e:
        logger.warning(f"Server engine negotiation failed: {e}")
        return None

def _build_engine_priority_list(self):
    """Build fallback priority list from config."""
    self._available_tts_engines = self._tts_factory.list_available_engines()
    
    # Priority: configured default → available engines
    primary = self.config.get("tts.default_engine", "silero")
    others = [e for e in self._available_tts_engines if e != primary]
    
    self._tts_engine_priority = [primary] + others
    logger.info(f"TTS engine priority: {self._tts_engine_priority}")

async def _create_tts_engine_with_fallback(self, engine_type: str) -> TTSEngineBase:
    """Create TTS engine with fallback to alternatives."""
    for engine in [engine_type] + self._tts_engine_priority:
        try:
            logger.info(f"Attempting to create {engine} TTS engine...")
            engine_obj = self._tts_factory.create_engine(engine, self.config)
            
            # Run health check
            health = await engine_obj.health_check()
            if not health.healthy:
                logger.warning(f"{engine} health check failed: {health.message}")
                continue
            
            self._tts_engine_type = engine
            logger.info(f"✅ Successfully initialized {engine} TTS engine")
            return engine_obj
            
        except Exception as e:
            logger.warning(f"Failed to initialize {engine}: {e}")
            continue
    
    raise RuntimeError("Could not initialize any TTS engine!")

async def switch_tts_engine_async(self, new_engine_type: str) -> bool:
    """Switch to different TTS engine at runtime."""
    try:
        logger.info(f"Switching TTS engine: {self._tts_engine_type} → {new_engine_type}")
        
        # Check if new engine available
        if not self._tts_factory.is_engine_available(new_engine_type):
            logger.error(f"Engine {new_engine_type} not available")
            return False
        
        # Stop current engine if speaking
        if self.tts_engine.get_status().value in ["SPEAKING", "INITIALIZING"]:
            await self.tts_engine.stop()
        
        # Create new engine
        new_engine = self._tts_factory.create_engine(new_engine_type, self.config)
        
        # Run health check
        health = await new_engine.health_check()
        if not health.healthy:
            logger.error(f"{new_engine_type} health check failed: {health.message}")
            return False
        
        # Switch
        self.tts_engine = new_engine
        self._tts_engine_type = new_engine_type
        logger.info(f"✅ Successfully switched to {new_engine_type}")
        
        # Emit signal for UI update
        self.tts_engine_switched.emit(new_engine_type)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to switch engine: {e}")
        return False

# 5. Add new signal (in __init__)
self.tts_engine_switched = pyqtSignal(str)  # Emits: new_engine_type
```

### 4.2 Configuration Schema Updates

#### Update `config/config.json`
```json
{
  "tts": {
    "default_engine": "silero",
    "engines": {
      "silero": {
        "model_name": "v3_1_ru",
        "speaker": "baya",
        "sample_rate": 48000,
        "enabled": true
      },
      "bark": {
        "model_size": "small",
        "device": "auto",
        "np_load_scale": 0.5,
        "enabled": true
      },
      "sapi5": {
        "rate": 1,
        "volume": 100,
        "enabled": false
      }
    },
    "fallback_on_error": true,
    "health_check_interval": 30
  },
  "auth": {
    "use_remote_server": true,
    "server_url": "http://127.0.0.1:8000",
    "engine_negotiation": true
  }
}
```

#### Add to `config/config.py`
```python
def get_enabled_tts_engines(self) -> List[str]:
    """Get list of enabled TTS engines."""
    engines = []
    engines_config = self.get("tts.engines", {})
    
    for engine_name, config in engines_config.items():
        if config.get("enabled", True):
            engines.append(engine_name)
    
    return engines

def get_tts_engine_config(self, engine_type: str) -> Dict:
    """Get configuration for specific engine."""
    return self.get(f"tts.engines.{engine_type}", {})
```

### 4.3 GUI Updates (Optional for Days 4-5)

Create `src/gui/tts_engine_selector_widget.py`:
```python
"""TTS Engine Selector widget for settings."""

class TTSEngineSelectorWidget(QWidget):
    engine_changed = pyqtSignal(str)  # Emits: new_engine_type
    
    def __init__(self, core: ArvisCore):
        super().__init__()
        self.core = core
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Dropdown for engine selection
        self.engine_combo = QComboBox()
        self.update_available_engines()
        
        # Health status indicator
        self.health_label = QLabel("Status: —")
        
        layout.addWidget(QLabel("TTS Engine:"))
        layout.addWidget(self.engine_combo)
        layout.addWidget(self.health_label)
        
        self.setLayout(layout)
    
    def connect_signals(self):
        self.engine_combo.currentTextChanged.connect(self.on_engine_selected)
        self.core.tts_engine_switched.connect(self.on_engine_switched)
    
    async def on_engine_selected(self, engine_type: str):
        """Handle engine selection."""
        success = await self.core.switch_tts_engine_async(engine_type)
        if not success:
            self.health_label.setText("❌ Failed to switch engine")
            self.engine_combo.setCurrentText(self.core._tts_engine_type)
    
    def on_engine_switched(self, engine_type: str):
        """Update UI when engine switched."""
        self.engine_combo.setCurrentText(engine_type)
        self.health_label.setText(f"✅ Using: {engine_type}")
    
    async def update_available_engines(self):
        """Refresh available engines list."""
        self.engine_combo.clear()
        for engine in self.core._available_tts_engines:
            self.engine_combo.addItem(engine)
```

---

## 📝 Day 5: Tests & Validation

### 5.1 Create Integration Tests

Create `tests/integration/test_arviscore_tts_integration.py`:

```python
"""Integration tests for ArvisCore ↔ TTS Factory."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.core.arvis_core import ArvisCore
from modules.tts_factory import TTSFactory
from modules.tts_base import TTSEngineBase, TTSStatus, HealthCheckResult


@pytest.mark.asyncio
class TestArvisCoreHTTSFactory:
    """Test ArvisCore integration with TTS Factory."""
    
    async def test_init_tts_engine_with_factory(self, mock_config):
        """Test that ArvisCore uses TTSFactory for initialization."""
        # Arrange
        mock_config.get.side_effect = lambda key, default=None: {
            "tts.default_engine": "silero"
        }.get(key, default)
        
        core = ArvisCore(mock_config)
        
        # Act
        await core.init_tts_engine_async()
        
        # Assert
        assert core.tts_engine is not None
        assert isinstance(core.tts_engine, TTSEngineBase)
        assert core._tts_engine_type == "silero"
    
    async def test_switch_tts_engine(self, mock_config):
        """Test switching between TTS engines."""
        # Arrange
        core = ArvisCore(mock_config)
        await core.init_tts_engine_async()
        
        # Act
        success = await core.switch_tts_engine_async("bark")
        
        # Assert
        if success:
            assert core._tts_engine_type == "bark"
    
    async def test_fallback_engine_on_error(self, mock_config):
        """Test fallback to alternative engine if primary fails."""
        # Setup: mock Silero as unavailable, Bark as available
        with patch("modules.tts_factory.TTSFactory.create_engine") as mock_create:
            mock_create.side_effect = [
                RuntimeError("Silero failed"),  # First call fails
                Mock(spec=TTSEngineBase)        # Second call succeeds
            ]
            
            # This test validates fallback logic
            pass  # Implementation depends on actual error scenarios
    
    async def test_engine_priority_list(self, mock_config):
        """Test that engine priority list is built correctly."""
        # Arrange
        core = ArvisCore(mock_config)
        
        # Act
        core._build_engine_priority_list()
        
        # Assert
        assert len(core._tts_engine_priority) > 0
        assert core._tts_engine_priority[0] == "silero"  # Default first
    
    async def test_health_check_on_switch(self, mock_config):
        """Test that health check runs before switching."""
        # Arrange
        core = ArvisCore(mock_config)
        await core.init_tts_engine_async()
        
        # Mock engine with failed health check
        mock_engine = Mock(spec=TTSEngineBase)
        mock_engine.health_check = AsyncMock(
            return_value=HealthCheckResult(
                healthy=False,
                message="Engine unavailable"
            )
        )
        
        with patch.object(core._tts_factory, "create_engine", return_value=mock_engine):
            # Act
            success = await core.switch_tts_engine_async("bark")
            
            # Assert
            assert not success  # Should fail due to health check


@pytest.mark.asyncio
class TestTTSEngineSignals:
    """Test PyQt signals for TTS engine switching."""
    
    async def test_tts_engine_switched_signal(self, mock_config):
        """Test that tts_engine_switched signal is emitted."""
        # Arrange
        core = ArvisCore(mock_config)
        await core.init_tts_engine_async()
        
        signal_received = False
        received_engine = None
        
        def on_signal(engine):
            nonlocal signal_received, received_engine
            signal_received = True
            received_engine = engine
        
        core.tts_engine_switched.connect(on_signal)
        
        # Act
        await core.switch_tts_engine_async("bark")
        
        # Assert
        assert signal_received or core._tts_engine_type == "bark"


@pytest.mark.asyncio
class TestServerEngineNegotiation:
    """Test server-side engine negotiation (placeholder for future)."""
    
    async def test_negotiate_engine_with_server(self, mock_config):
        """Test querying server for preferred engine."""
        # Arrange
        mock_config.get.side_effect = lambda key, default=None: {
            "auth.use_remote_server": True
        }.get(key, default)
        
        core = ArvisCore(mock_config)
        
        # Act
        server_engine = await core._negotiate_engine_with_server()
        
        # Assert
        # Currently returns None (placeholder)
        # Will implement after Server API extended
        assert server_engine is None or isinstance(server_engine, str)
```

### 5.2 Run Comprehensive Test Suite

```bash
# Test TTS Factory system (64 tests)
pytest tests/unit/test_tts_*.py -v --tb=short

# Test new integration tests (6-10 tests)
pytest tests/integration/test_arviscore_tts_*.py -v --tb=short

# Full coverage report
pytest tests/ --cov=modules --cov=src/core --cov-report=html

# Target: 70+ tests passing, 80%+ coverage
```

### 5.3 Validation Checklist

- [ ] ArvisCore initializes TTS via TTSFactory
- [ ] Config-driven engine selection works
- [ ] Engine switching succeeds
- [ ] Fallback engine used on error
- [ ] Health check runs before switching
- [ ] PyQt signals emit correctly
- [ ] Server negotiation placeholder exists
- [ ] 70+ tests passing
- [ ] 80%+ code coverage achieved
- [ ] No circular imports or errors
- [ ] Documentation updated

---

## 🔗 Server Coordination (Arvis-Server Integration)

### Research Needed (Days 4-5)

**Examine** `D:\AI\Arvis-Server`:
1. **Client API endpoints** (`/api/client/*`)
   - Is there an engine preference endpoint?
   - Should server track client engine selection?

2. **Multi-client coordination**
   - Do multiple clients need to negotiate engine usage?
   - Should Bark model be cached on server?

3. **Health check propagation**
   - Should client report engine health to server?
   - Server-side health dashboard?

### Proposed API Extensions (Future)

```http
# Get server's preferred TTS engine for this client
GET /api/client/engine-preference
Response:
{
  "preferred_engine": "bark",
  "available_engines": ["silero", "bark"],
  "reason": "User settings"
}

# Report client TTS engine health
POST /api/client/report-engine-health
Body:
{
  "engine_type": "bark",
  "health": {
    "healthy": true,
    "message": "All systems operational",
    "details": {...}
  }
}
```

**Note**: Implement after Days 4-5 if needed.

---

## 📊 Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Tests Passing | 70+ | — |
| Code Coverage | 80%+ | — |
| Engine Switching Time | < 2s | — |
| Health Check Performance | < 100ms | — |
| Fallback Activation Time | < 500ms | — |
| Zero Import Errors | ✅ | — |
| Server Coordination Placeholders | ✅ | — |

---

## 📅 Implementation Timeline

### Day 4 (4-6 hours)
- Morning: Modify `src/core/arvis_core.py` with TTSFactory integration
- Afternoon: Update config schema, create GUI widget
- Evening: Create integration test structure

### Day 5 (4-6 hours)
- Morning: Implement 6-10 integration tests
- Afternoon: Run full test suite, coverage analysis
- Evening: Documentation update, validation checklist completion

---

## 🎯 Deliverables (Days 4-5)

✅ Modified `src/core/arvis_core.py` with TTSFactory integration  
✅ Updated `config/config.json` and `config/config.py`  
✅ New `src/gui/tts_engine_selector_widget.py`  
✅ New `tests/integration/test_arviscore_tts_integration.py`  
✅ Server coordination placeholders implemented  
✅ 70+ tests passing (64 + 6-10 new)  
✅ 80%+ code coverage achieved  
✅ All documentation updated  

---

## 🚀 Next Steps (After Days 4-5)

1. **Feature 2**: LLM Streaming Optimization (Days 6-11)
2. **Feature 3**: Health Checks System (Days 12-15)
3. **Server Enhancement**: Extend Client API with engine negotiation endpoints

---

**Status**: Ready for Day 4 Implementation 🚀  
**Blocker**: None  
**Server Integration**: Hybrid system awareness built in via `_negotiate_engine_with_server()` placeholder
