# สรุปโครงสร้างโปรแกรม Wi-Fi Survey

โปรแกรมเดิมอยู่รวมกันในไฟล์ `survey_wifi.py` ไฟล์เดียวขนาดใหญ่ประมาณ 1600+ บรรทัด ตอนนี้ถูกแยกออกเป็นหลายไฟล์ตามหน้าที่ เพื่อให้อ่านง่าย แก้ง่าย และดูเป็นโครงสร้างแบบโปรมากขึ้น

## จุดเริ่มต้นของโปรแกรม

`Serway_tool/iperf3.19_64/iperf3.19_64/survey_wifi.py`

ไฟล์นี้เป็น entry point หลักของโปรแกรม มีหน้าที่เริ่มแอปเท่านั้น โดย import `WifiSurveyApp` จาก `ui/app.py` แล้วสั่ง `mainloop()`

## ไฟล์ตั้งค่า

`Serway_tool/iperf3.19_64/iperf3.19_64/config.py`

เก็บค่าคงที่ของระบบ เช่น

- IP server ของ iPerf
- port และระยะเวลาในการทดสอบ
- ค่า UDP bandwidth
- ชื่อแอป
- path สำหรับบันทึกไฟล์ survey
- ค่า Supabase จาก `.env.local`

การแยกไฟล์นี้ช่วยให้แก้ค่าตั้งค่าหลักได้จากที่เดียว

## ส่วนหน้าจอโปรแกรม

`Serway_tool/iperf3.19_64/iperf3.19_64/ui/app.py`

เป็นไฟล์หลักของ GUI โดยใช้ `customtkinter` สร้างหน้าจอ เช่น

- ช่องกรอก Building, Floor, Room, Note
- ปุ่ม START TEST & SAVE
- ปุ่ม CLEAR
- ปุ่ม IMPORT WINMTR
- กล่องแสดงผลลัพธ์
- กราฟ Spectrum Preview

ไฟล์นี้ยังควบคุม workflow หลักของการทดสอบ เช่น กดเริ่มเทสต์แล้วไปเรียก module อื่นๆ เพื่อเก็บ Wi-Fi, ping, iPerf, บันทึก Excel และส่ง Supabase

## ส่วน Network

โฟลเดอร์ `Serway_tool/iperf3.19_64/iperf3.19_64/network/`

### `wlan.py`

ใช้ดึงข้อมูล Wi-Fi จากเครื่อง เช่น

- SSID
- BSSID
- Band
- Channel
- Signal %
- RSSI dBm
- Receive / Transmit rate
- Noise floor และ SNR
- AP vendor จาก MAC address

### `ping.py`

ใช้ตรวจ network latency เช่น

- หา default gateway
- ping gateway
- ping iPerf server
- คำนวณค่า avg ping และ packet loss

### `iperf.py`

ใช้รัน `iperf3.exe` และแปลงผลลัพธ์ JSON เช่น

- TCP upload
- TCP download
- UDP bandwidth
- jitter
- packet loss

### `spectrum.py`

ใช้สแกน Wi-Fi รอบๆ และวาดกราฟ spectrum เช่น

- scan nearby Wi-Fi
- วิเคราะห์ co-channel / adjacent channel
- วาดกราฟด้วย matplotlib
- save กราฟเป็นรูป PNG

## ไฟล์โปรแกรมภายนอก

โฟลเดอร์ `Serway_tool/iperf3.19_64/iperf3.19_64/bin/iperf3/`

ใช้เก็บไฟล์ของ iPerf3 และ runtime library ที่จำเป็น เช่น

- `iperf3.exe`
- `cygwin1.dll`
- `cygcrypto-3.dll`
- `cygz.dll`

ไฟล์ `cyg*.dll` เป็น library ที่ `iperf3.exe` ต้องใช้ตอนรันบน Windows จึงควรเก็บไว้ในโฟลเดอร์เดียวกับ `iperf3.exe` ไม่ควรลบออก และไม่ควรแยกไปคนละที่ถ้าไม่ได้ตั้งค่า path เพิ่ม

