#!/usr/bin/env python3
"""
Tests for Memory Store - Cross-Project Learning

22 tests covering:
- Schema (2): tables/indexes created, FTS5 triggers work
- CRUD (3): store with all fields, query returns results, update via store
- FTS5 (3): relevance ranking, porter stemming, phrase matching
- Scoring (4): recency decay at 0/30/90 days, domain boost, category weights, combined
- Check command (2): finds prior failures, returns empty for novel errors
- Auto-capture (2): store healing success, store circuit breaker trip
- GC (2): removes old low-value, preserves high-value recent
- Edge cases (4): empty DB, unicode, very long text, 1000+ entries performance
"""

import importlib.util
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from math import exp
from pathlib import Path

import pytest

# Load memory-store module via importlib (hyphenated filename)
SCRIPT_DIR = Path(__file__).parent
SCRIPT_PATH = SCRIPT_DIR / "memory-store.py"

spec = importlib.util.spec_from_file_location("memory_store", SCRIPT_PATH)
memory_store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory_store)


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary database path and set env var."""
    path = str(tmp_path / "test-memory.db")
    os.environ["QRALPH_MEMORY_DB"] = path
    yield path
    os.environ.pop("QRALPH_MEMORY_DB", None)


@pytest.fixture
def initialized_db(db_path):
    """Provide an initialized database."""
    conn = memory_store.get_connection(db_path)
    conn.executescript(memory_store.SCHEMA_SQL)
    conn.commit()
    conn.close()
    return db_path


def _insert_memory(
    db_path,
    description="test memory",
    domain="backend",
    category="error_pattern",
    context=None,
    resolution=None,
    tags=None,
    success=0,
    project_id=None,
    source=None,
    related_files=None,
    timestamp=None,
):
    """Helper to insert a memory directly."""
    conn = memory_store.get_connection(db_path)
    now = timestamp or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute(
        """INSERT INTO memories
           (timestamp, project_id, domain, category, description,
            context, resolution, tags, success, source, related_files,
            created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (now, project_id, domain, category, description,
         context, resolution, tags, success, source, related_files, now, now),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


# ──────────────────────────────────────────────
# Schema tests (2)
# ──────────────────────────────────────────────


class TestSchema:
    def test_tables_and_indexes_created(self, initialized_db):
        """Tables, FTS5 virtual table, and indexes are all created."""
        conn = memory_store.get_connection(initialized_db)

        # Check memories table exists
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
        ).fetchall()
        assert len(tables) == 1

        # Check FTS5 virtual table exists
        fts_tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories_fts'"
        ).fetchall()
        assert len(fts_tables) == 1

        # Check indexes
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_memories_%'"
        ).fetchall()
        index_names = {row["name"] for row in indexes}
        assert "idx_memories_domain" in index_names
        assert "idx_memories_category" in index_names
        assert "idx_memories_project_id" in index_names
        assert "idx_memories_timestamp" in index_names

        # Check triggers
        triggers = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        ).fetchall()
        trigger_names = {row["name"] for row in triggers}
        assert "memories_ai" in trigger_names
        assert "memories_ad" in trigger_names
        assert "memories_au" in trigger_names

        conn.close()

    def test_fts5_triggers_sync(self, initialized_db):
        """FTS5 triggers keep search index in sync on INSERT, UPDATE, DELETE."""
        conn = memory_store.get_connection(initialized_db)

        # INSERT: should be searchable
        _insert_memory(initialized_db, description="unique_xylophone_pattern")
        results = conn.execute(
            "SELECT * FROM memories_fts WHERE memories_fts MATCH 'unique_xylophone_pattern'"
        ).fetchall()
        assert len(results) == 1

        # UPDATE: old term gone, new term found
        conn.execute(
            "UPDATE memories SET description = 'unique_trombone_pattern' WHERE id = 1"
        )
        conn.commit()
        old_results = conn.execute(
            "SELECT * FROM memories_fts WHERE memories_fts MATCH 'unique_xylophone_pattern'"
        ).fetchall()
        new_results = conn.execute(
            "SELECT * FROM memories_fts WHERE memories_fts MATCH 'unique_trombone_pattern'"
        ).fetchall()
        assert len(old_results) == 0
        assert len(new_results) == 1

        # DELETE: should no longer be searchable
        conn.execute("DELETE FROM memories WHERE id = 1")
        conn.commit()
        deleted_results = conn.execute(
            "SELECT * FROM memories_fts WHERE memories_fts MATCH 'unique_trombone_pattern'"
        ).fetchall()
        assert len(deleted_results) == 0

        conn.close()


