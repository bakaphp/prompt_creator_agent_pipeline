# Prompt Creator Agent Pipeline



## Postgres Configuration

### Add prompt_quality_results table for quality results storage.

Run the followinf query:

``` sql
CREATE TABLE prompts_quality_results (
    id SERIAL PRIMARY KEY,
    prompt TEXT NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('PASS', 'FAIL', 'PENDING')),
	reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

```