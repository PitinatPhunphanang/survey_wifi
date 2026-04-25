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
- รองรับการกรองตาม building, floor และ **band (2.4GHz / 5GHz)**
- แสดง KPI, room summary, traceroute timeline, latency chart และ packet loss chart
- รองรับการลบข้อมูลทั้งระดับตึกหรือชั้นผ่าน `DELETE /api/survey`

#### ✨ ฟีเจอร์ Band Filtering (ใหม่)

1. **Band Filter Tabs** (ด้านบนหน้า Dashboard)
   - รวมทั้งหมด (All)
   - 2.4 GHz
   - 5 GHz
   - ทุก KPI metrics จะเปลี่ยนตามการเลือก band

2. **Band Comparison Section**
   - แสดงเมื่อเลือก "รวมทั้งหมด" (All)
   - เลือก note ผ่าน dropdown
   - เทียบค่า RSSI, Download, Upload, Ping ของ 2.4GHz vs 5GHz ในจุด (note) เดียวกัน
   - แสดงเฉพาะคู่ที่มีทั้ง 2 band

3. **Band Badges ในตาราง**
   - สีฟ้า = 2.4GHz
   - สีม่วง = 5GHz
   - สีเขียว = 6GHz (ถ้ามี)

4. **Traceroute Band Filter**
   - Dropdown เลือก Band ร่วมกับ Room/Note
   - สามารถ filter traceroute data ตาม band

### Helper Functions (`src/lib/utils.ts`)

- **`normalizeBand(band)`** - แปลง band formats ต่างๆ เป็น standard format
  - Input: "2.4 GHz", "2.4", "2G", "5GHz", "5", "5G" เป็นต้น
  - Output: "2.4GHz" | "5GHz" | "6GHz" | "Unknown"

- **`getBandColor(band)`** - ส่งคืนสี badge สำหรับแต่ละ band
  - 2.4GHz: สีฟ้า
  - 5GHz: สีม่วง
  - 6GHz: สีเขียว

### Type Definitions (`src/types/index.ts`)

- `SurveyEntry` interface:
  - `band` field เปลี่ยนจาก `"2.4 GHz" | "5 GHz" | "6 GHz" | ""` → `string | null`
  - รองรับ band formats หลากหลาย (ยืดหยุ่นต่อการเปลี่ยนแปลงข้อมูล)

### API routes

- `GET /api/survey` ดึงข้อมูลจากตาราง `surveys` โดยเรียงตาม `survey_timestamp` ล่าสุดก่อน
  - หมายเหตุ: band filtering ทำด้านหน้า (client-side) หลังจากดึงข้อมูล
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
- ข้อมูล band จากเครื่องสำรวจจะถูกบันทึกตามที่ได้มา (เช่น "2.4 GHz", "2.4", "5GHz" เป็นต้น)
  - Dashboard จะ normalize ค่าเหล่านี้ผ่าน `normalizeBand()` function

## Dashboard Features

### KPI Metrics
- AVG RSSI
- AVG Download
- AVG Upload  
- AVG Ping
- AVG Jitter
- Poor Points
- **ทั้งหมดสามารถกรองตาม band ได้**

### Charts & Visualizations
- Quality Rating (Good/Fair/Poor)
- Band Distribution (สัดส่วน 2.4GHz/5GHz)
- RSSI by Point (เรียงจากแย่ไปดี)
- TCP Throughput (Download vs Upload)
- Server Ping
- UDP Jitter
- Packet Loss (UDP + Ping)

### Room Summary Table
- แสดงสรุปค่าเฉลี่ยต่อห้อง
- เทียบ worst points

### Point Detail Table
- แสดงแต่ละจุดทดสอบอย่างละเอียด
- **เพิ่ม Band Badge** เพื่อแสดง band ชัดเจน

### Traceroute Analysis
- Timeline view แต่ละ hop
- Latency range chart
- Packet loss chart
- Raw data table
- **รองรับการกรองตาม band**

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
