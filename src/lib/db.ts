import { Pool } from 'pg';

const pool = new Pool({
  host: '127.0.0.1',
  port: 5432,
  database: 'wifisurvey',
  user: 'wifi_admin',
  password: 'V7!mQ2#pL9@xR4$kN8zT6c',
});

export default pool;
