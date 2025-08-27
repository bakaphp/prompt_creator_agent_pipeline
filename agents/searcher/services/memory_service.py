import asyncpg

class DatabaseMemoryService(object):
    """
    A memory service that uses a database for storage.
    """
    def __init__(self, db_url: str):
        self.db_url = db_url

    async def retrieve_prompt_quality_results(self, status: str) -> dict:
        """Retrieve prompt quality results based on status."""
        conn = await asyncpg.connect(self.db_url)
        rows = await conn.fetch(
            "SELECT * FROM prompts_quality_results WHERE status = $1", status
        )
        await conn.close()
        return [dict(row) for row in rows]

    async def store_quality_result(self, prompt: str, status: str, reason: str) -> bool:
        """Store memory for a specific prompt."""
        conn = await asyncpg.connect(self.db_url)
        result = await conn.execute(
            "INSERT INTO prompts_quality_results (prompt, status, reason, created_at) VALUES ($1, $2, $3, NOW())",
            prompt,
            status,
            reason
        )
        return result == "INSERT 0 1"