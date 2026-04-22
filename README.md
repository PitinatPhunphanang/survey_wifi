# Wi-Fi Survey Pro 📶

โปรเจกต์สำหรับทดสอบและเก็บข้อมูลประสิทธิภาพของเครือข่าย Wi-Fi (Site Survey) แบบครบวงจร ตั้งแต่การเก็บข้อมูลภาคสนามด้วยโปรแกรม Python ไปจนถึงการแสดงผลรายงานด้วย Next.js Dashboard แบบเรียลไทม์

---

## � โครงสร้างไฟล์โปรเจกต์ (Project Structure)

```
d:\wifi/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── layout.tsx                # Layout หลักของเว็บ
│   │   ├── page.tsx                  # หน้า Dashboard หลัก
│   │   ├── globals.css               # CSS สไตล์ทั่วไป
│   │   ├── api/                      # REST API Endpoints
│   │   │   ├── survey/
│   │   │   │   └── latest/
│   │   │   │       └── route.ts      # API ดึงข้อมูล survey ล่าสุด (GET)
│   │   │   └── trace/
│   │   │       └── route.ts          # API ดึงข้อมูล traceroute (GET)
│   │   └── reference/
│   │       └── page.tsx              # หน้าอ้างอิง/ความช่วยเหลือ
│   │
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── MetricCard.tsx        # ส่วนแสดงค่า KPI (ช่องตัวเลข)
│   │   │   ├── ReportSummary.tsx     # สรุปรายงานสุขภาพ Wi-Fi
│   │   │   └── VisualCharts.tsx      # กราฟแสดงข้อมูล (Recharts)
│   │   └── ui/
│   │       ├── badge.tsx             # แท็กสถานะสี (Good/Fair/Poor)
│   │       ├── button.tsx            # ปุ่ม UI
│   │       ├── card.tsx              # ส่วน Card
│   │       ├── input.tsx             # Input Form
│   │       └── label.tsx             # Label สำหรับ Form
│   │
│   ├── lib/
│   │   ├── evaluation.ts             # ฟังก์ชันประเมินคุณภาพ Wi-Fi (Health Score)
│   │   ├── export.ts                 # ฟังก์ชันส่งออก JSON/CSV
│   │   ├── storage.ts                # จัดการ LocalStorage
│   │   ├── utils.ts                  # Utility functions
│   │   └── supabase/
│   │       ├── admin.ts              # Supabase Admin Client (Server-side)
│   │       ├── client.ts             # Supabase Browser Client (Client-side)
│   │       └── server.ts             # Supabase Server Client (Server Components)
│   │
│   └── types/
│       └── index.ts                  # TypeScript Types & Interfaces ทั้งหมด
│
├── public/                           # Static assets (images, icons, etc.)
├── Serway_tool/
│   └── iperf3.19_64/                 # ไบนารี iPerf 3 สำหรับทดสอบ Throughput
│       └── iperf3.19_64/
│           └── Wifi.py               # 🔴 Script Python หลัก - เก็บข้อมูล Wi-Fi
│
├── .env.example                      # Template ตัวแปรสภาพแวดล้อม
├── package.json                      # Dependencies และ Scripts
├── tsconfig.json                     # TypeScript Configuration
├── next.config.ts                    # Next.js Configuration
├── eslint.config.mjs                 # ESLint Rules
├── postcss.config.mjs                # PostCSS Configuration
├── components.json                   # shadcn/ui Configuration
└── README.md                         # ไฟล์นี้

```

---

## 🔄 Data Flow: ภาพรวมการไหลของข้อมูล

