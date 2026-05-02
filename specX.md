# Project Specification: IPNEX Radar (V1.2)
**Status:** In Development / Feature Complete (Phase 1-5)

## 1. Project Overview
IPNEX Radar คือระบบ IP Monitoring & Anti-Spoofing ระดับองค์กรที่ใช้ฐานข้อมูล SQLite เป็น Master Registry เพื่อติดตามและตรวจสอบความถูกต้องของอุปกรณ์ในเครือข่าย ป้องกันการสวมรอย (Spoofing) และเก็บบันทึกประวัติการเปลี่ยนแปลง (Audit Trail) ทั้งหมด

---

## 2. Core Features (Implemented)

### 2.1 Automated Network Discovery (T-003, T-004)
- **ARP Scanning:** ใช้ `scapy` ในการสแกนหาอุปกรณ์ผ่านโปรโตคอล ARP (Layer 2)
- **Scheduler:** สแกนอัตโนมัติทุกๆ 5 นาที (Background Process)
- **Identity Binding:** ผูกข้อมูล Hostname, IP, และ MAC Address เข้าด้วยกัน

### 2.2 Change Detection Engine (Phase 3)
- **New Device Detection:** บันทึกอุปกรณ์ใหม่ลง Master DB โดยอัตโนมัติ
- **IP/Hostname Migration:** ติดตามและบันทึกเมื่ออุปกรณ์เดิมเปลี่ยน IP หรือชื่อเครื่อง
- **Offline Detection (T-009):** ปรับสถานะเป็น `offline` อัตโนมัติหากเครื่องหายไปจากเน็ตเวิร์ค
- **Anti-Spoofing (T-010):** ตรวจพบเมื่อมีการใช้ IP เดิมแต่ MAC เปลี่ยนไป และส่งการแจ้งเตือนทันที

### 2.3 Manual Management
- **Manual Scan:** สั่งสแกนวงเน็ตเวิร์ค (Subnet) เฉพาะกิจผ่านหน้า UI
- **Manual Register:** ลงทะเบียนอุปกรณ์ใหม่เข้า Master Registry โดยตรงผ่านฟอร์ม
- **Manual Update:** แก้ไขข้อมูล Hostname/IP ของอุปกรณ์ในฐานข้อมูลได้โดยตรง

### 2.4 Monitoring & Review (Phase 5)
- **Glassmorphism Dashboard:** หน้าแรกแสดงสถานะอุปกรณ์แบบ Real-time
- **Audit Trail (History Page):** แสดงประวัติการเปลี่ยนแปลงย้อนหลัง 100 รายการล่าสุด (เก่า ➝ ใหม่)
- **Recent IP Highlight (T-015):** ติดป้ายไฟแจ้งเตือนเครื่องที่เพิ่งเปลี่ยน IP ในรอบ 7 วัน
- **Search & Filter:** ค้นหาตาม Hostname/IP/MAC และกรองตามสถานะ Online/Offline
- **CSV Export:** ส่งออกรายการอุปกรณ์ที่แสดงอยู่เป็นไฟล์ CSV

---

## 3. Technical Architecture

### 3.1 Backend (FastAPI)
- **Database:** SQLite (`ipnex.db`)
- **Library:** Scapy, APScheduler, Pydantic
- **Alert System:** Line Notify API
- **Lookup API:** รองรับโปรแกรมภายนอกดึงข้อมูลผ่าน `/api/lookup/{id}`

### 3.2 Frontend (Next.js)
- **Styling:** Tailwind CSS + Lucide Icons
- **Features:** Auto-polling ทุก 10 วินาที, Client-side Filtering

---

## 4. Database Schema

### Table: `devices` (Master)
| Field | Type | Description |
|---|---|---|
| `device_id` | INTEGER | Primary Key |
| `hostname` | TEXT | ชื่อเครื่องล่าสุด |
| `ip_address` | TEXT | IP ล่าสุด |
| `mac_address` | TEXT | MAC Address (Unique Key) |
| `status` | TEXT | online / offline |
| `is_reserved` | INTEGER | 0 = Regular, 1 = Server/Locked |
| `first_seen` | TEXT | วันที่พบครั้งแรก |
| `last_seen` | TEXT | วันที่พบล่าสุด |

### Table: `device_history` (Audit Log)
| Field | Type | Description |
|---|---|---|
| `log_id` | INTEGER | Primary Key |
| `device_id` | INTEGER | FK to devices |
| `change_type` | TEXT | INSERT / UPDATE_IP / UPDATE_HOSTNAME / SUSPICIOUS / STATUS_CHANGE |
| `field_changed` | TEXT | ฟิลด์ที่มีการเปลี่ยนแปลง |
| `old_value` | TEXT | ค่าเดิมก่อนเปลี่ยน |
| `new_value` | TEXT | ค่าใหม่หลังเปลี่ยน |
| `changed_at` | TEXT | วันเวลาที่เกิดการเปลี่ยนแปลง |

---

## 5. Upcoming / Roadmap
- [ ] **T-017** Implement logic to block manual DB updates if Baseline is Locked
- [ ] **T-018** Add Login/Auth system for Dashboard access
- [ ] **T-019** Configure Docker Volume Persistence for SQLite DB
- [ ] **T-020** Automated Log Cleanup (Delete logs > 90 days)