# ──────────────────────────────────────────────
# CRUD tests (3)
# ──────────────────────────────────────────────


class TestCRUD:
    def test_store_with_all_fields(self, initialized_db):
        """Store command saves all fields correctly."""
        args = memory_store.build_parser().parse_args([
            "store",
            "--description", "Database connection pool exhausted",
            "--domain", "backend",
            "--category", "error_pattern",
            "--project-id", "015-api-gateway",
            "--context", "Under load testing with 500 concurrent users",
            "--resolution", "Increased pool size from 10 to 50",
            "--tags", "database,performance,connection-pool",
            "--source", "healer-agent",
            "--related-files", "src/db.ts,src/config.ts",
            "--success",
        ])
        result = memory_store.cmd_store(args)

        assert result["status"] == "ok"
        assert result["id"] == 1

        # Verify all fields in DB
        conn = memory_store.get_connection(initialized_db)
        row = conn.execute("SELECT * FROM memories WHERE id = 1").fetchone()
        assert row["description"] == "Database connection pool exhausted"
        assert row["domain"] == "backend"
        assert row["category"] == "error_pattern"
        assert row["project_id"] == "015-api-gateway"
        assert row["context"] == "Under load testing with 500 concurrent users"
        assert row["resolution"] == "Increased pool size from 10 to 50"
        assert row["tags"] == "database,performance,connection-pool"
        assert row["success"] == 1
        assert row["source"] == "healer-agent"
        assert row["related_files"] == "src/db.ts,src/config.ts"
        conn.close()

    def test_query_returns_results(self, initialized_db):
        """Query command returns matching results."""
        _insert_memory(initialized_db, description="Redis cache invalidation bug",
                       domain="backend", category="error_pattern",
                       resolution="Added TTL to cache keys")
        _insert_memory(initialized_db, description="React component rendering loop",
                       domain="frontend", category="error_pattern")

        args = memory_store.build_parser().parse_args([
            "query", "cache invalidation"
        ])
        result = memory_store.cmd_query(args)

        assert result["status"] == "ok"
        assert result["count"] >= 1
        assert any("cache" in r["description"].lower() for r in result["results"])

    def test_update_via_store_creates_new_entry(self, initialized_db):
        """Storing again creates a new entry (append-only)."""
        _insert_memory(initialized_db, description="First approach to auth",
                       domain="security", category="failed_approach")

        args = memory_store.build_parser().parse_args([
            "store",
            "--description", "Second approach to auth using JWT",
            "--domain", "security",
            "--category", "successful_workaround",
            "--success",
        ])
        result = memory_store.cmd_store(args)
        assert result["id"] == 2

        conn = memory_store.get_connection(initialized_db)
        count = conn.execute("SELECT COUNT(*) AS cnt FROM memories").fetchone()["cnt"]
        assert count == 2
        conn.close()


# ──────────────────────────────────────────────
# FTS5 tests (3)
# ──────────────────────────────────────────────


