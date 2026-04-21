import { NextResponse } from 'next/server';
import pool from '@/lib/db';
import { generateId } from '@/lib/storage';

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
  } catch (error: any) {
    console.error('API Error fetching surveys:', error);
    return NextResponse.json(
      { error: 'Failed to fetch surveys', details: error.message },
      { status: 500 }
    );
  }
}
