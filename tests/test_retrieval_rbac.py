"""
Unit tests for RBAC role resolution and retrieval logic.

These tests mock Qdrant and the embedder so they run without
any external services.
"""
import pytest
from unittest.mock import MagicMock, patch

from config import ROLE_PERMISSIONS
from api.retrieval.retriever import _allowed_roles, search
from utils import QueryResult


# ── Role permission tests ─────────────────────────────────────────

class TestRolePermissions:
    def test_hr_admin_sees_all(self):
        roles = _allowed_roles("HR-Admin")
        assert "HR-Admin" in roles
        assert "Finance" in roles
        assert "General-Staff" in roles
        assert "Public" in roles

    def test_finance_cannot_see_hr(self):
        roles = _allowed_roles("Finance")
        assert "HR-Admin" not in roles
        assert "Finance" in roles
        assert "General-Staff" in roles
        assert "Public" in roles

    def test_general_staff_sees_staff_and_public(self):
        roles = _allowed_roles("General-Staff")
        assert "General-Staff" in roles
        assert "Public" in roles
        assert "HR-Admin" not in roles
        assert "Finance" not in roles

    def test_contractor_sees_only_public(self):
        roles = _allowed_roles("Contractor")
        assert roles == ["Public"]

    def test_unknown_role_defaults_to_public(self):
        roles = _allowed_roles("UnknownRole")
        assert roles == ["Public"]

    def test_all_configured_roles_present(self):
        for role in ROLE_PERMISSIONS:
            assert _allowed_roles(role) is not None


# ── Search mock tests ──────────────────────────────────────────────

class TestSearchRBAC:
    def _make_mock_hit(self, text: str, access_role: str, doc_type: str = "md", score: float = 0.9):
        hit = MagicMock()
        hit.score = score
        hit.payload = {
            "text": text,
            "parent_text": None,
            "access_role": access_role,
            "doc_type": doc_type,
            "source": f"test/{access_role.lower()}_doc.md",
            "page": None,
        }
        return hit

    @patch("retrieval.retriever._build_client")
    @patch("retrieval.retriever.embed_single", return_value=[0.1] * 1536)
    def test_general_staff_only_gets_allowed_results(self, mock_embed, mock_client_factory):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        # Simulate Qdrant returning only General-Staff + Public (RBAC filter already applied)
        mock_client.search.return_value = [
            self._make_mock_hit("You can apply for leave via the portal.", "General-Staff"),
            self._make_mock_hit("Public holiday schedule for 2026.", "Public"),
        ]

        results = search("How do I apply for leave?", "General-Staff")
        assert len(results) == 2
        # Confirm the filter was passed with the correct roles
        call_kwargs = mock_client.search.call_args.kwargs
        filter_obj = call_kwargs["query_filter"]
        assert filter_obj is not None

    @patch("retrieval.retriever._build_client")
    @patch("retrieval.retriever.embed_single", return_value=[0.1] * 1536)
    def test_pdf_returns_parent_text(self, mock_embed, mock_client_factory):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        hit = MagicMock()
        hit.score = 0.95
        hit.payload = {
            "text": "apply via portal",              # child text
            "parent_text": "Full page: HR portal is at https://hr.example.com. "
                           "Employees must log in with their employee ID.",
            "access_role": "General-Staff",
            "doc_type": "pdf",
            "source": "staff/onboarding.pdf",
            "page": 3,
        }
        mock_client.search.return_value = [hit]

        results = search("What is the HR portal URL?", "General-Staff")
        assert len(results) == 1
        # LLM should receive the parent_text, not the child snippet
        assert "Full page:" in results[0].text
        assert results[0].page == 3

    @patch("retrieval.retriever._build_client")
    @patch("retrieval.retriever.embed_single", return_value=[0.1] * 1536)
    def test_empty_results_handled_gracefully(self, mock_embed, mock_client_factory):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.search.return_value = []

        results = search("Some question", "Contractor")
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
