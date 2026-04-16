"""配置模块测试。"""

import os

from simclass.config import load_config, AppConfig


class TestConfig:
    def test_default_config(self):
        cfg = load_config()
        assert isinstance(cfg, AppConfig)
        assert cfg.llm.base_url == "https://openrouter.ai/api/v1"
        assert cfg.stt_provider == "seedasr"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setenv("SIMCLASS_AGENT_MODEL", "my-model")
        cfg = load_config()
        assert cfg.llm.api_key == "test-key"
        assert cfg.llm.agent_model == "my-model"
