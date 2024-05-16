from asyncio import run
from aiosqlite import connect

class ChallengeState:
    def __init__(self, db, challenge_name: str, user_id: str):
        self.db = db
        self.challenge_name = challenge_name
        self.user_id = user_id

    async def get(self):
        state = await self.get_with_reason()
        if state is None:
            return None
        st, _ = state
        return st

    async def create_challenge(self):
        async with connect(self.db.file) as db:
            await db.execute("INSERT INTO challenges \
                (name, user_id, state, reason) \
                VALUES (?, ?, ?, ?)",
                (self.challenge_name, self.user_id, "created", ""))
            await db.commit()

    async def get_with_reason(self):
        async with connect(self.db.file) as db:
            res = await db.execute("SELECT state, reason FROM challenges \
                WHERE name=? AND user_id=? LIMIT 1",
                (self.challenge_name, self.user_id))
            return await res.fetchone()

    async def set(self, state: str, reason: str = ""):
        async with connect(self.db.file) as db:
            await db.execute("UPDATE challenges SET state=?, reason=?\
                WHERE name=? AND user_id=?",
                (state, reason, self.challenge_name, self.user_id))
            await db.commit()

    async def set_server(self, server_idx: int):
        async with connect(self.db.file) as db:
            await db.execute("UPDATE challenges SET server=?\
                WHERE name=? AND user_id=?",
                (server_idx, self.challenge_name, self.user_id))
            await db.commit()

    async def get_server(self) -> int | None:
        async with connect(self.db.file) as db:
            res = await db.execute("SELECT server FROM challenges \
                WHERE name=? AND user_id=? LIMIT 1",
                (self.challenge_name, self.user_id))
            res = await res.fetchone()
            if res is None:
                return None
            else:
                return res[0]

    async def delete(self):
        async with connect(self.db.file) as db:
            await db.execute("DELETE FROM challenges WHERE name=? AND user_id=?",
                (self.challenge_name, self.user_id))
            await db.commit()

    async def delete_and_insert(self, state):
        async with connect(self.db.file) as db:
            await db.execute("DELETE FROM challenges WHERE name=? AND user_id=?",
                (self.challenge_name, self.user_id))
            await db.execute("INSERT INTO challenges \
                (name, user_id, state, reason) \
                VALUES (?, ?, ?, ?)",
                (self.challenge_name, self.user_id, state, ""))
            await db.commit()

class Database():
    def __init__(self, file: str) -> None:
        self.file = file
        run(self.setup())

    async def setup(self):
        async with connect(self.file) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS challenges ( \
                name TEXT NOT NULL, \
                user_id TEXT NOT NULL, \
                server INTEGER, \
                state TEXT NOT NULL,\
                reason TEXT NOT NULL,\
                PRIMARY KEY (name, user_id) \
            )")
            await db.commit()