class TestFTS5:
    def test_relevance_ranking(self, initialized_db):
        """More relevant results rank higher."""
        _insert_memory(initialized_db, description="database migration failed with timeout",
                       domain="backend", category="error_pattern",
                       context="database schema migration on large table")
        _insert_memory(initialized_db, description="CSS animation performance issue",
                       domain="frontend", category="error_pattern")

        args = memory_store.build_parser().parse_args([
            "query", "database migration"
        ])
        result = memory_store.cmd_query(args)

        assert result["count"] >= 1
        assert "database" in result["results"][0]["description"].lower()

    def test_porter_stemming(self, initialized_db):
        """Porter stemmer allows 'failing' to match 'failed'."""
        _insert_memory(initialized_db, description="deployment failed due to OOM",
                       domain="devops", category="failed_approach")

        args = memory_store.build_parser().parse_args([
            "query", "failing deployment"
        ])
        result = memory_store.cmd_query(args)

        assert result["count"] >= 1
        assert "failed" in result["results"][0]["description"].lower()

    def test_phrase_matching(self, initialized_db):
        """Phrase queries match exact sequences."""
        _insert_memory(initialized_db, description="connection pool exhausted under load",
                       domain="backend", category="error_pattern")
        _insert_memory(initialized_db, description="pool party event handler",
                       domain="frontend", category="architectural_decision")

        args = memory_store.build_parser().parse_args([
            "query", '"connection pool"'
        ])
        result = memory_store.cmd_query(args)

        assert result["count"] >= 1
        assert "connection pool" in result["results"][0]["description"].lower()


# ──────────────────────────────────────────────
# Scoring tests (4)
# ──────────────────────────────────────────────


class TestScoring:
    def test_recency_decay_zero_days(self, initialized_db):
        """Score at 0 days old has recency ~1.0."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        score = memory_store._compute_score(
            bm25_rank=-1.0,
            created_at=now,
            domain="backend",
            category="error_pattern",
        )
        # recency should be ~1.0, relevance = 1/(1+1) = 0.5
        expected_recency = 1.0
        expected = 0.5 * expected_recency * 1.0 * 1.0  # 0.5
        assert abs(score - expected) < 0.05

    def test_recency_decay_30_days(self, initialized_db):
        """Score at 30 days old has recency ~0.5 (half-life)."""
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        score = memory_store._compute_score(
            bm25_rank=-1.0,
            created_at=thirty_days_ago,
            domain="backend",
            category="error_pattern",
        )
        # recency = exp(-0.693) ~= 0.5, relevance = 0.5
        expected = 0.5 * 0.5 * 1.0 * 1.0  # ~0.25
        assert abs(score - expected) < 0.05

    def test_recency_decay_90_days(self, initialized_db):
        """Score at 90 days old has very low recency."""
        ninety_days_ago = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
        score = memory_store._compute_score(
            bm25_rank=-1.0,
            created_at=ninety_days_ago,
            domain="backend",
            category="error_pattern",
        )
        # recency = exp(-0.693 * 3) ~= 0.125
        expected = 0.5 * 0.125 * 1.0 * 1.0  # ~0.0625
        assert abs(score - expected) < 0.02

    def test_domain_boost(self, initialized_db):
        """Domain match gives 1.5x boost."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        score_match = memory_store._compute_score(
            bm25_rank=-1.0,
            created_at=now,
            domain="backend",
            category="error_pattern",
            query_domain="backend",
        )
        score_no_match = memory_store._compute_score(
            bm25_rank=-1.0,
            created_at=now,
            domain="backend",
            category="error_pattern",
            query_domain="frontend",
        )
        assert abs(score_match / score_no_match - 1.5) < 0.01

    def test_category_weights(self, initialized_db):
        """Category weights: workaround > decision > error > failed."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        scores = {}
        for cat in memory_store.VALID_CATEGORIES:
            scores[cat] = memory_store._compute_score(
                bm25_rank=-1.0,
                created_at=now,
                domain="backend",
                category=cat,
            )

        assert scores["successful_workaround"] > scores["architectural_decision"]
        assert scores["architectural_decision"] > scores["error_pattern"]
        assert scores["error_pattern"] > scores["failed_approach"]

    def test_combined_scoring_formula(self, initialized_db):
        """Full composite score = relevance * recency * domain_boost * category_weight."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        score = memory_store._compute_score(
            bm25_rank=-2.0,
            created_at=now,
            domain="backend",
            category="successful_workaround",
            query_domain="backend",
        )
        # relevance = 1/(1+2) = 0.333, recency ~1.0, domain=1.5, category=1.3
        expected = (1.0 / 3.0) * 1.0 * 1.5 * 1.3
        assert abs(score - expected) < 0.05


