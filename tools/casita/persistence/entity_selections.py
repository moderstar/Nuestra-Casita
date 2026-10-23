"""PostgreSQL persistence for Home Assistant entity selections."""

from __future__ import annotations

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class EntitySelection:
    entity_id: str
    enabled: bool
    room: str | None = None


class EntitySelectionRepository:
    """Store household-scoped Home Assistant entity preferences."""

    def __init__(self, connection_string: str):
        self._connection_string = connection_string

    def _connect(self):
        return psycopg.connect(
            self._connection_string,
            connect_timeout=5,
        )

    def initialize(
        self,
        household_id: str,
        legacy_entity_ids: tuple[str, ...] = (),
    ) -> None:
        """Create schema and import legacy selections exactly once."""

        with self._connect() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (f"nuestra-casita:ha-migration:{household_id}",),
            )
            connection.execute("""
                CREATE TABLE IF NOT EXISTS ha_entity_selections (
                    household_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    room TEXT,
                    PRIMARY KEY (household_id, entity_id)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS ha_selection_migrations (
                    household_id TEXT PRIMARY KEY,
                    migrated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            migrated = connection.execute(
                """
                SELECT 1 FROM ha_selection_migrations
                WHERE household_id = %s
                FOR UPDATE
                """,
                (household_id,),
            ).fetchone()

            if migrated is None:
                inserted = connection.execute(
                    """
                    INSERT INTO ha_selection_migrations (household_id)
                    VALUES (%s)
                    ON CONFLICT DO NOTHING
                    RETURNING household_id
                    """,
                    (household_id,),
                ).fetchone()

                if inserted is not None:
                    for entity_id in legacy_entity_ids:
                        connection.execute(
                            """
                            INSERT INTO ha_entity_selections
                                (household_id, entity_id, enabled)
                            VALUES (%s, %s, TRUE)
                            ON CONFLICT DO NOTHING
                            """,
                            (household_id, entity_id),
                        )

    def list(self, household_id: str) -> tuple[EntitySelection, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT entity_id, enabled, room
                FROM ha_entity_selections
                WHERE household_id = %s
                ORDER BY entity_id
                """,
                (household_id,),
            ).fetchall()

        return tuple(EntitySelection(*row) for row in rows)

    def enabled_entity_ids(self, household_id: str) -> tuple[str, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT entity_id
                FROM ha_entity_selections
                WHERE household_id = %s AND enabled = TRUE
                ORDER BY entity_id
                """,
                (household_id,),
            ).fetchall()

        return tuple(row[0] for row in rows)

    def save(
        self,
        household_id: str,
        entity_id: str,
        *,
        enabled: bool,
        room: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ha_entity_selections
                    (household_id, entity_id, enabled, room)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (household_id, entity_id)
                DO UPDATE SET
                    enabled = EXCLUDED.enabled,
                    room = EXCLUDED.room
                """,
                (household_id, entity_id, enabled, room),
            )
