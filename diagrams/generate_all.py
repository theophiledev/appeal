"""
Generate all system diagrams for the ULK Marks Appeal System.
Outputs: .dot (graphviz), .puml (plantuml), and a Mermaid markdown file.
"""
import os

OUT = os.path.dirname(os.path.abspath(__file__))

# ─── helpers ────────────────────────────────────────────────────────────────

def write(path, content):
    with open(os.path.join(OUT, path), 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  -> {path}")


# ════════════════════════════════════════════════════════════════════════════
# 1. DFD LEVEL 0 — CONTEXT DIAGRAM  (.dot)
# ════════════════════════════════════════════════════════════════════════════

DFD_L0_DOT = """digraph "ContextDiagram" {
  rankdir=LR;
  bgcolor="transparent";
  fontname="Arial";
  node [fontname="Arial"];
  edge [fontname="Arial"];

  // External entities
  node [shape=box, style="rounded,filled", fillcolor="#E3F2FD", color="#1565C0"];
  Student [label="Student\n(Mobile Phone / USSD)"];
  Admin  [label="Administrator\n(Web Portal)"];
  HOD    [label="Head of Department\n(Web Portal)"];

  // Central system
  node [shape=circle, style=filled, fillcolor="#FFF3E0", color="#E65100", width=1.8, height=1.8];
  System [label="USSD-Based\nMarks Appeal\nSystem"];

  // External gateway
  node [shape=box3d, style=filled, fillcolor="#F3E5F5", color="#7B1FA2"];
  AT [label="Africa's Talking\nUSSD Gateway"];

  // Data flows — Student
  edge [color="#1565C0", penwidth=1.2];
  Student -> AT [label="  USSD Input\n  (Student ID, PIN,\n  menu selection,\n  appeal reason)"];
  AT -> Student [label="  USSD Response\n  (menus, marks,\n  status, prompts)"];

  AT -> System [label="  HTTP POST\n  (sessionId,\n  phoneNumber,\n  text)"];
  System -> AT [label="  HTTP Response\n  (CON / END)"];

  // Data flows — Admin
  edge [color="#2E7D32", penwidth=1.2];
  Admin -> System [label="  Login Credentials,\n  Status Updates"];
  System -> Admin [label="  Dashboard View,\n  Appeals List,\n  Audit Logs"];

  // Data flows — HOD
  edge [color="#E65100", penwidth=1.2];
  HOD -> System [label="  Login Credentials,\n  Recommendations"];
  System -> HOD [label="  Departmental\n  Appeals List"];
}"
"""

# ════════════════════════════════════════════════════════════════════════════
# 2. DFD LEVEL 1  (.dot)
# ════════════════════════════════════════════════════════════════════════════

DFD_L1_DOT = """digraph "DFDLevel1" {
  rankdir=TB;
  bgcolor="transparent";
  fontname="Arial";
  node [fontname="Arial"];
  edge [fontname="Arial"];

  // External entities
  node [shape=box, style="rounded,filled", fillcolor="#E3F2FD", color="#1565C0"];
  Student [label="Student"];
  Admin [label="Administrator"];
  HOD [label="HOD"];

  // Processes
  node [shape=circle, style=filled, fillcolor="#FFF3E0", color="#E65100", width=1.5];
  P1 [label="1.0\nAuthenticate\nStudent"];
  P2 [label="2.0\nView\nMarks"];
  P3 [label="3.0\nSubmit\nAppeal"];
  P4 [label="4.0\nCheck\nAppeal Status"];
  P5 [label="5.0\nManage\nAppeals"];

  // Data stores
  node [shape=cylinder, style=filled, fillcolor="#E8F5E9", color="#2E7D32", width=1.2];
  DS1 [label="pin_credentials"];
  DS2 [label="marks"];
  DS3 [label="appeals"];
  DS4 [label="appeal_status"];
  DS5 [label="access_audit"];
  DS6 [label="admins"];

  // Central hub for routing
  node [shape=point, width=0, height=0];
  hub;

  // Student flows
  edge [color="#1565C0"];
  Student -> hub;
  hub -> P1;
  P1 -> DS1 [label=" read/write"];
  P1 -> DS5 [label=" write"];

  P1 -> P2 [label=" auth OK"];
  P2 -> DS2 [label=" read"];
  P2 -> hub; hub -> Student;

  P1 -> P3 [label=" auth OK"];
  P3 -> DS2 [label=" read"];
  P3 -> DS3 [label=" write"];
  P3 -> DS5 [label=" write"];
  P3 -> hub; hub -> Student;

  P1 -> P4 [label=" auth OK"];
  P4 -> DS3 [label=" read"];
  P4 -> DS4 [label=" read"];
  P4 -> hub; hub -> Student;

  // Admin flows
  edge [color="#2E7D32"];
  Admin -> P5;
  P5 -> DS3 [label=" read/write"];
  P5 -> DS4 [label=" read"];
  P5 -> DS6 [label=" read"];
  P5 -> DS5 [label=" read"];
  P5 -> Admin;

  // HOD flows
  edge [color="#E65100"];
  HOD -> P5;
  P5 -> HOD;
}"
"""

# ════════════════════════════════════════════════════════════════════════════
# 3. DFD LEVEL 2 — AUTHENTICATE STUDENT  (.dot)
# ════════════════════════════════════════════════════════════════════════════

DFD_L2_DOT = """digraph "DFDLevel2_Authenticate" {
  rankdir=TB;
  bgcolor="transparent";
  fontname="Arial";
  node [fontname="Arial"];
  edge [fontname="Arial"];

  // External
  node [shape=box, style="rounded,filled", fillcolor="#E3F2FD", color="#1565C0"];
  Student [label="Student"];

  // Sub-processes
  node [shape=circle, style=filled, fillcolor="#FFF3E0", color="#E65100", width=1.4];
  SP1 [label="1.1\nReceive\nStudent ID"];
  SP2 [label="1.2\nReceive\nPIN"];
  SP3 [label="1.3\nHash\nPIN"];
  SP4 [label="1.4\nCompare\nHash vs DB"];
  SP5 [label="1.5\nEnforce\nLockout"];
  SP6 [label="1.6\nLog\nEvent"];

  // Data stores
  node [shape=cylinder, style=filled, fillcolor="#E8F5E9", color="#2E7D32"];
  DS_PIN [label="pin_credentials"];
  DS_AUDIT [label="access_audit"];

  // Flows
  edge [color="#1565C0"];
  Student -> SP1 [label=" student_id"];
  SP1 -> SP2 [label=" step 1 done"];
  Student -> SP2 [label=" PIN"];
  SP2 -> SP3 [label=" PIN plaintext"];
  SP3 -> SP4 [label=" SHA-256 hash"];
  SP4 -> DS_PIN [label=" fetch record"];
  DS_PIN -> SP4 [label=" stored hash"];

  SP4 -> SP5 [label=" match result"];
  SP5 -> DS_PIN [label=" update attempts"];
  SP5 -> SP6 [label=" auth outcome"];
  SP6 -> DS_AUDIT [label=" write log"];
  SP6 -> Student [label=" result prompt"];
}"
"""

# ════════════════════════════════════════════════════════════════════════════
# 4. USE CASE DIAGRAM  (.puml — PlantUML)
# ════════════════════════════════════════════════════════════════════════════

USE_CASE_PUML = """@startuml
left to right direction
skinparam packageStyle rectangle
actor Student
actor Administrator
actor "Head of\nDepartment" as HOD
rectangle "USSD-Based Marks Appeal System" {
  :Student: --> (UC1 Register PIN)
  :Student: --> (UC2 Authenticate via PIN)
  :Student: --> (UC3 Reset PIN via OTP)
  :Student: --> (UC4 View Marks)
  :Student: --> (UC5 Submit Marks Appeal)
  :Student: --> (UC6 Check Appeal Status)

  :Administrator: --> (UC7 Login)
  :Administrator: --> (UC8 View All Appeals)
  :Administrator: --> (UC9 Update Appeal Status)
  :Administrator: --> (UC10 View Audit Logs)
  :Administrator: --> (UC11 Logout)

  :HOD: --> (UC12 Login)
  :HOD: --> (UC13 View Departmental Appeals)
  :HOD: --> (UC14 Submit Recommendation)

  (UC4) .> (UC2) : <<include>>
  (UC5) .> (UC2) : <<include>>
  (UC6) .> (UC2) : <<include>>
  (UC3) .> (UC2) : <<extend>>
}
@enduml
"""

# ════════════════════════════════════════════════════════════════════════════
# 5. SEQUENCE DIAGRAM — SUBMIT APPEAL  (.puml)
# ════════════════════════════════════════════════════════════════════════════

SEQ_APPEAL_PUML = """@startuml
actor Student
participant "Mobile Phone" as Phone
participant "Africa's Talking\nUSSD Gateway" as AT
participant "Flask /ussd\nEndpoint" as Flask
database "MySQL\nDatabase" as DB

Student -> Phone: Dial *123#
Phone -> AT: USSD request
AT -> Flask: POST /ussd (text="")
Flask --> AT: CON Welcome menu
AT --> Phone: Display menu
Phone --> Student: "1. View marks\n2. Appeal..."

Student -> Phone: Select "2"
Phone -> AT: text="2"
AT -> Flask: POST /ussd (text="2")
Flask --> AT: CON Enter Student ID
AT --> Phone: Display prompt
Phone --> Student: "Enter Student ID:"

Student -> Phone: Enter Student ID
Phone -> AT: text="2*STU001"
AT -> Flask: POST /ussd (text="2*STU001")
Flask --> AT: CON Enter your PIN
AT --> Phone: Display prompt
Phone --> Student: "Enter your PIN:"

Student -> Phone: Enter PIN
Phone -> AT: text="2*STU001*1234"
AT -> Flask: POST /ussd (text="2*STU001*1234")
Flask -> DB: Query pin_credentials
DB --> Flask: Record found
Flask -> DB: Update failed_attempts=0
Flask -> DB: Query marks for student
DB --> Flask: Module list
Flask --> AT: CON Select module
AT --> Phone: Module list
Phone --> Student: "1. DBMS (A)\n2. SE (B+)..."

Student -> Phone: Select "1"
Phone -> AT: text="2*STU001*1234*1"
AT -> Flask: POST /ussd (text="2*STU001*1234*1")
Flask --> AT: CON Enter reason
AT --> Phone: Display prompt

Student -> Phone: Type reason
Phone -> AT: text="2*STU001*1234*1*Marking error"
AT -> Flask: POST /ussd (text="2*STU001*1234*1*Marking error")
Flask -> DB: INSERT INTO appeals
Flask -> DB: INSERT INTO access_audit
Flask --> AT: END Appeal submitted
AT --> Phone: Display confirmation
Phone --> Student: "Appeal submitted\nWe will review it."
@enduml
"""

# ════════════════════════════════════════════════════════════════════════════
# 6. SEQUENCE DIAGRAM — ADMIN UPDATE STATUS  (.puml)
# ════════════════════════════════════════════════════════════════════════════

SEQ_ADMIN_PUML = """@startuml
actor Admin
participant "Web Browser" as Browser
participant "Flask Web\nServer" as Flask
database "MySQL\nDatabase" as DB

Admin -> Browser: Navigate to /admin/login
Browser -> Flask: GET /admin/login
Flask --> Browser: Login page
Browser --> Admin: Display login form

Admin -> Browser: Enter credentials
Browser -> Flask: POST /admin/login
Flask -> DB: Query admins table
DB --> Flask: Admin record
Flask ->> Browser: Set session cookie
Flask --> Browser: Redirect to /admin/dashboard
Browser --> Admin: Dashboard loaded

Admin -> Browser: Click "Update Status"
Browser -> Flask: POST /admin/manage_appeal/5
Flask -> DB: UPDATE appeals SET status_id=2
DB --> Flask: Row updated
Flask --> Browser: Redirect with flash
Browser --> Admin: "Appeal status updated"
@enduml
"""

# ════════════════════════════════════════════════════════════════════════════
# 7. ERD  (.puml)
# ════════════════════════════════════════════════════════════════════════════

ERD_PUML = """@startuml
!define table(x) class x << (T,#FFE0E0) >>
!define primary_key(x) <u>x</u>
!define foreign_key(x) <i><color:blue>x</color></i>

hide circle
skinparam linetype ortho

table(students) {
  + <u>student_id</u> VARCHAR(20)
  + full_name VARCHAR(100)
  + phone_number VARCHAR(15)
  + department VARCHAR(100)
  + email VARCHAR(100)
}

table(admins) {
  + <u>id</u> INT
  + username VARCHAR(50)
  + password VARCHAR(255)
}

table(marks) {
  + <u>id</u> INT
  + foreign_key(student_id) VARCHAR(20)
  + module_name VARCHAR(100)
  + mark INT
  + academic_year VARCHAR(20)
  + semester VARCHAR(20)
}

table(appeal_status) {
  + <u>id</u> INT
  + status_name VARCHAR(50)
}

table(appeals) {
  + <u>id</u> INT
  + foreign_key(student_id) VARCHAR(20)
  + module_name VARCHAR(100)
  + reason TEXT
  + foreign_key(status_id) INT
  + submitted_at TIMESTAMP
  + resolved_at TIMESTAMP
  + hod_recommendation TEXT
}

table(pin_credentials) {
  + <u>id</u> INT
  + foreign_key(student_id) VARCHAR(20)
  + pin_hash VARCHAR(64)
  + failed_attempts INT
  + is_locked TINYINT
  + otp_code VARCHAR(10)
  + otp_expiry DATETIME
}

table(access_audit) {
  + <u>id</u> INT
  + foreign_key(student_id) VARCHAR(20)
  + phone_number VARCHAR(15)
  + action VARCHAR(100)
  + success TINYINT
  + session_id VARCHAR(100)
  + timestamp TIMESTAMP
}

students ||--o{ marks : "has"
students ||--o{ appeals : "submits"
students ||--|| pin_credentials : "has"
students ||--o{ access_audit : "generates"
appeal_status ||--o{ appeals : "classifies"
@enduml
"""

# ════════════════════════════════════════════════════════════════════════════
# 8. MERMAID MARKDOWN — All diagrams in one file
# ════════════════════════════════════════════════════════════════════════════

MERMAID_MD = """# ULK Marks Appeal System — System Diagrams

> Generated for Chapter Four: System Analysis, Design and Implementation

---

## 1. Context Diagram (DFD Level 0)

```mermaid
graph TD
    subgraph "External Entities"
        S[Student]
        A[Administrator]
        H[Head of Department]
    end

    subgraph "USSD Gateway"
        AT[Africa's Talking<br/>USSD Gateway]
    end

    subgraph "System"
        SYS[USSD-Based<br/>Marks Appeal<br/>System]
    end

    S -- "USSD Input (ID, PIN, selection)" --> AT
    AT -- "USSD Response (menus, marks, status)" --> S
    AT -- "HTTP POST (sessionId, phoneNumber, text)" --> SYS
    SYS -- "HTTP Response (CON/END)" --> AT
    A -- "Login, Status Updates" --> SYS
    SYS -- "Dashboard, Appeals, Logs" --> A
    H -- "Login, Recommendations" --> SYS
    SYS -- "Departmental Appeals" --> H
```

---

## 2. Data Flow Diagram — Level 1

```mermaid
graph TD
    subgraph "External Entities"
        S[Student]
        AD[Administrator]
        HOD[Head of Department]
    end

    subgraph "Processes"
        P1["1.0 Authenticate Student"]
        P2["2.0 View Marks"]
        P3["3.0 Submit Appeal"]
        P4["4.0 Check Appeal Status"]
        P5["5.0 Manage Appeals"]
    end

    subgraph "Data Stores"
        D1[(pin_credentials)]
        D2[(marks)]
        D3[(appeals)]
        D4[(appeal_status)]
        D5[(access_audit)]
        D6[(admins)]
    end

    S --> P1
    P1 <--> D1
    P1 --> D5
    P1 --> P2
    P2 --> D2
    P2 --> S
    P1 --> P3
    P3 --> D2
    P3 --> D3
    P3 --> D5
    P3 --> S
    P1 --> P4
    P4 --> D3
    P4 --> D4
    P4 --> S
    AD --> P5
    HOD --> P5
    P5 <--> D3
    P5 --> D4
    P5 --> D6
    P5 --> D5
    P5 --> AD
    P5 --> HOD
```

---

## 3. Data Flow Diagram — Level 2 (Authenticate Student)

```mermaid
graph TD
    S[Student]

    subgraph "Process 1.0 Decomposition"
        SP1["1.1 Receive Student ID"]
        SP2["1.2 Receive PIN"]
        SP3["1.3 Hash PIN"]
        SP4["1.4 Compare Hash vs DB"]
        SP5["1.5 Enforce Lockout"]
        SP6["1.6 Log Event"]
    end

    subgraph "Data Stores"
        DPIN[(pin_credentials)]
        DAUDIT[(access_audit)]
    end

    S -- "student_id" --> SP1
    SP1 --> SP2
    S -- "PIN" --> SP2
    SP2 -- "plaintext PIN" --> SP3
    SP3 -- "SHA-256 hash" --> SP4
    SP4 <--> DPIN
    SP4 -- "match result" --> SP5
    SP5 -- "update attempts" --> DPIN
    SP5 -- "auth outcome" --> SP6
    SP6 --> DAUDIT
    SP6 -- "result prompt" --> S
```

---

## 4. Use Case Diagram

```mermaid
flowchart LR
    ST("Student")
    AD("Administrator")
    HD("HOD")

    UC1["UC1 Register PIN"]
    UC2["UC2 Authenticate via PIN"]
    UC3["UC3 Reset PIN via OTP"]
    UC4["UC4 View Marks"]
    UC5["UC5 Submit Marks Appeal"]
    UC6["UC6 Check Appeal Status"]
    UC7["UC7 Login Admin Portal"]
    UC8["UC8 View All Appeals"]
    UC9["UC9 Update Appeal Status"]
    UC10["UC10 View Audit Logs"]
    UC11["UC11 Logout"]
    UC12["UC12 Login HOD Portal"]
    UC13["UC13 View Dept Appeals"]
    UC14["UC14 Submit Recommendation"]

    ST --> UC1
    ST --> UC2
    ST --> UC3
    ST --> UC4
    ST --> UC5
    ST --> UC6
    AD --> UC7
    AD --> UC8
    AD --> UC9
    AD --> UC10
    AD --> UC11
    HD --> UC12
    HD --> UC13
    HD --> UC14

    UC4 -.->|include| UC2
    UC5 -.->|include| UC2
    UC6 -.->|include| UC2
    UC3 -.->|extend| UC2
```

---

## 5. Sequence Diagram — Student Submits an Appeal

```mermaid
sequenceDiagram
    participant S as Student
    participant P as Mobile Phone
    participant AT as Africa's Talking<br/>USSD Gateway
    participant F as Flask /ussd<br/>Endpoint
    participant DB as MySQL Database

    S->>P: Dial *123#
    P->>AT: USSD request
    AT->>F: POST /ussd (text="")
    F-->>AT: CON Welcome menu
    AT-->>P: Display menu
    P-->>S: "1. View marks<br/>2. Appeal..."

    S->>P: Select "2"
    P->>AT: text="2"
    AT->>F: POST /ussd (text="2")
    F-->>AT: CON Enter Student ID
    AT-->>P: Display prompt

    S->>P: Enter Student ID
    P->>AT: text="2*STU001"
    AT->>F: POST /ussd (text="2*STU001")
    F-->>AT: CON Enter your PIN

    S->>P: Enter PIN
    P->>AT: text="2*STU001*1234"
    AT->>F: POST /ussd (text="2*STU001*1234")
    F->>DB: Query pin_credentials
    DB-->>F: Record found
    F->>DB: Update failed_attempts=0
    F->>DB: Query marks
    DB-->>F: Module list
    F-->>AT: CON Select module
    AT-->>P: "1. DBMS (A)<br/>2. SE (B+)..."

    S->>P: Select "1"
    P->>AT: text="2*STU001*1234*1"
    AT->>F: POST /ussd
    F-->>AT: CON Enter reason

    S->>P: Type reason
    P->>AT: text="2*STU001*1234*1*Marking error"
    AT->>F: POST /ussd
    F->>DB: INSERT INTO appeals
    F->>DB: INSERT INTO access_audit
    F-->>AT: END Appeal submitted
    AT-->>P: Display confirmation
    P-->>S: "Appeal submitted"
```

---

## 6. Sequence Diagram — Administrator Updates Appeal Status

```mermaid
sequenceDiagram
    participant A as Admin
    participant B as Web Browser
    participant F as Flask Web Server
    participant DB as MySQL Database

    A->>B: Navigate to /admin/login
    B->>F: GET /admin/login
    F-->>B: Login page
    B-->>A: Display login form

    A->>B: Enter credentials
    B->>F: POST /admin/login
    F->>DB: Query admins
    DB-->>F: Admin record
    F-->>B: Set session, redirect
    B-->>A: Dashboard loaded

    A->>B: Select "Approved" & click Update
    B->>F: POST /hod/manage_appeal/5
    F->>DB: UPDATE appeals SET status_id=2
    DB-->>F: Row updated
    F-->>B: Redirect with flash
    B-->>A: "Appeal status updated"
```

---

## 7. Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    students ||--o{ marks : "has"
    students ||--o{ appeals : "submits"
    students ||--|| pin_credentials : "has"
    students ||--o{ access_audit : "generates"
    appeal_status ||--o{ appeals : "classifies"

    students {
        varchar student_id PK
        varchar full_name
        varchar phone_number
        varchar department
        varchar email
    }

    marks {
        int id PK
        varchar student_id FK
        varchar module_name
        int mark
        varchar academic_year
        varchar semester
    }

    appeals {
        int id PK
        varchar student_id FK
        varchar module_name
        text reason
        int status_id FK
        timestamp submitted_at
        timestamp resolved_at
        text hod_recommendation
    }

    appeal_status {
        int id PK
        varchar status_name
    }

    pin_credentials {
        int id PK
        varchar student_id FK
        varchar pin_hash
        int failed_attempts
        tinyint is_locked
        varchar otp_code
        datetime otp_expiry
    }

    access_audit {
        int id PK
        varchar student_id FK
        varchar phone_number
        varchar action
        tinyint success
        varchar session_id
        timestamp timestamp
    }

    admins {
        int id PK
        varchar username
        varchar password
    }
```

---

## 8. Physical Data Model (Relational Schema)

```text
appeal_db
│
├── students
│   ├── id              INT          PK AUTO_INCREMENT
│   ├── student_id      VARCHAR(20)  NOT NULL UNIQUE
│   ├── full_name       VARCHAR(100) NOT NULL
│   ├── phone_number    VARCHAR(15)  NOT NULL
│   ├── department      VARCHAR(100) NOT NULL
│   ├── email           VARCHAR(100) NULL
│   └── created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
│
├── admins
│   ├── id              INT          PK AUTO_INCREMENT
│   ├── username        VARCHAR(50)  NOT NULL UNIQUE
│   ├── password        VARCHAR(255) NOT NULL  (SHA-256)
│   └── created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
│
├── marks
│   ├── id              INT          PK AUTO_INCREMENT
│   ├── student_id      VARCHAR(20)  FK → students.student_id
│   ├── module_name     VARCHAR(100) NOT NULL
│   ├── mark            INT          NOT NULL
│   ├── academic_year   VARCHAR(20)  NULL
│   └── semester        VARCHAR(20)  NULL
│
├── appeal_status
│   ├── id              INT          PK AUTO_INCREMENT
│   └── status_name     VARCHAR(50)  NOT NULL
│       (Rows: Pending, Approved, Rejected)
│
├── appeals
│   ├── id              INT          PK AUTO_INCREMENT
│   ├── student_id      VARCHAR(20)  FK → students.student_id
│   ├── module_name     VARCHAR(100) NOT NULL
│   ├── reason          TEXT         NULL
│   ├── status_id       INT          NOT NULL DEFAULT 1  FK → appeal_status.id
│   ├── submitted_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
│   ├── resolved_at     TIMESTAMP    NULL
│   └── hod_recommendation TEXT     NULL
│
├── pin_credentials
│   ├── id              INT          PK AUTO_INCREMENT
│   ├── student_id      VARCHAR(20)  NOT NULL UNIQUE FK → students.student_id
│   ├── pin_hash        VARCHAR(64)  NOT NULL  (SHA-256)
│   ├── failed_attempts INT          DEFAULT 0
│   ├── is_locked       TINYINT(1)   DEFAULT 0
│   ├── otp_code        VARCHAR(10)  NULL
│   ├── otp_expiry      DATETIME     NULL
│   └── last_updated    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE
│
└── access_audit
    ├── id              INT          PK AUTO_INCREMENT
    ├── student_id      VARCHAR(20)  FK → students.student_id
    ├── phone_number    VARCHAR(15)  NULL
    ├── action          VARCHAR(100) NULL
    ├── success         TINYINT(1)   NULL
    ├── session_id      VARCHAR(100) NULL
    └── timestamp       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
```

---

## Table Summary

| Diagram | File | Description |
|---------|------|-------------|
| DFD Level 0 | `dfd_level0.dot` | Context diagram — system as single process |
| DFD Level 1 | `dfd_level1.dot` | 5 primary processes with data stores |
| DFD Level 2 | `dfd_level2_auth.dot` | Authentication sub-process decomposition |
| Use Case | `use_case.puml` | 3 actors, 14 use cases with relationships |
| Sequence (Appeal) | `sequence_appeal.puml` | Full student appeal flow via USSD |
| Sequence (Admin) | `sequence_admin.puml` | Admin login and status update flow |
| ERD | `erd.puml` | 7 entities with keys and relationships |
"""


# ════════════════════════════════════════════════════════════════════════════
# WRITE ALL FILES
# ════════════════════════════════════════════════════════════════════════════

print("Generating system diagrams...")

write("dfd_level0.dot", DFD_L0_DOT)
write("dfd_level1.dot", DFD_L1_DOT)
write("dfd_level2_auth.dot", DFD_L2_DOT)
write("use_case.puml", USE_CASE_PUML)
write("sequence_appeal.puml", SEQ_APPEAL_PUML)
write("sequence_admin.puml", SEQ_ADMIN_PUML)
write("erd.puml", ERD_PUML)
write("ALL_DIAGRAMS.md", MERMAID_MD)

print(f"\nAll diagrams generated in: {OUT}")
print("Open ALL_DIAGRAMS.md in VS Code or GitHub to view Mermaid diagrams.")
print("Use .dot files with Graphviz or .puml files with PlantUML for renders.")
