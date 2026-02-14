#!/usr/bin/env python3
"""
Memory Store - Cross-Project Learning

SQLite + FTS5 memory store for learning from failures across QRALPH projects.

Usage:
    memory-store.py init
    memory-store.py store --description "..." --domain "..." --category "..." [options]
    memory-store.py query "search terms" [--domain X] [--category X] [--limit N]
    memory-store.py check "has this been tried before?"
    memory-store.py stats [--domain X]
    memory-store.py export [--format json|md]
    memory-store.py gc [--older-than-days N]

Output: All commands print JSON.
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from math import exp
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_DB_PATH = os.path.join(".claude", "memory", "exec-team-memory.db")
DB_PATH = os.environ.get("QRALPH_MEMORY_DB", DEFAULT_DB_PATH)

VALID_CATEGORIES = (
    "error_pattern",
    "failed_approach",
    "successful_workaround",
    "architectural_decision",
)

CATEGORY_WEIGHTS = {
    "successful_workaround": 1.3,
    "architectural_decision": 1.2,
    "error_pattern": 1.0,
    "failed_approach": 0.9,
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    project_id TEXT,
    domain TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN (
        'error_pattern', 'failed_approach',
        'successful_workaround', 'architectural_decision'
    )),
    description TEXT NOT NULL,
    context TEXT,
    resolution TEXT,
    tags TEXT,
    success INTEGER NOT NULL DEFAULT 0,
    source TEXT,
    related_files TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    description, context, resolution, tags,
    content=memories, content_rowid=id,
    tokenize='porter unicode61'
);

-- Triggers to keep FTS5 in sync
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, description, context, resolution, tags)
    VALUES (new.id, new.description, new.context, new.resolution, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, description, context, resolution, tags)
    VALUES ('delete', old.id, old.description, old.context, old.resolution, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, description, context, resolution, tags)
    VALUES ('delete', old.id, old.description, old.context, old.resolution, old.tags);
    INSERT INTO memories_fts(rowid, description, context, resolution, tags)
    VALUES (new.id, new.description, new.context, new.resolution, new.tags);
END;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_memories_domain ON memories(domain);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_project_id ON memories(project_id);
CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp DESC);
"""


def get_db_path() -> str:
    """Return the configured database path."""
    return os.environ.get("QRALPH_MEMORY_DB", DEFAULT_DB_PATH)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open a connection to the memory database."""
    path = db_path or get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def cmd_init(args: argparse.Namespace) -> Dict[str, Any]:
    """Create DB and schema."""
    db_path = get_db_path()
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        return {"status": "ok", "db_path": db_path, "message": "Memory store initialized"}
    finally:
        conn.close()


def cmd_store(args: argparse.Namespace) -> Dict[str, Any]:
    """Store a new memory."""
    if args.category not in VALID_CATEGORIES:
        return {"error": f"Invalid category: {args.category}. Must be one of {VALID_CATEGORIES}"}

    conn = get_connection()
    try:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.execute(
            """INSERT INTO memories
               (timestamp, project_id, domain, category, description,
                context, resolution, tags, success, source, related_files,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                now,
                args.project_id,
                args.domain,
                args.category,
                args.description,
                args.context,
                args.resolution,
                args.tags,
                1 if args.success else 0,
                args.source,
                args.related_files,
                now,
                now,
            ),
        )
        conn.commit()
        return {
            "status": "ok",
            "id": cursor.lastrowid,
            "message": f"Memory stored with id {cursor.lastrowid}",
        }
    finally:
        conn.close()


def _compute_score(
    bm25_rank: float,
    created_at: str,
    domain: str,
    category: str,
    query_domain: Optional[str] = None,
) -> float:
    """Compute composite relevance score.

    score = relevance * recency_decay * domain_boost * category_weight

    relevance  = 1.0 / (1.0 + abs(fts5_bm25_rank))
    recency    = exp(-0.693 * days_old / 30)   (30-day half-life)
    domain     = 1.5 if domain matches query, else 1.0
    category   = {workaround: 1.3, decision: 1.2, error: 1.0, failed: 0.9}
    """
    relevance = 1.0 / (1.0 + abs(bm25_rank))

    try:
        dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        dt = datetime.utcnow()
    days_old = max((datetime.utcnow() - dt).total_seconds() / 86400, 0)
    recency = exp(-0.693 * days_old / 30)

    domain_boost = 1.5 if query_domain and domain == query_domain else 1.0

    category_weight = CATEGORY_WEIGHTS.get(category, 1.0)

    return relevance * recency * domain_boost * category_weight


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


