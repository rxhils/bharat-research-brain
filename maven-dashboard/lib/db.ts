// Real DB access for the dashboard. SERVER-ONLY — never import from a client component.
// Reads DATABASE_URL (Neon in production, local Docker Postgres in dev). Zero mock.

import { Pool } from "pg";

let _pool: Pool | null = null;

/** True when a DATABASE_URL is configured. The data layer shows honest empty
 *  states (not mock) when this is false. */
export function dbReady(): boolean {
  return !!process.env.DATABASE_URL;
}

function pool(): Pool {
  if (!_pool) {
    const cs = process.env.DATABASE_URL;
    if (!cs) throw new Error("DATABASE_URL is not set");
    const local = cs.includes("localhost") || cs.includes("127.0.0.1");
    _pool = new Pool({
      connectionString: cs,
      // Neon and most hosted PG require SSL; local Docker does not.
      ssl: local ? false : { rejectUnauthorized: false },
      max: 3,
    });
  }
  return _pool;
}

/** Run a parameterized read query and return rows. */
export async function q<T = Record<string, unknown>>(
  text: string,
  params: unknown[] = [],
): Promise<T[]> {
  const res = await pool().query(text, params);
  return res.rows as T[];
}