# ──────────────────────────────────────────────
# Check command tests (2)
# ──────────────────────────────────────────────


class TestCheck:
    def test_finds_prior_failures(self, initialized_db):
        """Check command finds prior failed approaches."""
        _insert_memory(initialized_db,
                       description="Tried WebSocket approach for real-time sync but failed",
                       domain="backend", category="failed_approach",
                       context="WebSocket connections dropped under proxy")
        _insert_memory(initialized_db,
                       description="WebSocket monitoring dashboard works great",
                       domain="frontend", category="successful_workaround", success=1)

        args = memory_store.build_parser().parse_args(["check", "WebSocket"])
        result = memory_store.cmd_check(args)

        assert result["tried_before"] is True
        assert result["count"] >= 1
        # Should only return failures, not successes
        for entry in result["prior_failures"]:
            assert entry["category"] in ("failed_approach", "error_pattern")

    def test_returns_empty_for_novel_errors(self, initialized_db):
        """Check command returns empty for never-seen-before errors."""
        _insert_memory(initialized_db,
                       description="Redis timeout under heavy load",
                       domain="backend", category="error_pattern")

        args = memory_store.build_parser().parse_args(["check", "quantum_entanglement_error"])
        result = memory_store.cmd_check(args)

        assert result["tried_before"] is False
        assert result["count"] == 0


# ──────────────────────────────────────────────
# Auto-capture tests (2)
# ──────────────────────────────────────────────


class TestAutoCapture:
    def test_store_healing_success(self, initialized_db):
        """Store a healing success memory via CLI args."""
        args = memory_store.build_parser().parse_args([
            "store",
            "--description", "Self-healed OOM error by reducing batch size from 1000 to 100",
            "--domain", "backend",
            "--category", "successful_workaround",
            "--project-id", "018-data-pipeline",
            "--context", "Healer agent detected OOM kill in container logs",
            "--resolution", "Reduced batch size, added memory monitoring",
            "--tags", "oom,healing,batch-size",
            "--source", "healer-agent",
            "--success",
        ])
        result = memory_store.cmd_store(args)

        assert result["status"] == "ok"

        conn = memory_store.get_connection(initialized_db)
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (result["id"],)).fetchone()
        assert row["success"] == 1
        assert row["category"] == "successful_workaround"
        assert row["source"] == "healer-agent"
        conn.close()

    def test_store_circuit_breaker_trip(self, initialized_db):
        """Store a circuit breaker trip as failed_approach."""
        args = memory_store.build_parser().parse_args([
            "store",
            "--description", "Circuit breaker tripped after 5 consecutive failures on OpenAI API",
            "--domain", "infrastructure",
            "--category", "error_pattern",
            "--project-id", "019-llm-gateway",
            "--context", "Rate limit exceeded, retries exhausted",
            "--tags", "circuit-breaker,openai,rate-limit",
            "--source", "orchestrator",
        ])
        result = memory_store.cmd_store(args)

        assert result["status"] == "ok"

        conn = memory_store.get_connection(initialized_db)
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (result["id"],)).fetchone()
        assert row["success"] == 0
        assert row["category"] == "error_pattern"
        conn.close()


# ──────────────────────────────────────────────
# GC tests (2)
# ──────────────────────────────────────────────


