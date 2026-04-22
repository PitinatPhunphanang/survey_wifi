import { NextResponse } from 'next/server';
import { createAdminClient } from '@/lib/supabase/admin';

const getErrorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Unknown error';

export async function GET() {
  try {
    const supabase = createAdminClient();
    
    const { data: rows, error } = await supabase
      .from('traceroute_hops')
      .select(`
        *,
        surveys(building, floor, room_point)
      `)
      .order('survey_id', { ascending: false })
      .order('hop', { ascending: true })
      .limit(2000);

    if (error) throw error;

    const formattedData = rows?.map((row) => {
      const surveyData = Array.isArray(row.surveys) ? row.surveys[0] : row.surveys;
      return {
        id: String(row.id),
        surveyId: String(row.survey_id),
        Building: surveyData?.building || '',
        Floor: surveyData?.floor || '',
        Room_Point: surveyData?.room_point || '',
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
      };
    }) || [];

    return NextResponse.json(formattedData);
  } catch (error: unknown) {
    console.error('API Error fetching traces:', error);
    return NextResponse.json(
      { error: 'Failed to fetch traces', details: getErrorMessage(error) },
      { status: 500 }
    );
  }
}
