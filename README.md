# Wi-Fi Survey Pro

ระบบนี้แบ่งเป็น 2 ส่วนที่ทำงานร่วมกัน:

- `src/` คือเว็บ dashboard ที่สร้างด้วย Next.js สำหรับดูผลสำรวจ Wi-Fi จากฐานข้อมูล Supabase
- `Serway_tool/iperf3.19_64/iperf3.19_64/` คือเครื่องมือเก็บข้อมูลภาคสนามบน Windows/Python สำหรับวัดสัญญาณ, ping, iPerf, traceroute และบันทึกผล

## โครงสร้างปัจจุบัน

```text
survey_wifi/
|-- src/
|   |-- app/
|   |   |-- api/
|   |   |   |-- survey/route.ts        # GET รายการ survey ทั้งหมด, DELETE ลบตาม building/floor
|   |   |   `-- trace/route.ts         # GET traceroute_hops ทั้งหมด
|   |   |-- reference/page.tsx         # หน้าอ้างอิง/คู่มือ
|   |   |-- favicon.ico
|   |   |-- globals.css
|   |   |-- layout.tsx
|   |   `-- page.tsx                   # Dashboard หลัก
|   |-- components/
|   |   |-- dashboard/
|   |   |   |-- MetricCard.tsx
|   |   |   |-- ReportSummary.tsx
|   |   |   `-- VisualCharts.tsx
|   |   `-- ui/
|   |       |-- badge.tsx
|   |       |-- button.tsx
|   |       |-- card.tsx
|   |       |-- input.tsx
|   |       `-- label.tsx
|   |-- lib/
|   |   |-- supabase/
|   |   |   |-- admin.ts               # server/admin client สำหรับ route handlers
|   |   |   |-- client.ts
|   |   |   `-- server.ts
|   |   |-- evaluation.ts
|   |   |-- export.ts
|   |   |-- storage.ts
|   |   `-- utils.ts
|   `-- types/index.ts
|-- public/
|-- Serway_tool/
|   `-- iperf3.19_64/
|       `-- iperf3.19_64/
|           |-- wifi.py                # โปรแกรมสำรวจ Wi-Fi ฝั่งภาคสนาม
|           |-- iperf3.exe
|           |-- cygwin1.dll
|           |-- cygcrypto-3.dll
|           |-- cygz.dll
|           |-- Survey_Data/           # รูป spectrum ที่บันทึกจากการสำรวจ
|           `-- *.xlsx                 # ไฟล์ผลลัพธ์แยกตาม building
|-- .env.example
|-- .env.local
|-- AGENTS.md
|-- components.json
|-- eslint.config.mjs
|-- next.config.ts
|-- package.json
|-- postcss.config.mjs
`-- tsconfig.json
```

## ภาพรวมการทำงาน

1. รัน `wifi.py` บนเครื่อง Windows ที่ต่อ Wi-Fi อยู่
2. กรอก `Building`, `Floor`, `Room / Test Point` แล้วเริ่มทดสอบ
3. โปรแกรมเก็บข้อมูล WLAN, ping gateway/server, TCP upload/download, UDP jitter/loss, traceroute และ spectrum image
4. ผลลัพธ์ถูกบันทึกทั้งลงไฟล์ Excel ใน `Serway_tool/...` และส่งขึ้น Supabase
5. เว็บ Next.js อ่านข้อมูลจาก Supabase ผ่าน `/api/survey` และ `/api/trace`
6. Dashboard แสดงผลแบบแยกตาม building, floor, room summary และ traceroute analysis

## ส่วนประกอบหลัก

### Web dashboard

- `src/app/page.tsx` เป็นหน้า dashboard หลัก
- โหลดข้อมูลจาก `/api/survey` และ `/api/trace`
- รองรับการกรองตาม building และ floor
- แสดง KPI, room summary, traceroute timeline, latency chart และ packet loss chart
- รองรับการลบข้อมูลทั้งระดับตึกหรือชั้นผ่าน `DELETE /api/survey`

### API routes