## ส่วน Storage

โฟลเดอร์ `Serway_tool/iperf3.19_64/iperf3.19_64/storage/`

### `excel.py`

ใช้จัดการไฟล์ Excel เช่น

- สร้าง workbook ใหม่
- append ข้อมูลลง sheet
- แก้ปัญหาไฟล์ Excel เปิดค้างอยู่ ด้วยการสร้าง autosave file

### `supabase_db.py`

ใช้จัดการฐานข้อมูล Supabase เช่น

- บันทึกข้อมูล survey ลงตาราง `surveys`
- import WinMTR TXT
- บันทึก hop data ลง `traceroute_hops`
- ป้องกันข้อมูลซ้ำบางกรณี

## ส่วน Utility

โฟลเดอร์ `Serway_tool/iperf3.19_64/iperf3.19_64/utils/`

### `helpers.py`

รวม helper function ที่ใช้ร่วมกัน เช่น

- แปลงค่า string เป็น float
- แปลง percentage
- ทำชื่อไฟล์ให้ปลอดภัย
- run command ผ่าน subprocess
- run PowerShell แล้ว parse JSON
- sanitize ค่า NaN ก่อนส่ง database

## ไฟล์ Backup และ Generator

### `survey_wifi_backup.py`

เป็นไฟล์ backup ของโค้ดเดิมก่อนแยกไฟล์ ควรเก็บไว้ก่อนจนกว่ามั่นใจว่า version ใหม่ใช้งานได้ครบ

### `generate_ui.py`

เป็น script ที่ใช้ generate `ui/app.py` และ `survey_wifi.py` จาก backup เดิม ไม่ใช่ไฟล์หลักสำหรับรันโปรแกรมปกติ

ถ้าจะส่งงานจริง อาจไม่จำเป็นต้องส่ง `generate_ui.py` ก็ได้ เว้นแต่ต้องการอธิบายว่ามีเครื่องมือช่วย migrate จากไฟล์เก่า

## ภาพรวมการทำงาน

ลำดับการทำงานหลักคือ:

1. เปิด `survey_wifi.py`
2. โปรแกรมสร้างหน้าจอจาก `ui/app.py`
3. ผู้ใช้กรอกข้อมูลสถานที่และกด START TEST & SAVE
4. โปรแกรมดึงข้อมูล Wi-Fi จาก `network/wlan.py`
5. โปรแกรม ping gateway/server จาก `network/ping.py`
6. โปรแกรมรัน iPerf จาก `network/iperf.py`
7. โปรแกรมสแกนและวาด spectrum จาก `network/spectrum.py`
8. โปรแกรมบันทึก Excel ผ่าน `storage/excel.py`
9. โปรแกรมส่งข้อมูลขึ้น Supabase ผ่าน `storage/supabase_db.py`

## สรุป

โครงสร้างใหม่นี้ดีกว่าเดิม เพราะแยกตาม responsibility ชัดเจน:

- `ui/` ดูแลหน้าจอ
- `network/` ดูแลงานเกี่ยวกับ Wi-Fi, ping, iPerf และ spectrum
- `storage/` ดูแล Excel และ database
- `utils/` เก็บ helper ที่ใช้ซ้ำ
- `bin/iperf3/` เก็บ `iperf3.exe` และ DLL ที่จำเป็น
- `config.py` เก็บค่าตั้งค่ากลาง
- `survey_wifi.py` เป็นไฟล์เริ่มต้นที่สั้นและสะอาด

โดยรวมถือว่าแยกไฟล์ได้เหมาะสมและดูเป็นโปรมากขึ้น เหลือเพียงทดสอบการใช้งานจริงกับเครื่อง, Wi-Fi, iPerf server และ Supabase เพื่อยืนยันว่า workflow ทั้งหมดทำงานครบ