class TestGC:
    def test_removes_old_low_value_entries(self, initialized_db):
        """GC removes old failed/error entries that are not successful."""
        old_ts = (datetime.utcnow() - timedelta(days=120)).strftime("%Y-%m-%d %H:%M:%S")
        _insert_memory(initialized_db,
                       description="Old failed approach",
                       domain="backend", category="failed_approach",
                       timestamp=old_ts, success=0)
        _insert_memory(initialized_db,
                       description="Old error pattern",
                       domain="backend", category="error_pattern",
                       timestamp=old_ts, success=0)

        args = memory_store.build_parser().parse_args(["gc", "--older-than-days", "90"])
        result = memory_store.cmd_gc(args)

        assert result["deleted"] == 2
        assert result["remaining"] == 0

    def test_preserves_high_value_recent_entries(self, initialized_db):
        """GC preserves successful entries and recent entries."""
        old_ts = (datetime.utcnow() - timedelta(days=120)).strftime("%Y-%m-%d %H:%M:%S")
        recent_ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Old but successful -- should survive
        _insert_memory(initialized_db,
                       description="Old successful workaround",
                       domain="backend", category="successful_workaround",
                       timestamp=old_ts, success=1)
        # Old architectural decision -- should survive (not failed/error)
        _insert_memory(initialized_db,
                       description="Old architectural decision",
                       domain="backend", category="architectural_decision",
                       timestamp=old_ts)
        # Recent failed approach -- should survive (too new)
        _insert_memory(initialized_db,
                       description="Recent failed approach",
                       domain="backend", category="failed_approach",
                       timestamp=recent_ts, success=0)
        # Old failed with success=0 -- should be deleted
        _insert_memory(initialized_db,
                       description="Old deletable failure",
                       domain="backend", category="failed_approach",
                       timestamp=old_ts, success=0)

        args = memory_store.build_parser().parse_args(["gc", "--older-than-days", "90"])
        result = memory_store.cmd_gc(args)

        assert result["deleted"] == 1
        assert result["remaining"] == 3


# ──────────────────────────────────────────────
# Edge case tests (4)
# ──────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_db_returns_empty(self, initialized_db):
        """Query on empty DB returns empty results without error."""
        args = memory_store.build_parser().parse_args(["query", "anything"])
        result = memory_store.cmd_query(args)

        assert result["count"] == 0
        assert result["results"] == []

    def test_unicode_text(self, initialized_db):
        """Unicode text is stored and retrieved correctly."""
        desc = "Fehler bei der Datenbankverbindung: \u00fc\u00f6\u00e4\u00df \u65e5\u672c\u8a9e \U0001f680"
        _insert_memory(initialized_db, description=desc,
                       domain="backend", category="error_pattern",
                       context="\u4e2d\u6587\u4e0a\u4e0b\u6587",
                       tags="\u00e9tiquettes,\u30bf\u30b0")

        args = memory_store.build_parser().parse_args(["query", "Datenbankverbindung"])
        result = memory_store.cmd_query(args)

        assert result["count"] >= 1
        assert "\u00fc\u00f6\u00e4\u00df" in result["results"][0]["description"]

    def test_very_long_text(self, initialized_db):
        """Text >10000 chars is stored and retrieved."""
        long_desc = "error " * 2000  # ~12000 chars
        _insert_memory(initialized_db, description=long_desc,
                       domain="backend", category="error_pattern")

        conn = memory_store.get_connection(initialized_db)
        row = conn.execute("SELECT description FROM memories WHERE id = 1").fetchone()
        assert len(row["description"]) > 10000
        conn.close()

        args = memory_store.build_parser().parse_args(["query", "error"])
        result = memory_store.cmd_query(args)
        assert result["count"] >= 1

    def test_1000_entries_performance(self, initialized_db):
        """1000+ entries query completes in <2 seconds."""
        conn = memory_store.get_connection(initialized_db)

        # Bulk insert 1000 entries
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        categories = list(memory_store.VALID_CATEGORIES)
        rows = []
        for i in range(1000):
            cat = categories[i % len(categories)]
            rows.append((
                now, f"proj-{i % 10}", "backend", cat,
                f"Memory entry {i} about database error number {i}",
                f"context for entry {i}", f"resolution {i}",
                f"tag{i},perf", 0, "test", None, now, now,
            ))

        conn.executemany(
            """INSERT INTO memories
               (timestamp, project_id, domain, category, description,
                context, resolution, tags, success, source, related_files,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        conn.close()

        start = time.time()
        args = memory_store.build_parser().parse_args(["query", "database error"])
        result = memory_store.cmd_query(args)
        elapsed = time.time() - start

        assert elapsed < 2.0, f"Query took {elapsed:.2f}s, expected <2s"
        assert result["count"] > 0