- `GET /api/survey` ดึงข้อมูลจากตาราง `surveys` โดยเรียงตาม `survey_timestamp` ล่าสุดก่อน
- `DELETE /api/survey` ลบข้อมูลตาม `building` หรือ `building + floor`
- `GET /api/trace` ดึงข้อมูลจากตาราง `traceroute_hops`

### Python survey tool

ไฟล์หลักคือ `Serway_tool/iperf3.19_64/iperf3.19_64/wifi.py`

ความสามารถหลัก:

- อ่านข้อมูล Wi-Fi ปัจจุบันด้วย `netsh wlan show interfaces`
- หา default gateway และวัด ping
- รัน `iperf3.exe` สำหรับ TCP upload/download และ UDP test
- รัน `tracert` และเก็บค่า latency/loss แบบ hop-by-hop
- สแกน Wi-Fi รอบข้างและบันทึกภาพ spectrum
- เซฟผลเป็น Excel และ insert เข้า Supabase

## Environment variables

คัดลอกจาก `.env.example` มาเป็น `.env.local`

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-public-key
SUPABASE_SECRET_KEY=your-secret-key
```

หมายเหตุ:

- ฝั่ง Next.js ใช้ค่าเหล่านี้สำหรับเชื่อม Supabase
- `wifi.py` จะพยายามไล่หา `.env.local` จากโฟลเดอร์แม่ขึ้นไป

## การรันเว็บ

ติดตั้งและรัน:

```bash
npm install
npm run dev
```

จากนั้นเปิด `http://localhost:3000`

สคริปต์ที่มีใน `package.json`:

```bash
npm run dev
npm run build
npm run start
npm run lint
```

## การรันเครื่องมือสำรวจ

ไปที่โฟลเดอร์เครื่องมือ:

```bash
cd Serway_tool/iperf3.19_64/iperf3.19_64
python wifi.py
```

สิ่งที่ต้องมีบนเครื่อง:

- Windows
- Python ที่ติดตั้ง dependency ที่ `wifi.py` ใช้งาน เช่น `customtkinter`, `matplotlib`, `pandas`, `python-dotenv`, `supabase`
- ไฟล์ `iperf3.exe` และ DLL ที่อยู่ในโฟลเดอร์เดียวกับ `wifi.py`
- เครื่องปลายทาง iPerf ที่พร้อมรับการทดสอบ

## โครงสร้างข้อมูลที่เว็บใช้งาน

### ตาราง `surveys`

ตัวอย่าง field สำคัญที่หน้าเว็บ map มาใช้งาน:

- `survey_timestamp`
- `building`
- `floor`
- `room_point`
- `note`
- `ssid`, `bssid`, `band`, `radio_type`, `channel`
- `signal_percent`, `rssi_dbm`
- `receive_rate_mbps`, `transmit_rate_mbps`
- `gateway_ip`
- `ping_gateway_ms`, `ping_gateway_loss_pct`
- `ping_server_ms`, `ping_server_loss_pct`
- `tcp_upload_mbps`, `tcp_download_mbps`
- `udp_target_bandwidth`, `udp_actual_mbps`, `udp_jitter_ms`, `udp_packetloss_pct`
- `rating`

### ตาราง `traceroute_hops`

field ที่ route และ dashboard ใช้งาน:

- `survey_id`
- `survey_timestamp`
- `building`
- `floor`
- `room_point`
- `hop`
- `ip`
- `loss_pct`
- `min_ms`
- `max_ms`
- `avg_ms`

## หมายเหตุเกี่ยวกับสถานะปัจจุบัน

- README เดิมอ้างโครงสร้างเก่าบางส่วน เช่น `api/survey/latest` ซึ่งไม่มีแล้วในโปรเจกต์ปัจจุบัน
- ชื่อไฟล์เครื่องมือภาคสนามในรีโปตอนนี้คือ `wifi.py` ตัวพิมพ์เล็ก
- โฟลเดอร์ `.next/`, `node_modules/` และไฟล์ผลลัพธ์ใน `Survey_Data/` เป็นข้อมูลที่เกิดจากการ build หรือการใช้งานจริง ไม่ใช่ source logic หลัก
