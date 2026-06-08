# ULK Marks Appeal System — System Diagrams

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
