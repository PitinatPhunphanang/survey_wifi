import { NextResponse } from 'next/server';
import pool from '@/lib/db';

const getErrorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Unknown error';

export async function GET() {
  try {
    const { rows } = await pool.query(`
      SELECT t.*, s.building, s.floor, s.room_point 
      FROM trace_hops t
      JOIN survey_results s ON t.survey_id = s.id
      ORDER BY t.survey_id DESC, t.hop ASC 
      LIMIT 2000
    `);

    const formattedData = rows.map((row) => ({
      id: String(row.id),
      surveyId: String(row.survey_id),
      Building: row.building || '',
      Floor: row.floor || '',
      Room_Point: row.room_point || '',
      Hop: row.hop,
      Hostname: row.hostname || '',
      IP: row.ip || '',
      'Loss_%': row.loss_percent ?? null,
      RTT1: row.rtt1 || '*',
      RTT2: row.rtt2 || '*',
      RTT3: row.rtt3 || '*',
      Min_ms: row.min_ms ?? null,
      Max_ms: row.max_ms ?? null,
      Avg_ms: row.avg_ms ?? null,
    }));

    return NextResponse.json(formattedData);
  } catch (error: unknown) {
    console.error('API Error fetching traces:', error);
    return NextResponse.json(
      { error: 'Failed to fetch traces', details: getErrorMessage(error) },
      { status: 500 }
    );
  }
}
