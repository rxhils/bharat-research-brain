// Real DB access for the dashboard. SERVER-ONLY — never import from a client component.
// Reads DATABASE_URL (Supabase pooler in production, local Docker Postgres in dev). Zero mock.

import { Pool, type PoolConfig } from "pg";

let _pool: Pool | null = null;

/** True when a DATABASE_URL is configured. The data layer shows honest empty
 *  states (not mock) when this is false. */
export function dbReady(): boolean {
  return !!process.env.DATABASE_URL;
}

/** TLS policy for the DB connection.
 *  - Local Docker: no SSL.
 *  - Hosted (Supabase pooler): when DATABASE_CA_CERT (PEM) is set we VERIFY the
 *    server certificate — full protection against MITM. Get it from the Supabase
 *    dashboard → Settings → Database → SSL Configuration (download cert) and put
 *    the PEM contents in the DATABASE_CA_CERT env var.
 *  - Hosted without a CA: fall back to encrypted-but-unverified (prior behaviour).
 *    Connections still use TLS; they just don't authenticate the server identity.
 *    Set DATABASE_CA_CERT to close that gap. */
function sslConfig(local: boolean): PoolConfig["ssl"] {
  if (local) return false;
  const ca = process.env.DATABASE_CA_CERT?.trim();
  if (ca) return { ca, rejectUnauthorized: true };
  return { rejectUnauthorized: false };
}

function pool(): Pool {
  if (!_pool) {
    const cs = process.env.DATABASE_URL;
    if (!cs) throw new Error("DATABASE_URL is not set");
    const local = cs.includes("localhost") || cs.includes("127.0.0.1");
    _pool = new Pool({
      connectionString: cs,
      ssl: sslConfig(local),
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
