import unittest
from unittest.mock import patch

from inkscape_ai.recovery_manager import (
    BridgeState,
    BridgeRecoveryManager,
    RecoverySettings,
    classify_error,
    load_recovery_settings,
)


class RecoveryManagerTests(unittest.TestCase):
    def test_classify_error(self):
        self.assertEqual(classify_error("Failed to connect to bridge"), "connectivity")
        self.assertEqual(classify_error("Timeout waiting for bridge response"), "timeout")
        self.assertEqual(classify_error("Document file not found"), "document_context")
        self.assertEqual(classify_error("something else"), "unknown")

    @patch.dict(
        "os.environ",
        {
            "INKSCAPE_RECOVERY_MODE": "aggressive",
            "INKSCAPE_RECOVERY_MAX_RETRIES": "4",
            "INKSCAPE_RECOVERY_KILL_POLICY": "full_aggressive",
            "INKSCAPE_RECOVERY_KILL_COOLDOWN_MS": "2222",
            "INKSCAPE_RECOVERY_ALLOWED_PROCESS_PATTERNS": "inkscape-ai-bridge,start_mcp.py",
            "INKSCAPE_RECOVERY_BACKOFF_MS": "100,200",
        },
        clear=False,
    )
    def test_load_recovery_settings(self):
        s = load_recovery_settings("localhost", 9877)
        self.assertEqual(s.mode, "aggressive")
        self.assertEqual(s.max_retries, 4)
        self.assertEqual(s.kill_policy, "full_aggressive")
        self.assertEqual(s.kill_cooldown_ms, 2222)
        self.assertEqual(s.allowed_process_patterns, ("inkscape-ai-bridge", "start_mcp.py"))
        self.assertEqual(s.backoff_ms, (100, 200))

    @patch("inkscape_ai.recovery_manager.cleanup_known_helpers", return_value=True)
    @patch("inkscape_ai.recovery_manager.cleanup_port_owner", return_value=True)
    @patch("inkscape_ai.recovery_manager._is_port_open", return_value=True)
    @patch("inkscape_ai.recovery_manager.time.sleep", return_value=None)
    def test_aggressive_recovery_runs_cleanup_once_per_attempt(
        self,
        _sleep,
        _is_port_open,
        cleanup_port_owner,
        cleanup_known_helpers,
    ):
        reconnect_calls = []
        rebind_calls = []

        def reconnect():
            reconnect_calls.append(True)

        def rebind():
            rebind_calls.append(True)
            return True

        settings = RecoverySettings(
            host="localhost",
            port=9877,
            mode="aggressive",
            max_retries=3,
            backoff_ms=(1, 1, 1),
            kill_policy="full_aggressive",
            kill_cooldown_ms=0,
        )
        mgr = BridgeRecoveryManager(
            settings=settings,
            reconnect=reconnect,
            restart_bridge=lambda: None,
            rebind_document=rebind,
        )
        attempts = {"count": 0}

        def flaky():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise Exception("Connection to bridge lost")
            return {"ok": True}

        result = mgr.recover_and_retry("test_op", flaky)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(reconnect_calls), 2)
        self.assertEqual(len(rebind_calls), 1)
        cleanup_port_owner.assert_called()
        cleanup_known_helpers.assert_called()

    @patch("inkscape_ai.recovery_manager.cleanup_known_helpers", return_value=True)
    @patch("inkscape_ai.recovery_manager.cleanup_port_owner", return_value=True)
    @patch("inkscape_ai.recovery_manager._is_port_open", return_value=True)
    @patch("inkscape_ai.recovery_manager.time.sleep", return_value=None)
    def test_cooldown_prevents_rapid_kill_loop(
        self,
        _sleep,
        _is_port_open,
        cleanup_port_owner,
        cleanup_known_helpers,
    ):
        settings = RecoverySettings(
            host="localhost",
            port=9877,
            mode="aggressive",
            max_retries=2,
            backoff_ms=(1, 1),
            kill_policy="full_aggressive",
            kill_cooldown_ms=999999,
        )
        mgr = BridgeRecoveryManager(
            settings=settings,
            reconnect=lambda: None,
            restart_bridge=lambda: None,
            rebind_document=lambda: True,
        )
        calls = {"count": 0}

        def always_fail():
            calls["count"] += 1
            raise Exception("Timeout waiting for bridge response")

        with self.assertRaises(Exception):
            mgr.recover_and_retry("test_op", always_fail)

        self.assertEqual(cleanup_port_owner.call_count, 1)
        self.assertEqual(cleanup_known_helpers.call_count, 1)

    def test_preflight_sets_ready_when_bridge_and_document_ok(self):
        settings = RecoverySettings(host="localhost", port=9877)
        mgr = BridgeRecoveryManager(
            settings=settings,
            reconnect=lambda: None,
            restart_bridge=lambda: None,
            rebind_document=lambda: True,
            is_bridge_alive=lambda: True,
            has_document=lambda: True,
        )
        mgr.preflight(require_document=True)
        self.assertEqual(mgr.state, BridgeState.READY)

    def test_final_error_exposes_one_line_hint(self):
        settings = RecoverySettings(host="localhost", port=9877, max_retries=1)
        mgr = BridgeRecoveryManager(
            settings=settings,
            reconnect=lambda: None,
            restart_bridge=lambda: None,
            rebind_document=lambda: True,
        )
        with self.assertRaises(Exception) as ctx:
            mgr.recover_and_retry("test_op", lambda: (_ for _ in ()).throw(Exception("Connection to bridge lost")))
        self.assertIn("Click Restart Bridge", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
