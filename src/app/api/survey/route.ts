import { NextResponse } from 'next/server';
import pool from '@/lib/db';

const getErrorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Unknown error';

export async function GET() {
  try {
    const { rows } = await pool.query(
      'SELECT * FROM survey_results ORDER BY timestamp DESC LIMIT 100'
    );

    // Map database snake_case columns to camelCase used by our SurveyEntry type
    const formattedData = rows.map((row) => ({
      id: String(row.id),
      createdAt: new Date(row.timestamp).getTime(),
      timestamp: row.timestamp,
      building: row.building || '',
      floor: row.floor || '',
      room: row.room_point || '',
      note: row.note || '',
      ssid: row.ssid || '',
      bssid: row.bssid || '',
      band: row.band || '',
      radioType: row.radio_type || '',
      channel: row.channel || '',
      signalPercent: row.signal_percent ?? '',
      rssi: row.rssi_dbm ?? '',
      rxRate: row.rx_rate_mbps ?? '',
      txRate: row.tx_rate_mbps ?? '',
      gatewayIp: row.gateway_ip || '',
      pingGatewayMs: row.ping_gateway_ms ?? '',
      pingGatewayLoss: row.ping_gateway_loss_percent ?? '',
      pingServerMs: row.ping_server_ms ?? '',
      pingLoss: row.ping_server_loss_percent ?? '',
      tcpUpload: row.tcp_upload_mbps ?? '',
      tcpDownload: row.tcp_download_mbps ?? '',
      udpTarget: row.udp_target_bandwidth || '',
      udpActual: row.udp_actual_mbps ?? '',
      udpJitter: row.udp_jitter_ms ?? '',
      udpLoss: row.udp_packetloss_percent ?? '',
    }));

    return NextResponse.json(formattedData);
  } catch (error: unknown) {
    console.error('API Error fetching surveys:', error);
    return NextResponse.json(
      { error: 'Failed to fetch surveys', details: getErrorMessage(error) },
      { status: 500 }
    );
  }
}

export async function DELETE(request: Request) {
  try {
    const body = await request.json();
    const building = typeof body?.building === 'string' ? body.building.trim() : '';
    const floor = typeof body?.floor === 'string' ? body.floor.trim() : '';
    const scope = body?.scope === 'building' ? 'building' : body?.scope === 'floor' ? 'floor' : '';

    if (!building || !scope) {
      return NextResponse.json(
        { error: 'Building and scope are required.' },
        { status: 400 }
      );
    }

    if (scope === 'floor' && !floor) {
      return NextResponse.json(
        { error: 'Floor is required when deleting a floor.' },
        { status: 400 }
      );
    }

    const client = await pool.connect();

    try {
      await client.query('BEGIN');

      const selectionQuery =
        scope === 'building'
          ? {
              text: 'SELECT id FROM survey_results WHERE building = $1',
              values: [building],
            }
          : {
              text: 'SELECT id FROM survey_results WHERE building = $1 AND floor = $2',
              values: [building, floor],
            };

      const { rows } = await client.query(selectionQuery.text, selectionQuery.values);
      const surveyIds = rows.map((row) => row.id);

      if (surveyIds.length === 0) {
        await client.query('ROLLBACK');
        return NextResponse.json(
          { error: 'No matching records found.' },
          { status: 404 }
        );
      }

      await client.query('DELETE FROM trace_hops WHERE survey_id = ANY($1::int[])', [surveyIds]);

      const deleteResult =
        scope === 'building'
          ? await client.query('DELETE FROM survey_results WHERE building = $1', [building])
          : await client.query(
              'DELETE FROM survey_results WHERE building = $1 AND floor = $2',
              [building, floor]
            );

      await client.query('COMMIT');

      return NextResponse.json({
        success: true,
        deletedCount: deleteResult.rowCount ?? 0,
        scope,
        building,
        floor: scope === 'floor' ? floor : null,
      });
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  } catch (error: unknown) {
    console.error('API Error deleting surveys:', error);
    return NextResponse.json(
      { error: 'Failed to delete surveys', details: getErrorMessage(error) },
      { status: 500 }
    );
  }
}