def cmd_query(args: argparse.Namespace) -> Dict[str, Any]:
    """Query memories using FTS5 with two-phase scoring."""
    search_terms = args.search_terms
    limit = args.limit or 10

    conn = get_connection()
    try:
        # Phase 1: FTS5 BM25 retrieval of top 50 candidates
        query_parts = []
        params: list = []

        query_parts.append(
            """SELECT m.*, bm25(memories_fts) AS rank
               FROM memories_fts
               JOIN memories m ON m.id = memories_fts.rowid
               WHERE memories_fts MATCH ?"""
        )
        params.append(search_terms)

        if args.domain:
            query_parts.append("AND m.domain = ?")
            params.append(args.domain)
        if args.category:
            query_parts.append("AND m.category = ?")
            params.append(args.category)

        query_parts.append("ORDER BY rank LIMIT 50")

        sql = " ".join(query_parts)
        rows = conn.execute(sql, params).fetchall()

        # Phase 2: Re-rank by composite score
        results = []
        for row in rows:
            row_dict = _row_to_dict(row)
            score = _compute_score(
                bm25_rank=row_dict["rank"],
                created_at=row_dict["created_at"],
                domain=row_dict["domain"],
                category=row_dict["category"],
                query_domain=args.domain,
            )
            row_dict["score"] = round(score, 4)
            del row_dict["rank"]
            results.append(row_dict)

        results.sort(key=lambda r: r["score"], reverse=True)
        results = results[:limit]

        return {
            "status": "ok",
            "query": search_terms,
            "total_candidates": len(rows),
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        return {"status": "ok", "query": search_terms, "results": [], "count": 0, "note": str(e)}
    finally:
        conn.close()


def cmd_check(args: argparse.Namespace) -> Dict[str, Any]:
    """Check if something has been tried before (filters for failures)."""
    search_terms = args.search_terms

    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT m.*, bm25(memories_fts) AS rank
               FROM memories_fts
               JOIN memories m ON m.id = memories_fts.rowid
               WHERE memories_fts MATCH ?
               AND m.category IN ('failed_approach', 'error_pattern')
               ORDER BY rank
               LIMIT 50""",
            (search_terms,),
        ).fetchall()

        results = []
        for row in rows:
            row_dict = _row_to_dict(row)
            score = _compute_score(
                bm25_rank=row_dict["rank"],
                created_at=row_dict["created_at"],
                domain=row_dict["domain"],
                category=row_dict["category"],
            )
            row_dict["score"] = round(score, 4)
            del row_dict["rank"]
            results.append(row_dict)

        results.sort(key=lambda r: r["score"], reverse=True)
        results = results[:10]

        return {
            "status": "ok",
            "query": search_terms,
            "prior_failures": results,
            "count": len(results),
            "tried_before": len(results) > 0,
        }
    except Exception as e:
        return {
            "status": "ok",
            "query": search_terms,
            "prior_failures": [],
            "count": 0,
            "tried_before": False,
            "note": str(e),
        }
    finally:
        conn.close()


def cmd_stats(args: argparse.Namespace) -> Dict[str, Any]:
    """Show statistics about the memory store."""
    conn = get_connection()
    try:
        # Total count
        total = conn.execute("SELECT COUNT(*) AS cnt FROM memories").fetchone()["cnt"]

        # By category
        category_rows = conn.execute(
            "SELECT category, COUNT(*) AS cnt FROM memories GROUP BY category"
        ).fetchall()
        by_category = {row["category"]: row["cnt"] for row in category_rows}

        # By domain
        domain_filter = ""
        params: list = []
        if args.domain:
            domain_filter = "WHERE domain = ?"
            params = [args.domain]

        domain_rows = conn.execute(
            f"SELECT domain, COUNT(*) AS cnt FROM memories {domain_filter} GROUP BY domain",
            params,
        ).fetchall()
        by_domain = {row["domain"]: row["cnt"] for row in domain_rows}

        # Success rate
        success_count = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM memories {domain_filter} AND success = 1"
            if domain_filter
            else "SELECT COUNT(*) AS cnt FROM memories WHERE success = 1",
            params,
        ).fetchone()["cnt"]

        filtered_total = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM memories {domain_filter}", params
        ).fetchone()["cnt"]

        success_rate = round(success_count / filtered_total, 2) if filtered_total > 0 else 0.0

        # Recent entries
        recent = conn.execute(
            "SELECT COUNT(*) AS cnt FROM memories WHERE timestamp > datetime('now', '-7 days')"
        ).fetchone()["cnt"]

        return {
            "status": "ok",
            "total": total,
            "filtered_total": filtered_total,
            "by_category": by_category,
            "by_domain": by_domain,
            "success_rate": success_rate,
            "recent_7_days": recent,
        }
    finally:
        conn.close()


def cmd_export(args: argparse.Namespace) -> Dict[str, Any]:
    """Export all memories."""
    fmt = args.format or "json"

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM memories ORDER BY timestamp DESC"
        ).fetchall()
        memories = [_row_to_dict(row) for row in rows]

        if fmt == "md":
            lines = ["# Memory Store Export", ""]
            for mem in memories:
                lines.append(f"## [{mem['id']}] {mem['description'][:80]}")
                lines.append(f"- **Domain**: {mem['domain']}")
                lines.append(f"- **Category**: {mem['category']}")
                lines.append(f"- **Project**: {mem.get('project_id', 'N/A')}")
                lines.append(f"- **Success**: {'Yes' if mem['success'] else 'No'}")
                lines.append(f"- **Created**: {mem['created_at']}")
                if mem.get("context"):
                    lines.append(f"- **Context**: {mem['context']}")
                if mem.get("resolution"):
                    lines.append(f"- **Resolution**: {mem['resolution']}")
                if mem.get("tags"):
                    lines.append(f"- **Tags**: {mem['tags']}")
                lines.append("")
            return {"status": "ok", "format": "md", "content": "\n".join(lines), "count": len(memories)}

        return {"status": "ok", "format": "json", "memories": memories, "count": len(memories)}
    finally:
        conn.close()


def cmd_gc(args: argparse.Namespace) -> Dict[str, Any]:
    """Garbage collect old low-value entries."""
    older_than_days = args.older_than_days or 90

    conn = get_connection()
    try:
        cutoff = (datetime.utcnow() - timedelta(days=older_than_days)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Only delete failed_approach and error_pattern that are old and not successful
        cursor = conn.execute(
            """DELETE FROM memories
               WHERE timestamp < ?
               AND success = 0
               AND category IN ('failed_approach', 'error_pattern')""",
            (cutoff,),
        )
        deleted = cursor.rowcount
        conn.commit()

        remaining = conn.execute("SELECT COUNT(*) AS cnt FROM memories").fetchone()["cnt"]

        return {
            "status": "ok",
            "deleted": deleted,
            "remaining": remaining,
            "cutoff_date": cutoff,
            "older_than_days": older_than_days,
        }
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Memory Store - Cross-Project Learning for QRALPH"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    subparsers.add_parser("init", help="Create DB and schema")

    # store
    store_parser = subparsers.add_parser("store", help="Store a new memory")
    store_parser.add_argument("--description", required=True, help="Description of the memory")
    store_parser.add_argument("--domain", required=True, help="Domain (e.g., frontend, backend)")
    store_parser.add_argument(
        "--category",
        required=True,
        choices=VALID_CATEGORIES,
        help="Category of memory",
    )
    store_parser.add_argument("--project-id", dest="project_id", help="Project ID")
    store_parser.add_argument("--context", help="Additional context")
    store_parser.add_argument("--resolution", help="How it was resolved")
    store_parser.add_argument("--tags", help="Comma-separated tags")
    store_parser.add_argument("--source", help="Source file or agent")
    store_parser.add_argument("--related-files", dest="related_files", help="Related file paths")
    store_parser.add_argument(
        "--success", action="store_true", default=False, help="Mark as successful"
    )

    # query
    query_parser = subparsers.add_parser("query", help="Query memories")
    query_parser.add_argument("search_terms", help="Search terms for FTS5")
    query_parser.add_argument("--domain", help="Filter by domain")
    query_parser.add_argument("--category", choices=VALID_CATEGORIES, help="Filter by category")
    query_parser.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")

    # check
    check_parser = subparsers.add_parser("check", help="Check if tried before (failures only)")
    check_parser.add_argument("search_terms", help="Search terms to check")

    # stats
    stats_parser = subparsers.add_parser("stats", help="Show memory store statistics")
    stats_parser.add_argument("--domain", help="Filter stats by domain")

    # export
    export_parser = subparsers.add_parser("export", help="Export memories")
    export_parser.add_argument(
        "--format", choices=["json", "md"], default="json", help="Export format"
    )

    # gc
    gc_parser = subparsers.add_parser("gc", help="Garbage collect old entries")
    gc_parser.add_argument(
        "--older-than-days",
        dest="older_than_days",
        type=int,
        default=90,
        help="Delete entries older than N days (default: 90)",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "init": cmd_init,
        "store": cmd_store,
        "query": cmd_query,
        "check": cmd_check,
        "stats": cmd_stats,
        "export": cmd_export,
        "gc": cmd_gc,
    }

    handler = commands.get(args.command)
    if not handler:
        print(json.dumps({"error": f"Unknown command: {args.command}"}), file=sys.stderr)
        sys.exit(1)

    try:
        result = handler(args)
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
