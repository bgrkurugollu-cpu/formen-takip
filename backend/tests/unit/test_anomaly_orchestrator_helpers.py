from app.services.anomaly_orchestrator import _sanitize_source_refs, infer_record_count, new_code


class TestSanitizeSourceRefs:
    def test_strips_fabricated_tool_call_ids(self):
        payload = {
            "verified_findings": [
                {"finding": "x", "evidence": "y", "source_refs": [
                    {"tool_call_id": "REAL-1", "tool_name": "compare_shifts"},
                    {"tool_call_id": "FAKE-999", "tool_name": "compare_shifts"},
                ]}
            ],
            "possible_causes": [
                {"cause": "c", "confidence": "low", "supporting_evidence": [], "contradicting_evidence": [],
                 "verification_required": "v", "source_refs": [{"tool_call_id": "FAKE-999", "tool_name": "x"}]}
            ],
        }
        result = _sanitize_source_refs(payload, {"REAL-1"})
        assert result["verified_findings"][0]["source_refs"] == [{"tool_call_id": "REAL-1", "tool_name": "compare_shifts"}]
        assert result["possible_causes"][0]["source_refs"] == []
        assert "analysis_limitations" in result and result["analysis_limitations"]

    def test_no_change_when_all_refs_valid(self):
        payload = {
            "verified_findings": [{"finding": "x", "evidence": "y", "source_refs": [{"tool_call_id": "REAL-1", "tool_name": "t"}]}],
            "possible_causes": [],
        }
        result = _sanitize_source_refs(payload, {"REAL-1"})
        assert result.get("analysis_limitations", []) == []


class TestInferRecordCount:
    def test_top_level_list(self):
        assert infer_record_count({"items": [1, 2, 3], "other": "x"}) == 3

    def test_nested_list(self):
        assert infer_record_count({"summary": {"records": [1, 2]}}) == 2

    def test_no_list_returns_none(self):
        assert infer_record_count({"a": 1, "b": "x"}) is None


class TestNewCode:
    def test_unique_and_prefixed(self):
        codes = {new_code("TOOL") for _ in range(20)}
        assert len(codes) == 20
        assert all(c.startswith("TOOL-") for c in codes)