```
┌──────────────────────────────────────────────────────────────┐
│ 1️⃣  FIELD TESTING (ผู้ปฏิบัติงาน)                           │
├──────────────────────────────────────────────────────────────┤
│ • รัน Wifi.py บนแล็ปท็อป                                     │
│ • สัมผัส Building/Floor/Room และกด "START"                  │
│ • ระบบทำ: Ping, iPerf, Traceroute                           │
│ • ผลลัพธ์ถูกส่งไปยัง Supabase ทันที                         │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ 2️⃣  DATABASE STORAGE (Supabase)                             │
├──────────────────────────────────────────────────────────────┤
│ Tables:                                                       │
│ • surveys: ข้อมูลหลักการทดสอบแต่ละครั้ง                     │
│ • traceroute_hops: ข้อมูล Hop แต่ละจุด                      │
│                                                               │
│ Foreign Key: traceroute_hops.survey_id → surveys.id          │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ 3️⃣  WEB DASHBOARD (Next.js + Supabase Client)               │
├──────────────────────────────────────────────────────────────┤
│ /api/survey/latest/route.ts → ดึงข้อมูล survey ล่าสุด      │
│ /api/trace/route.ts         → ดึง + Join traceroute data    │
│                                                               │
│ Components:                                                   │
│ • MetricCard: แสดงค่า RSSI, Throughput, Jitter, Loss       │
│ • VisualCharts: วาดกราฟวิเคราะห์ด้วย Recharts             │
│ • ReportSummary: สรุปสถานะ (Health Score)                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 🛠 ไฟล์สำคัญและหน้าที่ (Key Files & Their Purposes)

### 🔴 Python Testing Script
| ไฟล์ | หน้าที่ |
|------|--------|
| `Serway_tool/.../Wifi.py` | **สคริปต์หลักเก็บข้อมูล**: ทำ Ping, iPerf, Traceroute และส่งข้อมูลไปยัง Supabase |

### 🟢 Backend APIs (Next.js)
| ไฟล์ | Endpoint | หน้าที่ |
|------|----------|--------|
| `src/app/api/survey/latest/route.ts` | `GET /api/survey/latest` | ดึงการทดสอบ Wi-Fi ล่าสุด 1 ครั้ง |
| `src/app/api/trace/route.ts` | `GET /api/trace` | ดึงข้อมูล Traceroute ทั้งหมด + ข้อมูล Location (Building/Floor) ผ่าน JOIN |

### 🔵 Supabase Configuration
| ไฟล์ | หน้าที่ |
|------|--------|
| `src/lib/supabase/admin.ts` | สร้าง Supabase Client สำหรับเซิร์ฟเวอร์ (มีสิทธิ์เต็ม) |
| `src/lib/supabase/client.ts` | สร้าง Supabase Client สำหรับบราวเซอร์ (ฝั่งหน้า) |
| `src/lib/supabase/server.ts` | สร้าง Supabase Server Client สำหรับ Server Components |

### 📊 Frontend Components
| ไฟล์ | หน้าที่ |
|------|--------|
| `src/components/dashboard/MetricCard.tsx` | แสดงกล่องค่า KPI (RSSI, Throughput, Jitter) |
| `src/components/dashboard/VisualCharts.tsx` | วาดกราฟ Line/Bar Chart ด้วย Recharts |
| `src/components/dashboard/ReportSummary.tsx` | สรุปสภาพสุขภาพ Wi-Fi ทั้งหมด |

### 🔧 Utility Libraries
| ไฟล์ | หน้าที่ |
|------|--------|
| `src/lib/evaluation.ts` | ประเมินคุณภาพ Wi-Fi (Health Score) กำหนด Good/Fair/Poor |
| `src/lib/export.ts` | ส่งออกข้อมูล JSON หรือ CSV |
| `src/lib/storage.ts` | เก็บ/ดึงข้อมูลจาก Browser LocalStorage |
| `src/lib/utils.ts` | ฟังก์ชั่นช่วยเหลือต่างๆ |
| `src/types/index.ts` | TypeScript Types: `SurveyEntry`, `TraceHop`, `HealthReport` เป็นต้น |

### 📝 UI Components
| ไฟล์ | หน้าที่ |
|------|--------|
| `src/components/ui/badge.tsx` | แท็กสีแสดงสถานะ (Good ❌ / Fair ⚠ / Poor 🔴) |
| `src/components/ui/button.tsx` | ปุ่มคลิก UI |
| `src/components/ui/card.tsx` | ส่วน Card บรรจุข้อมูล |
| `src/components/ui/input.tsx` | ช่องกรอก Input |
| `src/components/ui/label.tsx` | ป้ายชื่อ Label |

---

## 🛠 การอัปเดตระบบล่าสุด (Changelog)

ระบบได้รับการยกระดับจากการใช้ไฟล์ Excel เพียงอย่างเดียว มาเป็นระบบฐานข้อมูลเต็มรูปแบบ เพื่อให้ข้อมูลเชื่อมโยงกันแบบอัตโนมัติ (Automated Data Pipeline):

1. **เปลี่ยนจาก PostgreSQL เป็น Supabase:** 
   - ลบ `docker-compose.yml` และ `postgres/` directory
   - ใช้ Supabase (Postgres-as-a-Service) แทนการรัน Docker
   - เก็บ credentials ใน `.env.local`

2. **อัปเดท API Routes:**
   - `/api/survey/latest/` → ดึงข้อมูล survey ล่าสุด
   - `/api/trace/` → ดึง traceroute_hops + ข้อมูล Location

3. **ยกเครื่องหน้า Dashboard (Next.js):**
   - ถอดระบบอัปโหลดไฟล์ Excel แบบ Manual ออก
   - เพิ่มระบบ API ให้เว็บดึงข้อมูลจาก Supabase สดๆ
   - เพิ่มเมนูด้านซ้าย (Sidebar) สำหรับเลือกตึก (Building) และชั้น (Floor)
   - แสดงผลกราฟวิเคราะห์แต่ละชั้น (Floor Report) และ Traceroute Analysis
   - เปลี่ยนเมนูและส่วนติดต่อผู้ใช้งานเป็น **ภาษาไทย**

---

## 💾 Supabase Database Schema

### Table: `surveys`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | รหัสการทดสอบ (Primary Key) |
| `survey_timestamp` | Timestamp | เวลาการทดสอบ |
| `building` | Text | ชื่อตึก |
| `floor` | Text | ชั้น |
| `room_point` | Text | ห้อง/จุดทดสอบ |
| `ssid` | Text | ชื่อ Wi-Fi |
| `rssi` | Integer | ค่า RSSI (dBm) |
| `signal_percent` | Integer | ความแรงสัญญาณ (%) |
| `tcp_download_mbps` | Float | ความเร็ว Download (Mbps) |
| `tcp_upload_mbps` | Float | ความเร็ว Upload (Mbps) |
| `udp_jitter_ms` | Float | Jitter (ms) |
| `udp_loss_percent` | Float | Packet Loss (%) |
| `ping_server_ms` | Float | Ping ไปเซิร์ฟเวอร์ (ms) |
| `ping_loss_percent` | Float | Ping Loss (%) |

### Table: `traceroute_hops`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary Key |
| `survey_id` | UUID | Foreign Key → surveys.id |
| `hop` | Integer | เลขที่ Hop |
| `hostname` | Text | ชื่อเซิร์ฟเวอร์ |
| `ip` | Text | IP Address |
| `rtt1_ms`, `rtt2_ms`, `rtt3_ms` | Float | Round Trip Time |
| `loss_percent` | Float | Loss % |

---

## 📊 หลักการดึงข้อมูลไปแสดงผล (Data Retrieval & Visualization)

1. **ฝั่ง Backend (API Routes):**
   - `/api/survey/latest/route.ts` → ส่งคำสั่ง `SELECT * FROM surveys ORDER BY survey_timestamp DESC LIMIT 1`
   - `/api/trace/route.ts` → ส่ง JOIN Query ระหว่าง `traceroute_hops` กับ `surveys` เพื่อดึง Location ด้วย
   - ส่งออกข้อมูลเป็น JSON

2. **ฝั่ง Frontend (Dashboard UI):**
   - เมื่อเปิดเว็บ ระบบเรียก API เพื่อขอข้อมูล JSON
   - ดึงรายชื่อตึก/ชั้นทั้งหมด เพื่อสร้างเมนูด้านซ้าย
   - เมื่อผู้ใช้คลิกเลือกชั้น → กรองข้อมูล และแสดงกราฟวิเคราะห์
   - ใช้ Recharts วาดกราฟ KPI, RSSI, Throughput, Jitter, Packet Loss

---

## 🚀 วิธีการรันโปรเจกต์ (How to run)

### 1️⃣ ตั้งค่า Environment Variables
สร้างไฟล์ `.env.local` ในโฟลเดอร์ root:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-public-anon-key
SUPABASE_SECRET_KEY=your-secret-service-role-key
```

