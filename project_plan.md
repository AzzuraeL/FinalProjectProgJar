# 🃏 Liar's Deck Online — Project Planning Document

> **Mata Kuliah:** Pemrograman Jaringan / Jaringan Komputer  
> **Jenis Proyek:** Game Berbasis Jaringan (Network-Based Game)  
> **Bahasa Pemrograman:** Python 3.10+  
> **Game Engine:** Pygame  
> **Protokol Jaringan:** TCP  
> **Mode:** 2-Player Online (1 Room = 2 Players)

---

## Table of Contents

1. [Project Overview](#1-project-overview)  
2. [Alasan Pemilihan Protokol TCP](#2-alasan-pemilihan-protokol-tcp)  
3. [Game Design Document](#3-game-design-document)  
4. [Arsitektur Sistem](#4-arsitektur-sistem)  
5. [Spesifikasi Protokol Komunikasi (Packet Spec)](#5-spesifikasi-protokol-komunikasi-packet-spec)  
6. [Skema Game State](#6-skema-game-state)  
7. [Fitur Wajib — Detail Implementasi](#7-fitur-wajib--detail-implementasi)  
8. [Fitur Bonus — Detail Implementasi](#8-fitur-bonus--detail-implementasi)  
9. [Struktur Folder dan File](#9-struktur-folder-dan-file)  
10. [Desain UI / Layar (Screen Design)](#10-desain-ui--layar-screen-design)  
11. [Desain Database / Penyimpanan Data](#11-desain-database--penyimpanan-data)  
12. [Alur Program Lengkap (Flow Diagram)](#12-alur-program-lengkap-flow-diagram)  
13. [Dependencies & Tech Stack](#13-dependencies--tech-stack)  
14. [Milestone Pengembangan](#14-milestone-pengembangan)  
15. [Referensi](#15-referensi)

---

## 1. Project Overview

**Liar's Deck Online** adalah implementasi digital 2D berbasis jaringan dari permainan kartu bluffing *Liar's Deck* (terinspirasi dari *Liar's Bar*). Game ini dimainkan oleh tepat **2 pemain** secara real-time melalui jaringan, dengan tampilan 2D bergaya UNO Online.

### 1.1 Ringkasan Fitur Inti

| Kategori | Deskripsi |
|---|---|
| Jenis Game | Turn-based card bluffing + Russian Roulette |
| Jumlah Pemain | 2 pemain per room |
| Platform | PC (Windows/Linux/macOS) |
| Arsitektur | Client-Server (dedicated server) |
| Komunikasi | TCP Socket menggunakan JSON over TCP |
| Tampilan | Pygame 2D — mirip UNO Online |
| Bahasa | Python 3.10+ |

### 1.2 Tujuan Proyek

- Menerapkan konsep **sinkronisasi state jaringan** pada game real-time.  
- Mengimplementasikan **room system**, **matchmaking**, dan **game loop** berbasis server.  
- Membangun UI 2D interaktif dengan Pygame yang mencerminkan state server secara real-time.  
- Memenuhi semua **fitur wajib** dan sebagian **fitur bonus** sesuai spesifikasi proyek.

---

## 2. Alasan Pemilihan Protokol TCP

### 2.1 Keputusan: TCP (bukan UDP)

Proyek ini menggunakan **TCP (Transmission Control Protocol)** sebagai protokol jaringan utama. Berikut alasan teknis dan kontekstual pemilihannya:

### 2.2 Karakteristik Game vs Kebutuhan Protokol

| Aspek | Liar's Deck Online | TCP | UDP |
|---|---|---|---|
| Kecepatan pengiriman | Tidak kritis (turn-based) | ✅ Cukup cepat | ✅ Lebih cepat |
| Reliabilitas data | **Sangat kritis** | ✅ Dijamin | ❌ Tidak dijamin |
| Urutan paket | **Sangat kritis** (urutan giliran) | ✅ Dijamin | ❌ Tidak dijamin |
| Toleransi packet loss | **Nol toleransi** (kartu hilang = bug fatal) | ✅ Retransmit otomatis | ❌ Paket bisa hilang |
| Konsistensi state | **Harus identik** di kedua client | ✅ Lebih mudah | ❌ Butuh logic tambahan |
| Overhead implementasi | - | ✅ Lebih simpel | ❌ Butuh ACK manual |

### 2.3 Argumen Utama

1. **Game Turn-Based, Bukan Real-Time FPS.**  
   Liar's Deck bukan game tembak-menembak yang butuh update 60x/detik. Setiap "event" terjadi ketika pemain menekan tombol, sehingga latensi sub-milidetik tidak diperlukan. TCP lebih dari cukup.

2. **Integritas Data Kritis.**  
   Setiap paket game — kartu yang dimainkan, tuduhan liar, trigger roulette — bersifat krusial. Hilangnya satu paket saja bisa menyebabkan state kedua klien berbeda (desync). TCP menjamin setiap byte sampai dan berurutan.

3. **Implementasi Lebih Bersih dan Maintainable.**  
   UDP membutuhkan implementasi acknowledgment, sequence number, dan retransmission secara manual. Dengan TCP, semua itu sudah ditangani OS/kernel, sehingga kode lebih fokus pada logika game.

4. **Anti-Invalid Packet Lebih Mudah.**  
   Dengan TCP, selama koneksi aktif, paket pasti datang utuh dan berurutan. Validasi hanya perlu memastikan format JSON dan isi data benar — tidak perlu khawatir paket terpotong atau datang out-of-order.

5. **Reconnect Handling Lebih Terstruktur.**  
   TCP memiliki mekanisme koneksi eksplisit (connect/disconnect/timeout), sehingga server mudah mendeteksi jika klien terputus dan menjalankan logika reconnect dengan session token.

### 2.4 Kompromi TCP yang Diterima

- **Head-of-line blocking**: Tidak bermasalah karena game ini turn-based.  
- **Overhead handshake**: Tidak signifikan karena koneksi bersifat persistent (long-lived connection per game session).  
- **Nagle's algorithm**: Akan dinonaktifkan dengan `socket.TCP_NODELAY = True` untuk memastikan pengiriman paket kecil bersifat immediate.

---

## 3. Game Design Document

### 3.1 Konsep Game

Liar's Deck Online adalah permainan kartu bluffing untuk **2 pemain** di mana setiap pemain harus memainkan kartu wajah-bawah sambil mengklaim bahwa kartu tersebut adalah "kartu meja" yang telah ditentukan. Pemain lawan bisa menantang kejujuran claim tersebut. Pemain yang kalah tantangan harus menarik pelatuk revolver. Pemain yang bertahan hidup hingga lawan mati adalah pemenangnya.

### 3.2 The Deck (Dek Kartu)

**Total: 20 kartu**, terdiri dari:

| Jenis Kartu | Jumlah | Keterangan |
|---|---|---|
| Ace (A) | 6 | Kartu reguler |
| King (K) | 6 | Kartu reguler |
| Queen (Q) | 6 | Kartu reguler |
| Joker (J) | 2 | Wild card — selalu bernilai sebagai kartu meja |
| **Total** | **20** | |

**Distribusi untuk 2 Pemain:**
- Setiap pemain menerima **5 kartu** di tangan.
- **10 kartu sisanya** dikocok dan tidak digunakan dalam ronde tersebut.
- Kartu dikocokan ulang di setiap ronde baru.

**Peluang Kebenaran per Kartu yang Dimainkan:**
- Jika kartu meja adalah Ace: kartu "benar" = 6 Ace + 2 Joker = **8 dari 20** kartu (40%)
- Kartu "bohong" = 12 dari 20 kartu (60%) → lebih banyak yang bohong daripada yang jujur!

### 3.3 Alur Satu Ronde (Round Flow)

```
[START ROUND]
      │
      ▼
[Kocok 20 kartu]
      │
      ▼
[Bagikan 5 kartu ke tiap pemain]
10 kartu tersisa disingkirkan
      │
      ▼
[Tentukan "Kartu Meja": Ace / King / Queen]
(dipilih secara acak oleh server)
      │
      ▼
[Tentukan siapa yang giliran pertama]
(random atau bergantian tiap ronde)
      │
      ▼
[===== GAME LOOP =====]
      │
      ▼
[Giliran Pemain Aktif]
 Pemain memilih 1–N kartu dari tangan,
 menaruh face-down di tengah meja,
 mengklaim "ini semua [kartu meja]"
      │
      ├─────────────────────────┐
      ▼                         ▼
[Pemain berikutnya       [Pemain berikutnya
 PERCAYA → giliran        TIDAK PERCAYA →
 berikutnya bermain]      "LIAR!" challenge]
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
             [Kartu TERBUKA]       [Kartu TERBUKA]
             [Semua Benar /        [Ada yang Bohong /
              semua Joker]          bukan kartu meja]
                    │                     │
                    ▼                     ▼
         [Penantang KALAH]      [Pemain yang Ditantang
          Penantang main          KALAH → dia main
          ROULETTE]               ROULETTE]
                    └─────────┬───────────┘
                              ▼
                    [Roulette Sequence]
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
             [Selamat]            [MATI → Pemain
           [Game loop             keluar. Game
            lanjut]               SELESAI]
```

### 3.4 Mekanisme Roulette

Setiap pemain memiliki revolver 6 ruang dengan **1 peluru hidup**. Setiap pull berurutan untuk pemain yang sama meningkatkan peluang kematian karena ruang kosong sudah habis.

| Pull ke- | Chamber tersisa | Peluang Mati | Peluang Hidup |
|---|---|---|---|
| 1 | 6/6 | 1/6 ≈ 16.67% | 5/6 ≈ 83.33% |
| 2 | 5/6 | 1/5 = 20.00% | 4/5 = 80.00% |
| 3 | 4/6 | 1/4 = 25.00% | 3/4 = 75.00% |
| 4 | 3/6 | 1/3 ≈ 33.33% | 2/3 ≈ 66.67% |
| 5 | 2/6 | 1/2 = 50.00% | 1/2 = 50.00% |
| 6 | 1/6 | **6/6 = 100%** | 0% |

**Aturan Penting Roulette:**
- Posisi peluru **tetap** selama satu game (tidak dikocok ulang antar roulette).
- Server menentukan posisi peluru di awal game secara acak (`random.randint(1, 6)`).
- Server melacak `pull_count[player_id]` untuk menentukan apakah chamber saat ini berisi peluru.
- Animasi roulette ditampilkan di client (tanpa mengungkap posisi peluru sebelum pull).
- Setelah mati, revolver pemain tersebut "dikunci" dan tidak bisa digunakan lagi.

**Logika Server untuk Roulette:**
```python
# Di awal game:
bullet_position = random.randint(1, 6)  # posisi peluru (1-6)
pull_count[player_id] = 0               # berapa kali sudah ditarik

# Saat roulette dipicu:
pull_count[player_id] += 1
if pull_count[player_id] == bullet_position:
    result = "DEAD"
else:
    result = "SURVIVED"
    # odds sekarang: 1/(6 - pull_count) untuk pull berikutnya
```

### 3.5 Aturan Khusus: Joker

- Joker **selalu** bernilai sebagai kartu meja yang aktif.  
- Jika kartu meja adalah "Ace", Joker dianggap sebagai Ace.  
- Joker tidak bisa "berbohong" — selalu benar saat dimainkan.  
- Pemain bisa menggunakan Joker sebagai "kartu aman" kapan saja.

### 3.6 Kondisi Akhir Game (End Condition)

Untuk 2 pemain:
- Game berakhir ketika **salah satu pemain mati** saat roulette.
- Pemain yang bertahan hidup adalah **pemenang**.
- Jika semua kartu di tangan kedua pemain habis dimainkan dalam satu ronde, ronde baru dimulai (kartu dikocok dan dibagikan ulang).

### 3.7 Variasi: Devil Mode *(Opsional / Bonus)*

Mode Devil menambahkan **Devil's Card** sebagai wildcard tambahan atau modifier rule. Detail implementasi bisa ditambahkan sebagai fitur bonus jika waktu memungkinkan.

---

## 4. Arsitektur Sistem

### 4.1 Topologi Jaringan

```
┌─────────────────────────────────────────────────────────┐
│                    DEDICATED SERVER                      │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐   ┌───────────┐  │
│  │  Lobby Mgr   │    │  Room Mgr    │   │  Logger   │  │
│  │  (matchmake) │    │  (game loop) │   │  (file)   │  │
│  └──────────────┘    └──────────────┘   └───────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              TCP Socket Handler                  │   │
│  │          (per-client thread / asyncio)           │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  Port: 12345 (game)    Port: 12346 (ping/health check)  │
└────────────────────┬────────────────────────────────────┘
                     │  TCP
          ┌──────────┴──────────┐
          │                     │
┌─────────▼──────────┐ ┌───────▼─────────────┐
│   CLIENT A          │ │   CLIENT B           │
│   (Pygame UI)       │ │   (Pygame UI)        │
│                     │ │                      │
│ - Render game state │ │ - Render game state  │
│ - Handle input      │ │ - Handle input       │
│ - Send actions      │ │ - Send actions       │
│ - Show ping (ms)    │ │ - Show ping (ms)     │
└─────────────────────┘ └──────────────────────┘
```

### 4.2 Server Architecture

Server berjalan sebagai program Python standalone yang:
- Membuka TCP socket pada port yang ditentukan.
- Menggunakan **threading** (satu thread per client) atau **asyncio** untuk menangani koneksi konkuren.
- Memiliki komponen berikut:

```
server/
├── main_server.py          ← Entry point, inisialisasi socket
├── lobby_manager.py        ← Manajemen antrian & matchmaking
├── room_manager.py         ← Manajemen room aktif
├── game_engine.py          ← Logika game (deck, roulette, validasi)
├── client_handler.py       ← Per-client thread handler
├── packet_validator.py     ← Validasi & sanitasi paket masuk
├── logger.py               ← Logging aktivitas ke file
└── config.py               ← Konfigurasi server (port, timeout, dll)
```

**State yang di-maintain server:**
```python
# Lobby State
waiting_queue: list[ClientSession]    # antrian matchmaking
active_rooms: dict[room_id, Room]     # room yang sedang bermain

# Per-Room State
class Room:
    room_id: str
    players: list[PlayerState]        # tepat 2 player
    deck: list[Card]                  # 20 kartu, sudah dikocok
    table_card: str                   # "ACE" | "KING" | "QUEEN"
    center_pile: list[Card]           # kartu yang sudah dimainkan ronde ini
    current_turn: int                 # index pemain (0 atau 1)
    last_play: dict                   # kartu terakhir yang dimainkan + siapa
    game_phase: str                   # "WAITING" | "PLAYING" | "CHALLENGE" | "ROULETTE" | "GAME_OVER"
    round_number: int

# Per-Player State
class PlayerState:
    player_id: str
    session_token: str                # untuk reconnect
    username: str
    hand: list[Card]                  # 5 kartu di tangan
    roulette_pull_count: int          # berapa kali sudah main roulette
    bullet_position: int              # posisi peluru (1-6), HANYA server yang tahu
    is_alive: bool
    is_connected: bool
    last_ping: float                  # timestamp ping terakhir
```

### 4.3 Client Architecture

Client berjalan sebagai program Pygame yang:
- Menampilkan semua layar (Lobby, Game, Game Over).
- Mengirim aksi user ke server via TCP.
- Menerima `game_state` update dari server dan me-render ulang tampilan.
- Tidak menyimpan game state lokal yang "authoritative" — semua kebenaran ada di server.

```
client/
├── main_client.py          ← Entry point, inisialisasi Pygame
├── network.py              ← TCP socket connection & send/receive
├── screens/
│   ├── screen_login.py     ← Layar input username & server IP
│   ├── screen_lobby.py     ← Layar antrian matchmaking
│   ├── screen_game.py      ← Layar permainan utama
│   └── screen_gameover.py  ← Layar hasil akhir
├── components/
│   ├── card_sprite.py      ← Sprite kartu (face-up & face-down)
│   ├── roulette_anim.py    ← Animasi revolver
│   ├── ping_display.py     ← Indikator ping/latency
│   └── button.py           ← Komponen UI tombol generik
├── assets/
│   ├── images/             ← Sprite, background, ikon
│   ├── fonts/              ← Font TTF
│   └── sounds/             ← SFX (opsional)
└── config.py               ← Konfigurasi client (IP, port, resolusi)
```

### 4.4 Communication Flow (Sequence)

```
CLIENT A                    SERVER                    CLIENT B
   │                           │                          │
   │──── [CONNECT TCP] ────────▶│                          │
   │◀─── [WELCOME + session] ───│                          │
   │                           │◀──── [CONNECT TCP] ───────│
   │                           │────  [WELCOME + session] ─▶│
   │                           │                          │
   │──── [JOIN_LOBBY] ─────────▶│                          │
   │                           │◀──── [JOIN_LOBBY] ────────│
   │                           │                          │
   │                   [Matchmaking: 2 players found]      │
   │                           │                          │
   │◀─── [MATCH_FOUND] ────────│──── [MATCH_FOUND] ───────▶│
   │◀─── [GAME_STATE_UPDATE] ──│──── [GAME_STATE_UPDATE] ──▶│
   │                           │                          │
   │   (Player A's turn)       │                          │
   │──── [PLAY_CARDS] ─────────▶│                          │
   │                    [Validate action]                  │
   │◀─── [GAME_STATE_UPDATE] ──│──── [GAME_STATE_UPDATE] ──▶│
   │                           │                          │
   │                           │   (Player B's turn)      │
   │                           │◀───── [CALL_LIAR] ────────│
   │                    [Process challenge]                │
   │◀─── [REVEAL_CARDS] ───────│──── [REVEAL_CARDS] ───────▶│
   │◀─── [ROULETTE_START] ─────│──── [ROULETTE_START] ─────▶│
   │                           │                          │
   │──── [ROULETTE_PULL] ──────▶│                          │
   │                    [Compute result]                   │
   │◀─── [ROULETTE_RESULT] ────│──── [ROULETTE_RESULT] ────▶│
   │◀─── [GAME_STATE_UPDATE] ──│──── [GAME_STATE_UPDATE] ──▶│
   │                           │                          │
   │      ... (game continues) ...                         │
   │                           │                          │
   │◀─── [GAME_OVER] ──────────│──── [GAME_OVER] ──────────▶│
```

---

## 5. Spesifikasi Protokol Komunikasi (Packet Spec)

### 5.1 Format Paket Dasar

Semua paket dikirim sebagai **JSON string** yang diakhiri dengan newline `\n` (line-delimited JSON). Server dan client membaca stream TCP dengan `recv_until('\n')`.

```
[4 bytes: panjang payload (big-endian uint32)] [N bytes: JSON string]
```

Atau format sederhana (pilih salah satu, konsisten):
```
{"type": "PACKET_TYPE", "payload": {...}}\n
```

### 5.2 Daftar Packet Types

#### C → S (Client ke Server)

| Packet Type | Deskripsi | Payload |
|---|---|---|
| `CONNECT` | Koneksi awal, kirim username | `{username, client_version}` |
| `RECONNECT` | Reconect dengan session token | `{session_token, username}` |
| `JOIN_LOBBY` | Minta masuk antrian matchmaking | `{}` |
| `LEAVE_LOBBY` | Keluar dari antrian | `{}` |
| `PLAY_CARDS` | Mainkan kartu dari tangan | `{card_indices: [int], claimed_type: str}` |
| `CALL_LIAR` | Tantang pemain sebelumnya | `{}` |
| `ROULETTE_PULL` | Konfirmasi tarik pelatuk | `{}` |
| `PING` | Ping untuk mengukur latency | `{timestamp: float}` |
| `CHAT` | Pesan chat *(opsional)* | `{message: str}` |
| `READY` | Pemain siap mulai ronde baru | `{}` |

#### S → C (Server ke Client)

| Packet Type | Deskripsi | Payload |
|---|---|---|
| `WELCOME` | Respons koneksi berhasil | `{session_token, player_id}` |
| `RECONNECT_OK` | Reconnect berhasil | `{game_state_snapshot}` |
| `RECONNECT_FAIL` | Session tidak valid/kadaluarsa | `{reason: str}` |
| `LOBBY_JOINED` | Berhasil masuk antrian | `{queue_position: int}` |
| `MATCH_FOUND` | Pasangan ditemukan | `{room_id, opponent_username}` |
| `GAME_STATE_UPDATE` | Update state game lengkap | `{game_state}` (lihat §6) |
| `YOUR_TURN` | Notifikasi giliran kamu | `{time_limit_seconds: int}` |
| `PLAY_ACCEPTED` | Kartu berhasil dimainkan | `{cards_played: int}` |
| `PLAY_REJECTED` | Aksi tidak valid | `{reason: str}` |
| `LIAR_CALLED` | Pemain lawan menyebut liar | `{caller_id: str}` |
| `REVEAL_CARDS` | Kartu terakhir diungkap | `{cards: list, was_lying: bool}` |
| `ROULETTE_START` | Mulai sekuens roulette | `{player_id, pull_number, survival_odds}` |
| `ROULETTE_RESULT` | Hasil roulette | `{player_id, result: "DEAD"/"SURVIVED", pull_number}` |
| `ROUND_RESET` | Ronde baru dimulai | `{new_table_card, round_number}` |
| `GAME_OVER` | Game selesai | `{winner_id, winner_username, reason}` |
| `OPPONENT_DISCONNECTED` | Lawan terputus | `{timeout_remaining: int}` |
| `OPPONENT_RECONNECTED` | Lawan terhubung kembali | `{}` |
| `PONG` | Respons ping | `{timestamp: float, server_time: float}` |
| `ERROR` | Error dari server | `{code: int, message: str}` |
| `CHAT_MSG` | Pesan chat diteruskan | `{sender: str, message: str}` |

### 5.3 Anti-Invalid Packet

Server memvalidasi setiap paket masuk:

```python
# packet_validator.py

REQUIRED_FIELDS = {
    "PLAY_CARDS": ["card_indices", "claimed_type"],
    "RECONNECT":  ["session_token", "username"],
    "PING":       ["timestamp"],
    # dst...
}

VALID_CLAIMED_TYPES = {"ACE", "KING", "QUEEN"}

def validate_packet(packet: dict, player_state: PlayerState) -> tuple[bool, str]:
    # 1. Cek field 'type' ada
    if "type" not in packet:
        return False, "Missing 'type' field"

    ptype = packet.get("type")

    # 2. Cek packet type dikenal
    if ptype not in KNOWN_PACKET_TYPES:
        return False, f"Unknown packet type: {ptype}"

    # 3. Cek field wajib ada
    payload = packet.get("payload", {})
    for field in REQUIRED_FIELDS.get(ptype, []):
        if field not in payload:
            return False, f"Missing required field: {field}"

    # 4. Validasi kontekstual: apakah giliran pemain ini?
    if ptype == "PLAY_CARDS" and not is_player_turn(player_state):
        return False, "Not your turn"

    # 5. Validasi kartu: index valid dan kartu ada di tangan
    if ptype == "PLAY_CARDS":
        indices = payload["card_indices"]
        if not isinstance(indices, list) or len(indices) == 0:
            return False, "card_indices must be non-empty list"
        if len(indices) > len(player_state.hand):
            return False, "Cannot play more cards than in hand"
        if any(i < 0 or i >= len(player_state.hand) for i in indices):
            return False, "Card index out of range"
        if payload["claimed_type"] not in VALID_CLAIMED_TYPES:
            return False, "Invalid claimed card type"

    # 6. Validasi game phase
    if ptype in PLAY_PHASE_PACKETS and current_phase != "PLAYING":
        return False, f"Action {ptype} not allowed in phase {current_phase}"

    return True, "OK"
```

---

## 6. Skema Game State

### 6.1 Full Game State Object (dikirim via `GAME_STATE_UPDATE`)

```json
{
  "room_id": "room_abc123",
  "round_number": 2,
  "table_card": "ACE",
  "game_phase": "PLAYING",
  "current_turn_player_id": "player_1",
  "center_pile_count": 3,
  "last_play": {
    "player_id": "player_0",
    "cards_count": 2,
    "claimed_type": "ACE",
    "revealed": false,
    "revealed_cards": null
  },
  "players": [
    {
      "player_id": "player_0",
      "username": "Alice",
      "hand_count": 3,
      "hand": ["ACE", "KING", "JOKER", "QUEEN", "ACE"],
      "roulette_pull_count": 1,
      "is_alive": true,
      "is_connected": true,
      "ping_ms": 42
    },
    {
      "player_id": "player_1",
      "username": "Bob",
      "hand_count": 5,
      "hand": null,
      "roulette_pull_count": 0,
      "is_alive": true,
      "is_connected": true,
      "ping_ms": 78
    }
  ],
  "roulette_state": {
    "active": false,
    "target_player_id": null,
    "pull_number": null,
    "survival_odds": null
  },
  "timestamp": 1718000000.123
}
```

> **Catatan Penting:**  
> - Field `hand` hanya berisi kartu untuk **pemain yang menerima paket** (data pribadi). Untuk lawan, `hand` = `null` dan hanya `hand_count` yang dikirim.  
> - Posisi peluru roulette **tidak pernah dikirim ke client**. Hanya server yang tahu.

### 6.2 Game Phases (FSM)

```
                     ┌───────────────┐
                     │    WAITING    │◀──── kedua pemain connect
                     └───────┬───────┘
                             │ kedua pemain READY
                             ▼
                     ┌───────────────┐
             ┌──────▶│    DEALING    │◀──── round reset
             │       └───────┬───────┘
             │               │ kartu terbagi, table_card ditentukan
             │               ▼
             │       ┌───────────────┐
             │       │    PLAYING    │◀──────────────┐
             │       └───────┬───────┘               │
             │               │ CALL_LIAR datang       │
             │               ▼                       │
             │       ┌───────────────┐               │
             │       │  CHALLENGING  │               │
             │       └───────┬───────┘               │
             │               │ kartu terungkap, loser ditentukan
             │               ▼                       │
             │       ┌───────────────┐               │
             │       │   ROULETTE    │               │
             │       └───────┬───────┘               │
             │         ┌─────┴──────┐                │
             │         ▼            ▼                 │
             │   [SURVIVED]       [DEAD]              │
             └──────────┘           │                 │
                        ROUND_RESET │                 │
                    (jika kartu     │                 │
                     habis, bukan   ▼                 │
                     mati)   ┌───────────────┐        │
                             │   GAME_OVER   │        │
                             └───────────────┘        │
                                                      │
                        PLAYING → semua kartu habis ──┘
```

---

## 7. Fitur Wajib — Detail Implementasi

### 7.1 Real-Time Update

**Strategi:** Server mengirim `GAME_STATE_UPDATE` ke semua pemain dalam room setiap kali ada perubahan state yang signifikan.

```python
# Setelah setiap aksi valid diproses:
def broadcast_state(room: Room):
    for player in room.players:
        state = build_state_for_player(room, player.player_id)
        packet = {"type": "GAME_STATE_UPDATE", "payload": state}
        player.connection.send(serialize(packet))
```

**Client-side:** Client memiliki event loop yang:
1. Membaca paket dari socket (non-blocking dengan `select` atau thread terpisah).
2. Meng-update `local_state` ketika `GAME_STATE_UPDATE` diterima.
3. Pygame render loop (`while running`) menggambar `local_state` setiap frame.

```python
# client/network.py — receive thread
def receive_loop(sock, state_queue):
    buffer = ""
    while True:
        data = sock.recv(4096).decode("utf-8")
        buffer += data
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            packet = json.loads(line)
            state_queue.put(packet)   # thread-safe queue ke main thread
```

---

### 7.2 Game State Synchronization

**Pendekatan:** Server sebagai **single source of truth**. Client tidak pernah mengubah state lokal secara unilateral — hanya mengirim aksi, dan mengaplikasikan state yang datang dari server.

**Mekanisme:**
1. Setiap `GAME_STATE_UPDATE` menyertakan `timestamp` dan sequence number.
2. Client hanya mengaplikasikan state jika sequence number lebih besar dari yang terakhir diterima (drop late packets).
3. Saat reconnect, server mengirim **full state snapshot** untuk resync.

```python
# client — apply state
def apply_state(new_state: dict):
    if new_state["seq"] > local_seq:
        local_state = new_state
        local_seq = new_state["seq"]
    # else: drop (state lama)
```

---

### 7.3 Reconnect Handling

**Flow:**
1. Server mendeteksi client disconnect (socket error / timeout).
2. Server menandai `player.is_connected = False` dan memulai **countdown 60 detik**.
3. Server mengirim `OPPONENT_DISCONNECTED` ke pemain lain, dengan `timeout_remaining`.
4. Selama countdown, game **di-pause** (giliran tidak berjalan).
5. Jika client reconnect dengan `session_token` yang valid sebelum timeout → game dilanjutkan.
6. Jika timeout habis → pemain yang disconnect dinyatakan kalah (GAME_OVER).

```python
# server/client_handler.py
def handle_disconnect(player: PlayerState, room: Room):
    player.is_connected = False
    broadcast(room, {"type": "OPPONENT_DISCONNECTED",
                     "payload": {"timeout_remaining": 60}})
    timer = threading.Timer(60.0, lambda: forfeit_player(player, room))
    player.reconnect_timer = timer
    timer.start()

def handle_reconnect(session_token: str, new_conn) -> bool:
    player = find_player_by_token(session_token)
    if player and not player.is_alive == False:
        player.reconnect_timer.cancel()
        player.connection = new_conn
        player.is_connected = True
        # Kirim full state snapshot
        new_conn.send(serialize({
            "type": "RECONNECT_OK",
            "payload": build_full_state(player)
        }))
        broadcast(player.room, {"type": "OPPONENT_RECONNECTED", "payload": {}})
        return True
    return False
```

---

### 7.4 Ping / Latency Indicator

**Implementasi:**
- Client mengirim `PING` packet setiap **1 detik** dengan `timestamp` lokal.
- Server segera membalas dengan `PONG` + timestamp server.
- Client menghitung: `latency_ms = (time.time() - sent_timestamp) * 1000`.
- Latency ditampilkan di corner layar game dengan color coding:
  - 🟢 Hijau: < 80ms
  - 🟡 Kuning: 80–150ms  
  - 🔴 Merah: > 150ms

```python
# client/components/ping_display.py
class PingDisplay:
    def __init__(self):
        self.ping_ms = 0
        self.last_ping_sent = 0

    def send_ping(self, sock):
        if time.time() - self.last_ping_sent >= 1.0:
            ts = time.time()
            sock.send(serialize({"type": "PING", "payload": {"timestamp": ts}}))
            self.last_ping_sent = ts

    def on_pong(self, packet):
        sent_ts = packet["payload"]["timestamp"]
        self.ping_ms = int((time.time() - sent_ts) * 1000)

    def get_color(self):
        if self.ping_ms < 80:   return (0, 200, 0)     # Hijau
        if self.ping_ms < 150:  return (255, 200, 0)   # Kuning
        return (255, 50, 50)                             # Merah

    def draw(self, surface, font, pos):
        text = f"Ping: {self.ping_ms} ms"
        color = self.get_color()
        surface.blit(font.render(text, True, color), pos)
```

---

### 7.5 Logging Aktivitas Player

**Server Logger** mencatat setiap event game ke file log dengan format terstruktur.

```python
# server/logger.py
import logging
import os
from datetime import datetime

class GameLogger:
    def __init__(self, log_dir="logs"):
        os.makedirs(log_dir, exist_ok=True)
        filename = f"{log_dir}/game_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            filename=filename,
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(message)s"
        )
        self.logger = logging.getLogger("GameLogger")

    def log_connect(self, player_id, username, ip):
        self.logger.info(f"CONNECT | player={player_id} | user={username} | ip={ip}")

    def log_play_cards(self, room_id, player_id, cards, claimed):
        self.logger.info(f"PLAY | room={room_id} | player={player_id} | "
                         f"cards={cards} | claimed={claimed}")

    def log_liar_call(self, room_id, caller_id, target_id):
        self.logger.info(f"LIAR_CALL | room={room_id} | caller={caller_id} | target={target_id}")

    def log_reveal(self, room_id, player_id, cards, was_lying):
        self.logger.info(f"REVEAL | room={room_id} | player={player_id} | "
                         f"cards={cards} | lying={was_lying}")

    def log_roulette(self, room_id, player_id, pull_num, result):
        self.logger.info(f"ROULETTE | room={room_id} | player={player_id} | "
                         f"pull={pull_num} | result={result}")

    def log_game_over(self, room_id, winner_id, reason):
        self.logger.info(f"GAME_OVER | room={room_id} | winner={winner_id} | reason={reason}")

    def log_disconnect(self, player_id, reason):
        self.logger.info(f"DISCONNECT | player={player_id} | reason={reason}")

    def log_invalid_packet(self, player_id, reason, raw_data):
        self.logger.warning(f"INVALID_PACKET | player={player_id} | "
                            f"reason={reason} | raw={raw_data[:200]}")
```

**Contoh output log:**
```
2025-06-12 10:23:01 | INFO    | CONNECT    | player=p001 | user=Alice | ip=192.168.1.5
2025-06-12 10:23:02 | INFO    | CONNECT    | player=p002 | user=Bob   | ip=192.168.1.8
2025-06-12 10:23:05 | INFO    | PLAY       | room=r001  | player=p001 | cards=['ACE','JOKER'] | claimed=ACE
2025-06-12 10:23:12 | INFO    | LIAR_CALL  | room=r001  | caller=p002 | target=p001
2025-06-12 10:23:12 | INFO    | REVEAL     | room=r001  | player=p001 | cards=['ACE','JOKER'] | lying=False
2025-06-12 10:23:14 | INFO    | ROULETTE   | room=r001  | player=p002 | pull=1 | result=SURVIVED
2025-06-12 10:23:45 | WARNING | INVALID_PACKET | player=p002 | reason=Not your turn | raw=...
```

---

### 7.6 Anti-Invalid Packet Sederhana

Implementasi di `packet_validator.py` (detail kode ada di §5.3). Selain validasi per-field:

```python
# Rate limiting: max 10 paket per detik per client
class RateLimiter:
    def __init__(self, max_per_second=10):
        self.max = max_per_second
        self.counts = {}    # player_id → (count, window_start)

    def is_allowed(self, player_id) -> bool:
        now = time.time()
        count, window = self.counts.get(player_id, (0, now))
        if now - window > 1.0:
            self.counts[player_id] = (1, now)
            return True
        if count >= self.max:
            return False
        self.counts[player_id] = (count + 1, window)
        return True
```

Server juga memutus koneksi client yang mengirim terlalu banyak paket invalid berturut-turut (threshold: 5x dalam 10 detik → kick + log warning).

---

## 8. Fitur Bonus — Detail Implementasi

### 8.1 Dedicated Game Server *(Bonus)*

Server dijalankan sebagai program standalone yang bisa berjalan di mesin terpisah dari client. Konfigurasi via `config.py`:

```python
SERVER_HOST = "0.0.0.0"   # dengarkan semua interface
SERVER_PORT = 12345
MAX_ROOMS = 10
RECONNECT_TIMEOUT = 60    # detik
```

Server bisa dijalankan di mesin manapun: `python server/main_server.py`. Client tinggal menginput IP server.

---

### 8.2 Spectator Mode *(Bonus)*

- Pemain ketiga bisa bergabung ke room aktif sebagai spectator.
- Server mengirim `GAME_STATE_UPDATE` ke spectator juga, **tanpa** data hand pemain.
- Spectator tidak bisa mengirim aksi game, hanya bisa melihat.
- Server memisahkan broadcast: `broadcast_to_players()` vs `broadcast_to_all()`.

```python
def broadcast_state(room: Room):
    # Kirim ke players (dengan hand mereka sendiri)
    for player in room.players:
        state = build_state_for_player(room, player.player_id, include_hand=True)
        player.conn.send(serialize({"type": "GAME_STATE_UPDATE", "payload": state}))
    # Kirim ke spectators (tanpa hand)
    for spectator in room.spectators:
        state = build_state_for_spectator(room)
        spectator.conn.send(serialize({"type": "GAME_STATE_UPDATE", "payload": state}))
```

---

### 8.3 Ranking System *(Bonus)*

Server menyimpan statistik pemain di file JSON/SQLite:

```json
{
  "players": {
    "Alice": {"wins": 5, "losses": 3, "total_games": 8, "roulette_survived": 12, "roulette_deaths": 3},
    "Bob":   {"wins": 3, "losses": 5, "total_games": 8, "roulette_survived": 8,  "roulette_deaths": 5}
  }
}
```

Ranking screen menampilkan leaderboard berdasarkan wins. Data disimpan ke `data/rankings.json` dan di-load saat server start.

---

### 8.4 Match Replay *(Bonus)*

Server menyimpan seluruh log aksi satu game dalam format yang bisa di-replay:

```json
{
  "match_id": "match_20250612_102300",
  "players": ["Alice", "Bob"],
  "events": [
    {"seq": 1, "time": 0.0,  "type": "ROUND_START",  "data": {"table_card": "ACE"}},
    {"seq": 2, "time": 5.3,  "type": "PLAY_CARDS",   "data": {"player": "Alice", "cards": ["ACE","JOKER"], "claimed": "ACE"}},
    {"seq": 3, "time": 12.1, "type": "CALL_LIAR",    "data": {"player": "Bob", "target": "Alice"}},
    {"seq": 4, "time": 12.1, "type": "REVEAL",       "data": {"cards": ["ACE","JOKER"], "lying": false}},
    {"seq": 5, "time": 14.8, "type": "ROULETTE",     "data": {"player": "Bob", "pull": 1, "result": "SURVIVED"}}
  ]
}
```

Client replay mode bisa "memutarkan" game dari file ini step-by-step.

---

### 8.5 Voice Communication *(Bonus)*

Menggunakan library `pyaudio` dan UDP untuk stream audio real-time antar 2 pemain.

```
Client A → [pyaudio capture] → [UDP ke server/peer] → [pyaudio playback] → Client B
```

Karena sifat audio streaming yang toleran terhadap packet loss, UDP cocok **khusus untuk fitur voice ini** (berbeda dari game logic yang tetap pakai TCP).

---

## 9. Struktur Folder dan File

```
liars_deck_online/
│
├── server/
│   ├── main_server.py          # Entry point server
│   ├── client_handler.py       # Thread handler per client
│   ├── lobby_manager.py        # Matchmaking & antrian
│   ├── room_manager.py         # Manajemen room aktif
│   ├── game_engine.py          # Core game logic
│   ├── packet_validator.py     # Validasi & sanitasi paket
│   ├── logger.py               # Logging ke file
│   └── config.py               # Konfigurasi server
│
├── client/
│   ├── main_client.py          # Entry point client (Pygame)
│   ├── network.py              # TCP connection & send/recv
│   ├── game_state.py           # Local state holder
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── screen_login.py     # Layar login & input server IP
│   │   ├── screen_lobby.py     # Layar antrian matchmaking
│   │   ├── screen_game.py      # Layar permainan utama
│   │   └── screen_gameover.py  # Layar hasil akhir & statistik
│   ├── components/
│   │   ├── __init__.py
│   │   ├── card_sprite.py      # Render kartu (face-up/down)
│   │   ├── roulette_anim.py    # Animasi revolver
│   │   ├── ping_display.py     # Indikator ping
│   │   ├── hand_display.py     # Render tangan kartu
│   │   ├── center_pile.py      # Render tumpukan tengah meja
│   │   └── button.py           # UI Button generik
│   └── assets/
│       ├── images/
│       │   ├── cards/
│       │   │   ├── ace.png
│       │   │   ├── king.png
│       │   │   ├── queen.png
│       │   │   ├── joker.png
│       │   │   └── card_back.png
│       │   ├── ui/
│       │   │   ├── revolver.png
│       │   │   ├── table_bg.png
│       │   │   └── logo.png
│       │   └── icons/
│       │       ├── ping_green.png
│       │       ├── ping_yellow.png
│       │       └── ping_red.png
│       ├── fonts/
│       │   └── game_font.ttf
│       └── sounds/
│           ├── gunshot.wav
│           ├── card_play.wav
│           ├── card_flip.wav
│           └── win.wav
│
├── shared/
│   ├── __init__.py
│   ├── constants.py            # Konstanta bersama (card types, phases, dll)
│   ├── packet_types.py         # Enum semua packet types
│   └── utils.py                # Fungsi utility (serialize/deserialize, dll)
│
├── data/
│   ├── rankings.json           # Data ranking pemain (bonus)
│   └── replays/                # File replay per match (bonus)
│
├── logs/
│   └── .gitkeep                # Log files akan dibuat di sini
│
├── tests/
│   ├── test_game_engine.py     # Unit test logika game
│   ├── test_packet_validator.py
│   └── test_roulette.py        # Test distribusi probabilitas roulette
│
├── requirements.txt
├── README.md
└── run_server.bat / run_server.sh
```

---

## 10. Desain UI / Layar (Screen Design)

### 10.1 Screen 1: Login Screen

```
┌─────────────────────────────────────────────────────┐
│                    🃏 LIAR'S DECK                    │
│                    ─────────────                     │
│                                                     │
│              Username: [___________]                │
│              Server IP: [___________]               │
│              Port:     [  12345   ]                 │
│                                                     │
│                  [ CONNECT ]                        │
│                                                     │
│              [ View Rankings ]  (bonus)             │
└─────────────────────────────────────────────────────┘
```

### 10.2 Screen 2: Lobby Screen

```
┌─────────────────────────────────────────────────────┐
│                 🔍 FINDING MATCH...                  │
│                                                     │
│         Welcome, Alice!                             │
│         Players online: 3                           │
│         Waiting in queue...                         │
│                                                     │
│         [●●●●●●●●●●] Searching...                   │
│                                                     │
│              [ CANCEL ]                             │
│                                                     │
│         Ping to server: 42 ms 🟢                    │
└─────────────────────────────────────────────────────┘
```

### 10.3 Screen 3: Game Screen (Main)

```
┌─────────────────────────────────────────────────────────────┐
│ Ping: 42ms 🟢              Round: 2          [🔇]            │
│─────────────────────────────────────────────────────────────│
│                                                             │
│  BOB ❤ ALIVE  [Pull: 1/6] ████████░░  Roulette: ~83%       │
│     ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐                               │
│     │▒▒│ │▒▒│ │▒▒│ │▒▒│ │▒▒│   ← opponent's hand (5 cards  │
│     └──┘ └──┘ └──┘ └──┘ └──┘     shown face-down)          │
│                                                             │
│         ═══════════════════════════════════                 │
│         TABLE CARD:  ♠ ACE                                  │
│         ─────────────────────────────────                   │
│         [Center Pile: 2 cards played]                       │
│              ┌──┐ ┌──┐                                      │
│              │▒▒│ │▒▒│   ← face-down pile                   │
│              └──┘ └──┘                                      │
│         ─────────────────────────────────                   │
│         Bob played 2 cards claiming "ACE"                   │
│         ═══════════════════════════════════                 │
│                                                             │
│  YOUR TURN! Select cards to play, or call LIAR              │
│     ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐                               │
│     │A ♠│ │K ♣│ │J 🃏│ │Q ♦│ │A ♥│   ← your hand           │
│     └──┘ └──┘ └──┘ └──┘ └──┘     (click to select)        │
│  ALICE ❤ ALIVE  [Pull: 0/6]                                 │
│                                                             │
│  [ PLAY SELECTED (2) ]     [ CALL LIAR! ]                   │
└─────────────────────────────────────────────────────────────┘
```

**Keterangan Elemen UI:**
- **Tangan lawan** ditampilkan di atas, face-down (hanya count yang terlihat).
- **Center pile** di tengah, face-down. Saat challenge, dibalik dengan animasi flip.
- **Tangan sendiri** di bawah, face-up. Klik kartu untuk memilih/deselect.
- **Roulette indicator** menampilkan berapa kali sudah pull dan odds saat ini.
- **Log teks** di tengah menampilkan aksi terakhir.
- Tombol **PLAY SELECTED** aktif jika ada kartu dipilih.
- Tombol **CALL LIAR** aktif jika ada kartu di center pile (ada aksi dari lawan).

### 10.4 Screen 4: Roulette Sequence Screen

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│         💀 ALICE MUST PLAY ROULETTE! 💀              │
│                                                      │
│              ╔═══════════════╗                       │
│              ║   [ 🔫 ]     ║                        │
│              ║  PULL: 1/6   ║                        │
│              ║ ODDS: 16.7%  ║                        │
│              ╚═══════════════╝                       │
│                                                      │
│     (spinning animation — chamber unknown)           │
│                                                      │
│              [ PULL THE TRIGGER ]                    │
│                                                      │
│    Reason: You were caught lying!                   │
└──────────────────────────────────────────────────────┘
```

Setelah trigger ditarik:
- **SURVIVED**: Efek klik, suara "click", screen shake ringan, kembali ke game.
- **DEAD**: Efek ledakan, suara "gunshot", animasi dramatic, game over.

### 10.5 Screen 5: Game Over Screen

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│            🏆 ALICE WINS! 🏆                         │
│                                                      │
│         Bob met his fate at the table.               │
│                                                      │
│   ┌─────────────┬──────────────────────────────┐    │
│   │             │ Alice        │ Bob            │    │
│   ├─────────────┼──────────────┼────────────────┤    │
│   │ Roulette    │ 2 survived   │ 3 survived, 1  │    │
│   │             │              │ DEAD           │    │
│   │ Times Lied  │ 3            │ 4              │    │
│   │ Times Honest│ 5            │ 3              │    │
│   └─────────────┴──────────────┴────────────────┘    │
│                                                      │
│        [ PLAY AGAIN ]     [ MAIN MENU ]             │
└──────────────────────────────────────────────────────┘
```

---

## 11. Desain Database / Penyimpanan Data

### 11.1 Penyimpanan Data (File-Based, tidak butuh DBMS)

Untuk kesederhanaan, data disimpan sebagai file JSON/log. Tidak perlu database penuh untuk proyek ini.

**`data/rankings.json`** (untuk fitur bonus ranking):
```json
{
  "last_updated": "2025-06-12T10:30:00",
  "leaderboard": [
    {
      "username": "Alice",
      "wins": 10,
      "losses": 5,
      "total_games": 15,
      "win_rate": 66.7,
      "roulette_survived": 28,
      "roulette_deaths": 5,
      "times_caught_lying": 5,
      "times_falsely_accused": 3,
      "elo_score": 1150
    }
  ]
}
```

**`logs/game_YYYYMMDD_HHMMSS.log`** (dibuat server untuk setiap sesi):
```
2025-06-12 10:23:01 | INFO | CONNECT | player=p001 | user=Alice | ip=127.0.0.1
...
```

**`data/replays/match_XXXXXXXX.json`** (untuk fitur bonus replay):
```json
{
  "match_id": "match_20250612",
  "duration_seconds": 180,
  "winner": "Alice",
  "events": [...]
}
```

---

## 12. Alur Program Lengkap (Flow Diagram)

### 12.1 Server Start Flow

```
python main_server.py
        │
        ▼
  Load config.py
        │
        ▼
  Init TCP Socket (bind + listen)
        │
        ▼
  Init LobbyManager, RoomManager, Logger
        │
        ▼
  ┌─────────────────────────────┐
  │     Accept loop             │
  │  while True:                │
  │    conn, addr = sock.accept │
  │    spawn Thread(conn, addr) │◀── setiap koneksi baru
  └─────────────────────────────┘
```

### 12.2 Per-Client Thread Flow

```
Thread(conn, addr)
        │
        ▼
  receive CONNECT packet
        │
        ├── [session_token ada] → handle_reconnect()
        │
        └── [baru] → buat PlayerState, kirim WELCOME
              │
              ▼
        receive JOIN_LOBBY
              │
              ▼
        lobby_manager.add(player)
              │
        ┌─────────────────────────────┐
        │ [antrian >= 2 pemain]        │
        │   create Room               │
        │   broadcast MATCH_FOUND     │
        │   start_game(room)          │
        └─────────────────────────────┘
              │
              ▼
        Game Loop (per player)
        while player.is_connected:
          packet = recv_packet(conn)
          if valid:
            process_action(packet, room)
            broadcast_state(room)
          else:
            log_invalid()
            send ERROR
```

### 12.3 Game Action Flow

```
Receive PLAY_CARDS from Player X
        │
        ▼
  packet_validator.validate()
        │
    ┌───┴───┐
  [Valid]  [Invalid]
    │          │
    │          └── send ERROR, log_invalid()
    ▼
  game_engine.apply_play(room, player, cards)
    - Hapus kartu dari hand player
    - Tambah ke center_pile
    - Update last_play
    - Set current_turn ke player berikut
        │
        ▼
  logger.log_play_cards(...)
        │
        ▼
  broadcast_state(room) ke semua
        │
        ▼
  send YOUR_TURN ke player berikutnya
```

---

## 13. Dependencies & Tech Stack

### 13.1 requirements.txt

```
pygame==2.5.2
# (semua library lain adalah stdlib Python)
```

> **Catatan:** Seluruh networking menggunakan `socket` dari stdlib. `threading` dan `json` juga stdlib. Tidak ada library network eksternal yang wajib.

**Library Opsional (Bonus):**
```
pyaudio==0.2.14         # voice communication (bonus)
sqlite3                 # ranking persistence (stdlib, bawaan Python)
```

### 13.2 Versi Python

- **Python 3.10+** (untuk `match` statement dan type hints modern)

### 13.3 Kompatibilitas Platform

| Platform | Status |
|---|---|
| Windows 10/11 | ✅ Didukung penuh |
| Ubuntu/Debian Linux | ✅ Didukung penuh |
| macOS 12+ | ✅ Didukung penuh |

### 13.4 Cara Menjalankan

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Jalankan server
cd liars_deck_online/
python server/main_server.py

# 3. Jalankan client (di mesin lain atau window baru)
python client/main_client.py
# Masukkan IP server dan username di layar login
```

---

## 14. Milestone Pengembangan

### Fase 1: Foundation (Minggu 1)
- [ ] Setup struktur folder dan file
- [ ] Implementasi `shared/constants.py` dan `shared/packet_types.py`
- [ ] Implementasi `server/config.py` dan `client/config.py`
- [ ] Implementasi `server/logger.py`
- [ ] Unit test: `test_game_engine.py` (deck, roulette)

### Fase 2: Core Networking (Minggu 2)
- [ ] Implementasi TCP socket server (`main_server.py`, `client_handler.py`)
- [ ] Implementasi TCP client (`network.py`, thread receive loop)
- [ ] Implementasi packet serialize/deserialize (`shared/utils.py`)
- [ ] Implementasi `packet_validator.py` (anti-invalid packet)
- [ ] Test koneksi dasar: connect, WELCOME, disconnect

### Fase 3: Game Logic & Matchmaking (Minggu 3)
- [ ] Implementasi `lobby_manager.py` (antrian + matchmaking)
- [ ] Implementasi `room_manager.py` (create/destroy room)
- [ ] Implementasi `game_engine.py` (deck, deal, play, liar, roulette)
- [ ] Implementasi `GAME_STATE_UPDATE` broadcast
- [ ] Test: full game flow server-side (2 client simulasi)

### Fase 4: Pygame UI (Minggu 4)
- [ ] Setup Pygame: window, font, color constants
- [ ] `screen_login.py` — input field, connect button
- [ ] `screen_lobby.py` — antrian, ping display
- [ ] `screen_game.py` — tangan kartu, center pile, aksi tombol
- [ ] `card_sprite.py` — render kartu face-up dan face-down
- [ ] `roulette_anim.py` — animasi roulette sequence
- [ ] `ping_display.py` — ping indicator dengan color coding

### Fase 5: Fitur Wajib Lanjutan (Minggu 5)
- [ ] Reconnect handling (server-side timer + client retry)
- [ ] Opponent disconnect UI feedback
- [ ] Ping/latency indicator live update
- [ ] `screen_gameover.py` — statistik akhir game
- [ ] Integration test: full game E2E dengan 2 client nyata

### Fase 6: Polish & Bonus (Minggu 6)
- [ ] Suara (card play, gunshot, win)
- [ ] Animasi kartu flip saat reveal
- [ ] Ranking system + leaderboard screen
- [ ] Spectator mode
- [ ] Match replay
- [ ] README dan dokumentasi
- [ ] Final testing & bug fix

---

## 15. Referensi

1. **Python Online Game Tutorial** — https://realpython.com/multiplayer-game-programming-async-io-pt1/  
2. **Multiple User Network Game in Python** — https://techwithtim.net/tutorials/python-online-game-tutorial/  
3. **Pygame Documentation** — https://www.pygame.org/docs/  
4. **Python socket Documentation** — https://docs.python.org/3/library/socket.html  
5. **Python threading Documentation** — https://docs.python.org/3/library/threading.html  
6. **Liar's Bar Game — Official Rules Reference** (sumber aturan game asli)  
7. **TCP vs UDP for Games** — https://gafferongames.com/post/udp_vs_tcp/  
8. **PodSixNet** — Python networking library untuk game: http://mccormick.cx/projects/PodSixNet/  
9. **JSON over TCP (Line-Delimited JSON)** — https://en.wikipedia.org/wiki/JSON_streaming  

---

> **Catatan Akhir:**  
> Dokumen ini bersifat *living document* — update sesuai perkembangan implementasi.  
> Semua fitur wajib (Real-time update, Game state synchronization, Reconnect handling, Ping/latency indicator, Logging aktivitas player, Anti-invalid packet sederhana) diprioritaskan terlebih dahulu sebelum mengerjakan fitur bonus.  
> 
> **Total estimasi baris kode:** ~2500–4000 baris Python (server + client + shared).  
> **Tingkat kesulitan:** Menengah-Tinggi (networking + game logic + UI).
