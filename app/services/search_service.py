from __future__ import annotations

from difflib import SequenceMatcher
from typing import Sequence

from app.db.database import Database
from app.utils import normalize


class SearchService:
    def __init__(self, db: Database):
        self.db = db

    async def search_products(
        self,
        query: str,
        *,
        shop_id: int | None = None,
        business_type: str | None = None,
        limit: int = 20,
        active_only: bool = True,
    ) -> Sequence[dict]:
        normalized = normalize(query)
        if len(normalized) < 2:
            return []

        terms = {normalized}
        terms.update(await self._load_synonyms(normalized, shop_id=shop_id, business_type=business_type))
        like_terms = [f"%{t}%" for t in terms if t]
        if not like_terms:
            return []

        base_query = [
            "SELECT p.* FROM products p",
        ]
        params: list[object] = []
        if business_type:
            base_query.append("JOIN shops s ON s.id = p.shop_id")

        where = ["1=1"]
        if shop_id is not None:
            where.append("p.shop_id=?")
            params.append(shop_id)
        if business_type is not None:
            where.append("s.business_type=?")
            params.append(business_type)
        if active_only:
            where.append("p.is_active=1")

        like_clauses = []
        for _ in like_terms:
            like_clauses.append("(p.name_norm LIKE ? OR p.keywords_norm LIKE ?)")
        for term in like_terms:
            params.extend([term, term])
        where.append("(" + " OR ".join(like_clauses) + ")")

        base_query.append("WHERE " + " AND ".join(where))
        base_query.append("ORDER BY p.id DESC")
        base_query.append("LIMIT ?")
        params.append(max(limit * 3, limit))

        async with self.db.conn() as conn:
            cur = await conn.execute(" ".join(base_query), params)
            rows = [dict(r) for r in await cur.fetchall()]

            if not rows:
                fallback = [
                    "SELECT p.* FROM products p",
                ]
                fallback_params: list[object] = []
                if business_type:
                    fallback.append("JOIN shops s ON s.id = p.shop_id")
                fallback_where = ["1=1"]
                if shop_id is not None:
                    fallback_where.append("p.shop_id=?")
                    fallback_params.append(shop_id)
                if business_type is not None:
                    fallback_where.append("s.business_type=?")
                    fallback_params.append(business_type)
                if active_only:
                    fallback_where.append("p.is_active=1")
                fallback.append("WHERE " + " AND ".join(fallback_where))
                fallback.append("ORDER BY p.id DESC LIMIT ?")
                fallback_params.append(max(limit * 5, 50))
                cur = await conn.execute(" ".join(fallback), fallback_params)
                rows = [dict(r) for r in await cur.fetchall()]

        scored = []
        for row in rows:
            name_norm = normalize(row.get("name", ""))
            score = _similarity(normalized, name_norm)
            if normalized in name_norm:
                score = max(score, 0.9)
            if score >= 0.55:
                scored.append((score, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:limit]]

    async def _load_synonyms(
        self,
        term: str,
        *,
        shop_id: int | None,
        business_type: str | None,
    ) -> set[str]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """
                SELECT term, synonym
                FROM search_synonyms
                WHERE (shop_id IS NULL OR shop_id=?)
                  AND (business_type IS NULL OR business_type=?)
                  AND term=?
                """,
                (shop_id, business_type, term),
            )
            rows = await cur.fetchall()
        return {normalize(r["synonym"]) for r in rows if r["synonym"]}


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()