### 2️⃣ รัน Web Dashboard
```bash
npm install          # ติดตั้ง dependencies (ทำเฉพาะครั้งแรก)
npm run dev          # รัน dev server
```
เปิดเว็บได้ที่ `http://localhost:3000`

### 3️⃣ รันตัวเทส Wi-Fi (ฝั่งผู้ปฏิบัติงาน)
```bash
cd Serway_tool/iperf3.19_64/iperf3.19_64/
python Wifi.py
```

---

## 🔍 วิธีการเพิ่มเติม/แก้ไข (Editing Guide)

### 📌 หากต้องการเพิ่ม Field ใหม่ในการทดสอบ:
1. **อัปเดท Supabase Schema** → เพิ่ม column ในตาราง `surveys`
2. **อัปเดท `Wifi.py`** → เก็บข้อมูล field ใหม่
3. **อัปเดท `src/types/index.ts`** → เพิ่ม Type definition
4. **อัปเดท Component** → แสดงข้อมูล field ใหม่บน Dashboard

### 📌 หากต้องการเปลี่ยน API Endpoint:
1. แก้ไขไฟล์ใน `src/app/api/*/route.ts`
2. ส่วนหน้าเว็บจะอัปเดทอัตโนมัติหากใช้ `fetch()` ที่เหมาะสม

### 📌 หากต้องการเพิ่มกราฟใหม่:
1. แก้ไข `src/components/dashboard/VisualCharts.tsx`
2. ใช้ Recharts library เพื่อสร้างกราฟ

---

## 📦 Dependencies หลัก

- **Next.js 16.2.4** - Web Framework
- **React 19.2.4** - UI Library
- **@supabase/supabase-js** - Supabase Client
- **recharts** - Chart Library
- **shadcn/ui** - UI Components
- **tailwindcss** - CSS Framework
- **typescript** - Type Safety

---
