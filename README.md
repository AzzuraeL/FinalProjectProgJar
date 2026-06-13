# Bullet and Bluff Online (Liar's Deck)

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![GUI](https://img.shields.io/badge/GUI-Pygame-orange)
![Network](https://img.shields.io/badge/Network-Socket%20TCP-brightgreen)
![Status](https://img.shields.io/badge/Status-Completed-brightgreen)

Repositori ini berisi implementasi **Bullet and Bluff Online** (Liar's Deck), sebuah permainan kartu multiplayer online. Dokumentasi ini merinci spesifikasi fitur dan mendokumentasikan seluruh class serta fungsi Python dalam codebase.

---

## Daftar Isi

1. [Pemenuhan Persyaratan & Lokasi Implementasi](#-1-pemenuhan-persyaratan--lokasi-implementasi)
2. [Alasan Pemilihan Protokol TCP](#-2-alasan-pemilihan-protokol-tcp)
3. [Arsitektur Kode: Sisi Client (`client/`)](#-3-arsitektur-kode-sisi-client-client)
4. [Arsitektur Kode: Sisi Server (`server/`)](#-4-arsitektur-kode-sisi-server-server)
5. [Arsitektur Kode: Shared Utilities (`shared/`)](#-5-arsitektur-kode-shared-utilities-shared)
6. [Masalah yang Ditemukan & Solusi](#-6-masalah-yang-ditemukan--solusi)

---

## 1. Pemenuhan Persyaratan & Lokasi Implementasi

Berikut adalah rincian lokasi implementasi setiap ketentuan:

### Ketentuan Dasar
| Ketentuan | Lokasi File Terkait | Penjelasan Implementasi |
|-----------|----------------------|-------------------------|
| **Fokus Sinkronisasi Jaringan** | `server/game_engine.py`, `client/game_state.py` | Aplikasi menggunakan model *Server-Authoritative*. Server (`GameEngine`) menghitung kebenaran permainan dan mem-broadcast-nya melalui paket `S_GAME_STATE_UPDATE` yang dirender ulang oleh `GameState` klien. |
| **Minimal 2 Orang** | `server/lobby_manager.py` | Antrean di `LobbyManager` mendukung minimal 2 klien dan maksimal 4 klien. Jika belum mencapai 4 orang, timer menunggu hingga minimal 2 pemain terkumpul sebelum match dimulai. |
| **Room System** | `server/room_manager.py` | Fungsi `RoomManager.create_room` membuat objek `Room` ber-UUID unik dengan `GameEngine` tersendiri sehingga sesi tidak saling tumpang tindih. |
| **Matchmaking** | `server/lobby_manager.py` | Fungsi `LobbyManager.add_to_queue` memasukkan klien ke dalam `deque`, lalu `LobbyManager._check_loop` mengevaluasi dan memasangkan *match* secara otomatis. |
| **Protokol (TCP/UDP)** | `server/main_server.py`, `client/network.py` | Menggunakan `socket.SOCK_STREAM` dari standard library Python untuk koneksi TCP. |
| **Game Engine** | `client/main_client.py` dkk | Seluruh antarmuka dan visual kartu dirender menggunakan *Surface* dan *Blit* dari library `pygame`. |

### Fitur Wajib & Bonus
| Fitur Wajib | Lokasi File Terkait | Penjelasan Implementasi |
|-------------|----------------------|-------------------------|
| **Real-time Update** | `server/client_handler.py` | Setiap aksi klien diterima server dan langsung memicu `ClientHandler.broadcast_room`. |
| **Game State Sync** | `server/client_handler.py` | Pemanggilan `send_game_state()` merangkai paket JSON berisi status tumpukan kartu dan nyawa, kemudian `GameState.update_from_server` pada sisi klien memparsanya. |
| **Reconnect Handling** | `server/client_handler.py` | Setiap klien memiliki `session_token`. Saat koneksi terputus, server mempertahankan sesi selama 30 detik melalui `ClientHandler.reconnect_timeout()`. Jika klien kembali terhubung dan memanggil `_handle_reconnect()`, sesi sebelumnya dipulihkan. |
| **Ping Indicator** | `client/components/ping_display.py` | Komponen merender durasi waktu tempuh dari fungsi `PingDisplay.should_send_ping()` ke `PingDisplay.on_pong_received()`. |
| **Logging Player** | `server/logger.py` | Class `GameLogger` mencatat event seperti `log_connect()`, `log_liar_call()`, dan lainnya ke dalam file di direktori `/logs/`. |
| **Anti-Invalid Packet** | `server/packet_validator.py` | `RateLimiter.check()` menolak request yang melebihi batas frekuensi dari suatu IP, sementara `validate_packet()` memvalidasi struktur payload JSON. |
| **(Bonus) Dedicated Game Server** | `server/main_server.py` | Berjalan secara headless (tanpa UI), tidak bergantung pada klien, sehingga dapat di-deploy pada server cloud. |

---

## 2. Alasan Pemilihan Protokol TCP

**Protokol Utama:** TCP (Transmission Control Protocol)

Permainan *Liar's Deck* dirancang dengan siklus *turn-based* asinkron. Aspek terpenting dalam komputasinya adalah **urutan** dan **keabsahan** paket.

Jika menggunakan UDP (connectionless), ada risiko *packet loss* di mana aksi klien tidak diterima server, sehingga sesi game dapat terhenti karena status kedua pihak tidak sinkron. TCP mengatasi hal ini melalui **Guaranteed Delivery** dan pengurutan paket secara linear (jika 2 aksi dikirim dalam selang 0.1 detik, server memprosesnya secara berurutan). Overhead latensi TCP tidak menjadi masalah pada game berbasis giliran, di mana reliabilitas pengiriman lebih diprioritaskan daripada transmisi instan seperti pada UDP.

---

## 3. Arsitektur Kode: Sisi Client (`client/`)

Berikut adalah dokumentasi seluruh class dan fungsi dalam folder klien.

### Inti Aplikasi Client
**File: `client/config.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `get_custom_font` | Memuat file `.ttf` kustom dari direktori `assets/`. Jika file tidak ditemukan, fungsi melakukan *graceful fallback* ke font default Pygame untuk mencegah crash. |

**File: `client/game_state.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `GameState` | Class representasi status lokal klien atas kondisi server (jumlah kartu, nyawa, giliran, dan tipe kartu aktif di meja). |
| `__init__` | Menginisialisasi seluruh properti lokal dengan nilai `None` atau array kosong. |
| `reset` | Mengosongkan seluruh variabel untuk skenario klien keluar sesi dan memulai matchmaking baru. |
| `update_from_server` | Menerima `dict` state dari paket server dan memperbarui variabel internal lokal sebagai acuan validasi UI. |
| `is_my_turn` | Mengembalikan `True` jika `player_id` lokal sesuai dengan giliran yang sedang aktif. |
| `my_info` | Mencari dan mengembalikan data pemain lokal dari array `players` dalam state room. |
| `opponents` | Menyaring daftar pemain dengan mengecualikan pemain lokal, mengembalikan data lawan berupa nama dan jumlah kartu. |
| `opponent_username` | Mengekstrak nama lawan khusus untuk format tampilan duel 1v1 ("Vs [Nama Lawan]") di bagian atas layar. |
| `my_alive` | Memeriksa nilai integer HP; mengembalikan `True` jika nyawa masih > 0. Jika tidak, tombol aksi di UI dinonaktifkan. |
| `set_status` | Mengatur pesan notifikasi *flash* beserta timer pudar yang ditampilkan di tengah layar. |

**File: `client/main_client.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `LiarsDeckClient` | Class utama yang membungkus Pygame Display dan antarmuka transmisi socket. |
| `main` | Titik masuk `__main__` yang membuat instansi objek klien dan menjalankan loop utamanya. |
| `__init__` | Mengalokasikan kanvas Pygame window, menyiapkan frame-clock, serta mengatur status awal klien ke `STATE_LOGIN`. |
| `run` | Loop utama game (*while-loop*). Menetapkan FPS di 60, memproses event OS (Quit, Alt+F4), memperbarui input, dan memanggil render UI. |
| `toggle_fullscreen` | Mengalihkan mode display Pygame antara mode jendela dan *Borderless Fullscreen*. |
| `_handle_event` | Menerima event Mouse/Key dari Pygame dan meneruskan logikanya ke instansi layar yang sedang aktif (Lobby/Game). |
| `_do_connect` | Mengambil string IP dan port dari field input UI, kemudian menginisiasi koneksi TCP sinkron ke `NetworkClient`. |
| `_do_reconnect` | Mengambil kredensial sesi tersimpan (IP, port, player_id, session_token), menginisiasi koneksi TCP baru, dan mengirim paket `C_RECONNECT` alih-alih `C_CONNECT` untuk memulihkan sesi sebelumnya. |
| `_process_network` | Mengambil seluruh paket dari antrean `poll_packets()` dan memprosesnya. |
| `_route_packet` | Router paket yang mencocokkan tipe string JSON untuk mengeksekusi transisi logika secara otomatis (seperti memicu animasi roulette atau pergantian state ke GameOver). |
| `_update` | Meneruskan nilai *Delta-Time* dari siklus loop ke class layar yang aktif untuk keperluan kalkulasi animasi. |
| `_draw` | Mengosongkan frame setiap siklus dan mendelegasikan render ke class GUI yang aktif. |
| `_draw_error_overlay` | Menggambar overlay error semi-transparan berwarna merah di bagian bawah layar. |
| `_show_error` | Mengaktifkan overlay error dengan argumen string pesan yang diterima dari server. |

**File: `client/session_manager.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `save_session` | Menyimpan kredensial koneksi saat ini (player_id, session_token, username, IP, port) ke file JSON per-username di direktori `data/` agar klien dapat melakukan reconnect otomatis setelah crash atau penutupan mendadak. |
| `load_session` | Membaca file sesi tersimpan dari disk dan mengembalikan dict kredensial jika valid. Jika `username` diberikan, memuat file spesifik pengguna tersebut; jika tidak, memindai seluruh direktori sesi dan mengembalikan sesi terbaru berdasarkan `mtime` file. |
| `clear_session` | Menghapus file sesi dari disk, biasanya dipanggil saat pemain sengaja disconnect atau logout. Jika `username` diberikan, menghapus file spesifik pengguna tersebut beserta file legacy. |
| `_safe_username` | Membersihkan string username dari karakter non-alfanumerik untuk digunakan sebagai nama file yang aman, membatasi panjang maksimum 32 karakter. |
| `_session_path` | Menghasilkan path file sesi berdasarkan username: `data/session_<username>.json` jika username diberikan, atau `data/session.json` sebagai fallback legacy. |

**File: `client/network.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `NetworkClient` | Wrapper socket berbasis thread yang memisahkan eksekusi I/O TCP agar tidak memblokir frame rate Pygame. Menggunakan *generation counter* (`_generation`) untuk mengidentifikasi thread penerima yang sudah kedaluwarsa setelah reconnect. |
| `__init__` | Menginisialisasi struktur `Deque` thread-safe, referensi objek `socket`, dan generation counter `_generation`. |
| `is_connected` | Memeriksa flag koneksi untuk memastikan socket masih aktif dan valid. |
| `connect` | Menginisiasi koneksi TCP ke alamat IP server, menaikkan `_generation`, dan men-spawn daemon thread baru untuk membaca buffer secara asinkron. |
| `disconnect` | Menutup file descriptor socket secara bersih dan menaikkan `_generation` agar thread penerima lama berhenti memposting event `__DISCONNECTED__`. |
| `send_packet` | Menserialisasi dict Python ke JSON, mengonversinya ke byte ASCII dengan terminator `\n`, dan mengirimkannya melalui `sendall()`. |
| `_receive_loop` | Thread daemon yang membaca chunk secara kontinu, memisahkan payload berdasarkan karakter `\n`, dan mendeserialisasinya menjadi paket. Menerima parameter `gen` (generation); hanya memposting `__DISCONNECTED__` jika generation masih cocok dengan generation saat ini, mencegah thread lama mengganggu sesi baru. |
| `poll_packets` | Menguras dan mengembalikan seluruh isi antrean paket secara atomik untuk diproses oleh game loop. |

### Komponen GUI (`client/components/`)
**File: `client/components/button.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `Button` | Objek visual berbentuk persegi untuk kontrol klik di Pygame. |
| `get_button_image` | Static method yang membuat dan men-cache bitmap latar tombol untuk efisiensi rendering. |
| `__init__` | Menginisialisasi hit-box (`pygame.Rect`) pada koordinat X, Y berdasarkan ukuran teks yang diberikan. |
| `_get_font` | Mengambil font tebal kustom untuk teks tombol. |
| `draw` | Merender teks dan bitmap tombol, dengan deteksi hover berdasarkan posisi kursor mouse. |
| `is_clicked` | Mengembalikan `True` jika event `MOUSEBUTTONDOWN` terjadi di dalam area rektangular tombol. |
| `set_text` | Mengubah label tombol setelah inisialisasi (contoh: dari "Play" ke "Wait"). |
| `set_pos` | Memindahkan posisi X, Y tombol untuk penyesuaian tata letak setelah perubahan dimensi layar. |
| `center_x` | Menempatkan tombol pada posisi horizontal tengah berdasarkan lebar display. |

**File: `client/components/card_sprite.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `CardSprite` | Representasi visual satu kartu remi dalam tampilan grafis. |
| `_get_font` | Mengambil font tebal untuk merender angka nominal kartu. |
| `get_card_image` | Membuat dan men-cache bitmap kartu dengan warna dasar dan simbol suit (Spades/Hearts/dll.) sebagai aset statis. |
| `get_card_back_image` | Membuat dan men-cache bitmap sisi belakang kartu dengan pola kotak-kotak sebagai aset statis. |
| `__init__` | Mendefinisikan rank dan suit kartu, serta menginisialisasi y-offset untuk animasi hover. |
| `rect` | Getter yang mengembalikan `pygame.Rect` kartu berdasarkan posisi y-offset animasi saat ini. |
| `set_position` | Menerima koordinat awal penempatan kartu dari komponen induk. |
| `update_y` | Menginterpolasi posisi y kartu secara bertahap (delta-time dependent) saat properti `is_hovered` aktif. |
| `draw` | Memilih mode render berdasarkan flag `face-down`, dan menerapkan filter warna emas jika kartu berstatus `is_selected`. |
| `_draw_face_up` | Merender sisi depan kartu menggunakan operasi blit Pygame. |
| `_draw_face_down` | Merender sisi belakang kartu untuk menyembunyikan nilainya dari pemain lain. |
| `contains_point` | Memeriksa apakah titik koordinat `(x, y)` berada di dalam area hit-box kartu. |

**File: `client/components/center_pile.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `CenterPile` | Komponen visual yang menampilkan jumlah kartu dalam tumpukan tengah. |
| `__init__` | Menginisialisasi nilai hitungan awal (N=0). |
| `_get_font` | Menginisialisasi font untuk label "Cards in play". |
| `_get_badge_font` | Menginisialisasi font khusus untuk angka di dalam lencana bulat merah. |
| `set_position` | Menetapkan posisi elemen tumpukan pada area meja di layar game. |
| `set_count` | Memperbarui jumlah kartu yang ditampilkan sesuai data dari paket JSON server. |
| `draw` | Menggambar representasi visual tumpukan kartu beserta lencana merah penunjuk jumlah. |

**File: `client/components/hand_display.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `HandDisplay` | Manajer yang mengelola dan menampilkan kumpulan objek `CardSprite` dalam susunan kipas. |
| `__init__` | Menginisialisasi array kosong sebagai wadah objek `CardSprite`. |
| `set_cards` | Membaca list `(suit, rank)` dari luar dan mengonversinya secara massal menjadi objek `CardSprite`. |
| `set_facedown` | Mengatur semua kartu agar ditampilkan dalam posisi tertutup (face-down), umumnya digunakan saat pemain kehabisan nyawa. |
| `set_position` | Menetapkan batas rektangular area penampung kartu di bagian bawah layar. |
| `_layout` | Menghitung distribusi spasi antar kartu (*fanning algorithm*) agar tumpang tindih kartu terlihat natural saat jumlah kartu melebihi kapasitas layar. |
| `draw` | Merender setiap `CardSprite` dari kiri ke kanan sesuai urutan z-index. |
| `handle_click` | Mendeteksi klik pada kartu dengan hit-test dari layer teratas (kanan) ke kiri, kemudian mengubah status seleksi kartu yang terklik. |
| `get_selected_indices` | Mengembalikan daftar indeks kartu yang sedang terpilih untuk dikirim ke server. |
| `get_selected_cards` | Mengembalikan daftar dict `{"suit": "x", "rank": "y"}` dari kartu yang sedang terpilih. |
| `clear_selection` | Mereset status seleksi semua kartu menjadi tidak terpilih. |

**File: `client/components/ping_display.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `PingDisplay` | Komponen UI yang menampilkan latensi jaringan (ping) dalam milidetik. |
| `__init__` | Menginisialisasi nilai ping default 0 ms dan interval pengiriman ping pertama sebesar 2 detik. |
| `_get_font` | Mengambil font berukuran kecil tanpa serif untuk teks indikator ping. |
| `should_send_ping` | Mengembalikan `True` jika interval waktu antar pengiriman ping sudah terlewati, untuk mencegah pengiriman berlebih. |
| `on_pong_received` | Menghitung selisih waktu antara pengiriman ping dan penerimaan pong, kemudian menyimpannya sebagai nilai latensi dalam milidetik. |
| `draw` | Menampilkan nilai ping di sudut kiri atas layar; teks berubah warna menjadi merah jika latensi melebihi batas normal. |

**File: `client/components/roulette_anim.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `RouletteAnimation` | Komponen animasi visual revolver yang ditampilkan saat pemain yang tertangkap berbohong menerima penalti roulette. |
| `__init__` | Menginisialisasi batas kecepatan rotasi, konstanta perlambatan (*friction*), dan jumlah ruang silinder (1–6). |
| `_get_font` | Mengambil font untuk teks hasil akhir animasi ("BANG!" / "CLICK!"). |
| `start_spin` | Mengaktifkan animasi dengan mengatur state ke aktif dan menetapkan kecepatan rotasi awal. |
| `show_result` | Menerima hasil vonis dari payload JSON server dan menyimpannya untuk ditampilkan sebagai teks akhir animasi. |
| `is_active` | Mengembalikan `True` jika animasi masih berjalan atau fase fade-out belum selesai. |
| `reset` | Mereset seluruh variabel animasi (kecepatan, vonis, visibilitas) ke nilai awal. |
| `draw` | Memilih dan memanggil sub-rutin render yang sesuai berdasarkan state animasi: silinder berputar atau tampilan hasil akhir. |
| `_draw_spinning` | Merender efek silinder berputar dengan penurunan kecepatan bertahap dan *alpha-blending* untuk kesan blur. |
| `_draw_result` | Menampilkan teks hasil akhir ("BANG!" atau "CLICK!") dengan warna merah/hijau di tengah revolver yang berhenti. |
| `_draw_cylinder` | Menggambar silinder revolver berenam lubang secara prosedural menggunakan `pygame.draw.circle`, tanpa aset gambar eksternal. |

### Layar GUI Klien (`client/screens/`)
**File: `client/screens/screen_game.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `GameScreen` | Class utama yang mengelola tampilan layar permainan. Seluruh komponen (kartu, meja, tombol) diinisialisasi di dalamnya. |
| `__init__` | Menginisialisasi objek komponen dan menempatkan dua tombol utama ("Play Cards" & "Call Liar") pada koordinat kanvas yang ditetapkan. |
| `_get_font` | Mengambil font proporsional untuk teks di layar game. |
| `handle_event` | Menangkap event `pygame.MOUSEBUTTONDOWN` dan mencocokkan koordinat klik ke tombol internal. Jika cocok, membentuk `action_dict` yang diteruskan ke router socket sebagai perintah ke server (contoh: `{type: C_PLAY_CARDS}`). |
| `update` | Meneruskan nilai delta-time ke sistem animasi fade-out status, rotasi Roulette, dan pergerakan kartu tangan. |
| `draw` | Merender seluruh elemen layar secara berlapis dari latar belakang hingga elemen terdepan, dengan memanggil sub-fungsi render secara berurutan. |
| `_draw_opponents` | Menampilkan avatar dan jumlah kartu tersisa setiap lawan di bagian atas layar. |
| `_draw_table_card` | Menampilkan rank target ronde saat ini (contoh: "Must play Aces") sebagai teks di area meja. |
| `_draw_last_play` | Menampilkan informasi aksi terakhir (contoh: "Fulan played 2 Jacks") sebagai referensi bagi pemain untuk memutuskan apakah memanggil Liar. |
| `_draw_player_bar` | Menampilkan panel pemain lokal di sudut kanan bawah, berisi nama dan jumlah nyawa. |
| `_draw_turn_indicator` | Menampilkan border visual pada ikon pemain yang sedang mendapat giliran berdasarkan `current_turn_id`. |
| `_draw_status` | Menampilkan pesan status sementara (contoh: "It's your turn!") yang berangsur memudar seiring waktu. |
| `_draw_reveal` | Menampilkan kartu-kartu dari tumpukan tengah setelah seruan "Call Liar" agar semua pemain dapat melihat isinya. |
| `_draw_roulette_overlay` | Menerapkan filter peredupan layar dan merender `RouletteAnimation` di tengah sebagai overlay. |

**File: `client/screens/screen_gameover.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `GameOverScreen` | Layar akhir permainan yang menampilkan hasil dan statistik ketika HP pemain mencapai 0. |
| `__init__` | Mewarisi sisa `GameState` pasca pertandingan dan menginisialisasi dua tombol navigasi (Play Again dan Main Menu). |
| `_get_font` | Memuat font berukuran besar untuk teks pengumuman hasil ("YOU LOSE!" / "WINNER!"). |
| `handle_event` | Mendeteksi klik pada tombol menu dan meneruskan perintah perpindahan state ke manajer klien utama. |
| `draw` | Mengisi latar layar dengan warna hitam dan merender statistik permainan. |
| `_draw_stats` | Menampilkan statistik akhir dari data server: jumlah ronde yang dijalani dan sisa HP. |
| `_draw_particles` | Menampilkan efek partikel konfeti pada layar pemenang menggunakan titik-titik lingkaran Pygame. |

**File: `client/screens/screen_lobby.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `LobbyScreen` | Layar antrian yang ditampilkan saat menunggu server menemukan pemain lain untuk *matchmaking*. |
| `__init__` | Menginisialisasi tombol "Batal" untuk mengirim paket `C_LEAVE_LOBBY`. |
| `_get_font` | Mengambil font untuk teks "Waiting for match". |
| `handle_event` | Mendeteksi klik tombol "Cancel" dan memicu aksi *disconnect* dari sisi klien. |
| `draw` | Merender teks status, indikator ping, dan memanggil `_draw_spinner`. |
| `_draw_spinner` | Menggambar ikon loading berputar menggunakan kalkulasi sinus-kosinus untuk menunjukkan bahwa aplikasi aktif. |

**File: `client/screens/screen_login.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `_InputField` | Sub-class helper untuk field teks yang menangani input keyboard, kedipan kursor, rendering rektangular, dan operasi backspace. |
| `__init__` (InputField) | Menetapkan batas kotak dan placeholder teks abu-abu jika variabel teks kosong. |
| `handle_event` (InputField) | Memfilter event keyboard; menerima karakter alfanumerik dan titik, serta membatasi panjang input maksimum. |
| `draw` (InputField) | Merender kotak putih beserta teks input secara real-time. |
| `LoginScreen` | Layar login yang menyediakan input username dan alamat IP server, serta memicu koneksi TCP. |
| `__init__` (LoginScreen) | Menginisialisasi dua komponen `_InputField` untuk username dan alamat IP server. |
| `_get_font` s/d `_get_err_font` | Menyediakan font dalam berbagai ukuran (judul, sub-judul, dan pesan error) untuk layar login. |
| `_load_title_img` | Memuat aset gambar logo jika tersedia di direktori klien. |
| `handle_event` (LoginScreen) | Mendistribusikan event keyboard ke field input yang aktif, atau memicu koneksi saat tombol Enter/Connect ditekan. |
| `_try_connect` | Mengambil nilai dari field input, menetapkan port default (`8080`), dan meneruskan data koneksi ke `_do_connect` di *main_client*. |
| `_draw_bg_video` | Menampilkan efek partikel bergerak sebagai latar belakang animasi pada form login. |
| `draw` (LoginScreen) | Merender seluruh elemen layar: judul, field input aktif, tombol sambung, dan efek partikel latar. |
| `_draw_bg_motifs` | Menggambar elemen dekoratif geometris (segitiga/garis) sebagai bingkai visual layar login. |

**File: `client/screens/screen_menu.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `_RoomCodeField` | Komponen input internal untuk memasukkan kode room 6 karakter di layar menu, mendukung kursor berkedip dan validasi karakter alfanumerik. |
| `MenuScreen` | Layar menu utama yang ditampilkan setelah login. Menyediakan opsi quick matchmaking, membuat room privat, bergabung ke room berdasarkan kode, atau disconnect dari server. |
| `__init__` (MenuScreen) | Menyiapkan layout menu dengan tiga tombol aksi utama (Quick Match, Create Room, Join Room), field input kode room, dan tombol Disconnect. |
| `_load_title_img` | Memuat aset gambar judul dari direktori `assets/` dengan fallback jika file tidak ditemukan. |
| `handle_event` (MenuScreen) | Memproses klik mouse dan input keyboard pada layar menu, mengembalikan dict aksi yang sesuai (quick_match, create_room, join_room, atau disconnect). |
| `set_error` | Menampilkan pesan error di layar menu dengan timer fade-out selama 4 detik. |
| `draw` (MenuScreen) | Merender seluruh elemen layar menu: judul, info pengguna, indikator ping, tombol-tombol aksi, field input kode room, dan pesan error jika ada. |

**File: `client/screens/screen_room.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `RoomScreen` | Layar lobi room privat tempat pemain berkumpul sebelum memulai pertandingan. Menampilkan kode room, daftar pemain dengan indikator host, dan kontrol untuk memulai atau meninggalkan room. |
| `__init__` | Menyiapkan layout lobi room dengan tampilan info room, area daftar pemain, tombol Start Game (host only), dan tombol Leave Room. |
| `update_players` | Memperbarui daftar pemain dan penunjukan host saat server mengirim pembaruan keanggotaan room, menandai pemain yang merupakan host dengan bintang emas. |
| `handle_event` | Memproses klik mouse pada tombol lobi room, mengembalikan string aksi ('start_game' untuk host, 'leave_room' untuk semua pemain). |
| `draw` | Merender layar lobi room termasuk kotak kode room, panel daftar pemain dengan slot kosong, animasi menunggu, dan tombol aksi berdasarkan peran pemain (host atau bukan). |

---

## 4. Arsitektur Kode: Sisi Server (`server/`)

### Sistem Konektivitas
**File: `server/main_server.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `LiarsDeckServer` | Class utama server yang menginisialisasi komponen pengelola (*LobbyManager*, *RoomManager*, *GameLogger*, *RateLimiter*) dan membuka TCP socket listener. |
| `main` | Titik masuk command-line; membuat instansi server, menangani sinyal interupsi keyboard (`SIGINT/Ctrl+C`), dan menjalankan server. |
| `__init__` | Menyimpan konfigurasi IP:Port, menginisialisasi dictionary `SessionTokens` untuk klien yang terhubung secara konkuren, serta menyiapkan *Mutex-Lock* thread. |
| `start` | Menjalankan `socket.bind` dan `socket.listen`, kemudian memasuki loop tak terbatas yang menerima koneksi masuk via `socket.accept()` dan men-spawn `ClientHandler` baru per koneksi. |
| `start_match` | Dipanggil oleh LobbyManager saat match terbentuk. Membuat room baru via RoomManager, memperbarui sesi pemain, dan mengirim paket `S_MATCH_FOUND` kepada semua pemain terkait. |
| `shutdown` | Menutup server secara bersih: menutup socket server dan semua koneksi klien aktif untuk mencegah zombie socket. |
| `signal_handler` | Menangkap sinyal interupsi `Ctrl+C` dari OS dan meneruskannya ke metode `shutdown` untuk penghentian yang bersih. |

**File: `server/client_handler.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `ClientHandler` | Thread object yang mengelola siklus hidup satu koneksi klien secara eksklusif hingga koneksi terputus. |
| `__init__` | Menyimpan referensi ke komponen server (*LobbyManager*, *RoomManager*, *RateLimiter*, *GameLogger*), socket klien, dan `Player_ID`. |
| `send_packet` | Mengonversi dict Python ke string UTF-8, menambahkan terminator `\n`, dan mengirimnya ke klien via `sendall()`. |
| `send_to_opponent` | Mengirim paket ke semua pemain di room yang sama kecuali pengirim asli (untuk notifikasi seperti "Enemy Played a Card"). |
| `broadcast_room` | Mengirim paket ke seluruh pemain dalam room yang sama tanpa pengecualian. |
| `send_game_state` | Meminta rekonstruksi state dari GameEngine dengan data kartu lawan yang disembunyikan (`'hidden'`), lalu mengirimkannya secara eksklusif ke klien ini. |
| `send_your_turn` | Mengirim notifikasi giliran kepada pemain yang `Player_ID`-nya sesuai dengan `current_turn_id`, sehingga UI-nya dapat mengaktifkan input. |
| `run` | Loop penerima data utama. Membaca stream 1024-byte dari socket secara kontinu dan meneruskannya ke `_process_buffer`. |
| `_process_buffer` | Memisahkan buffer berdasarkan karakter `\n`, mendeserialisasi setiap segmen sebagai JSON, dan meneruskannya ke `_route_packet`. |
| `_route_packet` | Memeriksa field `type` pada paket, memvalidasi rate limit, lalu mendelegasikan ke handler yang sesuai. |
| `_handle_connect` | Memproses koneksi awal klien: menyimpan username, membuat `session_token`, dan mengirimkan respons sambutan. |
| `_handle_reconnect` | Memvalidasi `session_token` dari permintaan koneksi ulang, menutup socket handler lama, memperbarui referensi handler di `session` dan `room.players`, lalu memulihkan sesi pemain di room yang sebelumnya aktif dengan mengirim `S_RECONNECT_OK` dan `S_GAME_STATE_UPDATE`. |
| `_handle_join_lobby` | Mendaftarkan pemain ke antrean matchmaking `LobbyManager`. |
| `_handle_leave_lobby` | Menghapus pemain dari antrean `LobbyManager` ketika pemain menekan Cancel dari UI. |
| `_handle_play_cards` | Memvalidasi dan memproses aksi memainkan kartu: memverifikasi giliran, mengeksekusi aksi di GameEngine, dan mem-broadcast hasilnya. |
| `_handle_call_liar` | Memproses seruan "Call Liar": menghentikan alur giliran dan mendorong GameEngine untuk menjalankan `check_cards_truth()`. |
| `_handle_roulette_pull` | Meneruskan permintaan eksekusi roulette ke GameEngine dan mem-broadcast hasilnya (kena penalti atau selamat). |
| `_handle_ping` | Merespons paket `C_PING` dengan langsung mengirimkan `S_PONG` tanpa melibatkan GameEngine. |
| `_handle_chat` | Mendistribusikan pesan chat pemain ke seluruh anggota room. |
| `_handle_ready` | Menandai klien sebagai siap. Jika semua pemain di room sudah siap, GameEngine mendistribusikan kartu awal. |
| `_handle_create_room` | Membuat room privat baru dengan kode unik yang dapat dibagikan, menetapkan pemain sebagai host, dan mengirim `S_ROOM_CREATED`. |
| `_handle_join_room` | Bergabung ke room privat menggunakan kode room yang dibagikan host, memvalidasi kapasitas dan status room, lalu mengirim `S_ROOM_JOINED`. |
| `_handle_leave_room` | Menghapus pemain dari room berstatus WAITING, menotifikasi pemain tersisa, dan mengalihkan host jika diperlukan. |
| `_handle_start_room_game` | (Host only) Memulai pertandingan dari room WAITING: mengubah status room ke `IN_GAME`, membuat `GameEngine` baru, dan mendistribusikan state awal ke semua pemain. |
| `_start_match` | Mengasosiasikan handler ini ke room yang ditetapkan setelah matchmaking berhasil, menetapkan `room.status = 'IN_GAME'`, agar pengiriman paket tidak salah sasaran. |
| `_handle_disconnect` | Menangani pemutusan koneksi: menonaktifkan profil pemain, menutup buffer, mencatat kejadian ke log, dan memulai hitung mundur `reconnect_timeout`. Dilindungi pengecekan `is_superseded` agar handler lama yang sudah digantikan tidak merusak sesi baru. |
| `cleanup` | Menghapus token dan data pemain dari penyimpanan sesi server dan RateLimiter setelah timeout diskoneksi berakhir. |
| `reconnect_timeout` | Menunggu 30 detik setelah diskoneksi sebelum memanggil `forfeit()` pada GameEngine, memberikan waktu bagi pemain untuk reconnect. |

### Sistem Logika & Aturan
**File: `server/game_engine.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `PlayerState` | Struktur data in-memory yang menyimpan identitas, kartu di tangan, dan HP satu pemain. |
| `GameEngine` | Class inti yang mengelola seluruh logika permainan (aturan, distribusi kartu, giliran, dan validasi klaim) secara independen dari lapisan jaringan (*socket-agnostic*). |
| `__init__` | Menginisialisasi wadah data pemain, tumpukan kartu tengah (`center_pile`), rank target konstan di meja, dan pointer giliran. |
| `create_deck` | Membuat satu deck 52 kartu dari kombinasi suit dan rank, kemudian mengacak urutannya. |
| `deal_cards` | Mendistribusikan kartu dari deck ke masing-masing pemain sesuai jumlah yang ditentukan. |
| `choose_table_card` | Memilih rank target secara acak (contoh: '8', 'Jack', 'King') sebagai kartu yang harus dimainkan sepanjang ronde. |
| `current_turn_id` | Mengembalikan `Player_ID` pemain yang sedang mendapat giliran berdasarkan pointer urutan. |
| `_advance_turn` | Memajukan pointer giliran (+1) ke pemain berikutnya secara sirkular, melewati pemain dengan HP 0. |
| `play_cards` | Memindahkan kartu dari tangan pemain ke `center_pile`, memvalidasi giliran, dan menyimpan klaim kartu untuk verifikasi liar. |
| `call_liar` | Menghentikan siklus giliran dan memicu `check_cards_truth()` untuk memeriksa klaim kartu terakhir. |
| `check_cards_truth` | Memeriksa apakah kartu yang dimainkan sesuai dengan klaim. Jika semua kartu cocok, penantang dinyatakan salah; jika ada satu saja yang tidak cocok, pemain sebelumnya dinyatakan berbohong. |
| `pull_roulette` | Menentukan hasil roulette secara probabilistik dan mengurangi HP pemain yang terkena penalti. |
| `check_round_over` | Memeriksa jumlah pemain yang tersisa. Jika hanya satu yang bertahan, menetapkan status GameOver; jika tidak, mereset ronde. |
| `reset_round` | Mengosongkan `center_pile`, mengambil kembali kartu pemain, membuat deck baru, dan menentukan rank target baru untuk memulai ronde berikutnya. |
| `start_game` | Menginisialisasi state permainan: mengatur ronde ke satu, menonaktifkan roulette, menonaktifkan fase reinkarnasi, dan menjalankan `deal_cards()`. |
| `build_state_for_player` | Membangun objek state permainan yang disesuaikan untuk klien tertentu, dengan mengganti data kartu lawan menjadi `'hidden'` untuk mencegah kecurangan. Selama `PHASE_ROULETTE`, selalu menyertakan `roulette_state` berisi target pemain, nomor pull, jumlah ruang silinder, dan status selamat. |
| `get_winner` | Mengembalikan `Player_ID` pemain yang masih memiliki HP lebih dari 0 sebagai pemenang. |
| `get_loser` | Mengembalikan daftar pemain yang HP-nya sudah mencapai 0. |
| `set_player_connected` | Mengatur status koneksi pemain. Pemain yang terputus dilewati saat giliran berpindah untuk mencegah game terhenti. |
| `forfeit` | Menetapkan HP pemain menjadi 0 setelah timeout diskoneksi, sehingga pertandingan dapat dilanjutkan atau diakhiri. |

### Manajer Sistem Lainnya
**File: `server/lobby_manager.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `LobbyManager` | Mengelola antrean pemain yang mencari pertandingan dan mengelompokkan mereka saat jumlah memenuhi syarat. |
| `__init__` | Menginisialisasi struktur deque kosong dan menjalankan background thread untuk memantau kelayakan match melalui `_check_loop`. |
| `add_to_queue` | Menambahkan profil klien ke antrean beserta cap waktu masuk sebagai acuan FIFO dan penghitungan waktu tunggu. |
| `_pop_match` | Mengambil dan mengembalikan kelompok 2–4 profil dari bagian depan antrean untuk dijadikan satu match. |
| `_check_loop` | Loop permanen di background thread yang memeriksa kelayakan match secara berkala: jika ada 4 pemain, atau 2 pemain dengan waktu tunggu > 10 detik, match langsung dibentuk. |
| `remove_from_queue` | Menghapus pemain dari antrean saat pemain membatalkan pencarian match. |
| `queue_size` | Mengembalikan jumlah pemain yang saat ini berada dalam antrean. |
| `is_in_queue` | Memeriksa apakah pemain sudah terdaftar dalam antrean untuk mencegah duplikasi. |
| `get_wait_time_remaining` | Mengembalikan sisa waktu tunggu sebelum match dipaksa dibentuk, berdasarkan waktu masuk pemain paling lama dalam antrean. |
| `stop` | Menghentikan background thread matchmaking dengan mengubah flag loop menjadi `False`, memungkinkan server shutdown dengan aman. |

**File: `server/room_manager.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `Room` | Struktur data yang menyimpan instansi `GameEngine` dan daftar `Client ID` untuk satu sesi pertandingan yang terisolasi. |
| `RoomManager` | Mengelola registrasi dan pencarian `Room` aktif melalui kamus berbasis UUID, menjadi titik referensi bagi handler socket. Mendukung room privat dengan kode dan matchmaking otomatis. |
| `__init__` | Menginisialisasi kamus kosong sebagai penyimpan data room dan peta `_player_room_map` untuk pencarian room berdasarkan player ID secara O(1). |
| `create_room` | Membuat room baru dari daftar pemain matchmaking dengan UUID unik, menginisialisasi `GameEngine` baru, mendaftarkan pemain ke dalamnya, dan menyimpannya di kamus RoomManager. |
| `create_private_room` | Membuat room privat dengan kode unik yang dapat dibagikan (contoh: "ABC123"). Hanya host yang ditambahkan secara awal; pemain lain bergabung melalui kode room. Room berstatus `WAITING` hingga host memulai game. |
| `get_room_by_code` | Mencari room berdasarkan kode room secara case-insensitive, digunakan saat pemain memasukkan kode untuk bergabung ke room privat. |
| `add_player_to_room` | Menambahkan pemain ke room WAITING yang sudah ada setelah memvalidasi kapasitas dan status room. |
| `remove_player_from_room` | Menghapus pemain dari room. Menghapus room jika kosong. Mengalihkan host jika pemain yang keluar adalah host saat ini. |
| `get_room_players` | Mengembalikan daftar informasi pemain (player_id, username) untuk seluruh pemain di room tertentu. |
| `remove_room` | Menghapus room dari kamus setelah pertandingan selesai untuk membebaskan memori. |
| `get_room` | Mengembalikan objek `Room` berdasarkan UUID yang diberikan oleh handler klien. |
| `get_room_by_player` | Mencari room berdasarkan `Player_ID` melalui `_player_room_map` tanpa mengetahui UUID room, berguna saat pemain reconnect tanpa informasi room. |
| `room_count` | Mengembalikan jumlah room yang sedang aktif sebagai indikator beban server. |
| `all_rooms` | Mengembalikan iterator atas semua room aktif untuk keperluan monitoring dan logging. |

**File: `server/packet_validator.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `validate_packet` | Memvalidasi struktur paket JSON masuk: mengembalikan `False` jika field `type` tidak ada atau tipe propertinya tidak sesuai. |
| `RateLimiter` | Middleware keamanan yang melacak frekuensi request per `Player_ID` menggunakan cap waktu, untuk membatasi pengiriman paket berlebih. |
| `__init__` | Menetapkan batas `requests_per_second` yang diizinkan per koneksi dan menginisialisasi kamus pelacak. |
| `check` | Membandingkan cap waktu terkini dengan riwayat request pemain. Mengembalikan `False` jika frekuensi request melebihi batas yang ditetapkan. |
| `remove_player` | Menghapus data pelacak pemain dari kamus setelah koneksi terputus. |

**File: `server/logger.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `GameLogger` | Class logging sentral yang mencetak dan menyimpan aktivitas server ke file `.log` dengan stempel waktu OS. |
| `__init__` | Membuat direktori `/logs` jika belum ada, kemudian menginisialisasi file log dengan nama berdasarkan waktu. |
| `log_connect` | Mencatat event koneksi baru beserta alamat IP dan `Player_ID` yang diberikan. |
| `log_disconnect` | Mencatat event pemutusan koneksi beserta penyebabnya (Normal Quit, Force Close, atau error socket). |
| `log_play_cards` | Mencatat aksi pemain memainkan kartu beserta klaim nominalnya. |
| `log_liar_call` | Mencatat event seruan "Call Liar" beserta identitas pemain yang menantang. |
| `log_reveal` | Mencatat hasil verifikasi kartu setelah "Call Liar": apakah klaim pemain terbukti jujur atau berbohong. |
| `log_roulette` | Mencatat hasil putaran roulette: pemain selamat atau terkena penalti. |
| `log_game_over` | Mencatat akhir pertandingan beserta `Player_ID` pemenang. |
| `log_invalid_packet` | Mencatat paket tidak valid yang diterima beserta tipe kesalahan strukturnya. |
| `log_info` | Mencetak pesan informasi umum ke stdout. |
| `log_error` | Mencetak pesan error ke stderr saat terjadi kesalahan kritis (contoh: socket error). |
| `log_debug` | Mencetak pesan debug yang hanya aktif di lingkungan pengembangan. |

---

## 5. Arsitektur Kode: Shared Utilities (`shared/`)

Modul utilitas bersama yang digunakan oleh klien maupun server untuk menyeragamkan konstanta, tipe paket, dan fungsi bantu.

**File: `shared/constants.py`**
*(Hanya Variabel Konstanta)*
| Referensi / Enumerasi | Deskripsi |
|----------------------|-----------|
| Variabel Konstanta (e.g. `PHASE_GAME_OVER`) | Mendefinisikan konstanta label status (fase permainan, jenis kartu, kapasitas silinder). Menyeragamkan nilai antara klien dan server untuk mencegah kesalahan akibat *typo* pada komparasi string. |

**File: `shared/packet_types.py`**
*(Hanya Variabel Konstanta)*
| Referensi / Enumerasi | Deskripsi |
|----------------------|-----------|
| `C_CONNECT`, `S_MATCH_FOUND`, dll. | Mendefinisikan konstanta tipe paket untuk sistem routing JSON. Prefiks `C_` menandakan paket dari klien ke server, prefiks `S_` menandakan paket dari server ke klien. |

**File: `shared/utils.py`**
| Class / Fungsi | Deskripsi |
|----------------|-----------|
| `serialize` | Mengonversi dict Python menjadi string JSON tanpa spasi, kemudian mengodekannya sebagai bytes UTF-8 untuk dikirim melalui TCP socket. |
| `deserialize` | Mendekode bytes dari socket menjadi string Unicode, kemudian mengurainya kembali ke dict Python. Mengembalikan `None` jika data tidak valid. |
| `generate_id` | Menghasilkan string ID unik menggunakan UUID v4 berbasis `os.urandom` untuk menghindari tabrakan nama room di server. |
| `generate_session_token` | Menghasilkan token string hexadecimal 32 karakter yang aman secara kriptografis, digunakan sebagai identitas sesi klien untuk keperluan reconnect. |

---

## 6. Masalah yang Ditemukan & Solusi

Selama pengembangan dan pengujian fitur reconnect serta room system, ditemukan beberapa bug kritis yang menyebabkan kegagalan koneksi, tampilan tidak sinkron, dan fase permainan yang macet. Setiap masalah di bawah didokumentasikan secara lengkap mulai dari gejala yang terlihat oleh pengguna, urutan kejadian teknis secara kronologis, analisis akar penyebab mendalam, hingga solusi final beserta kode implementasinya.

---

### Masalah 1: Tabrakan File Sesi Antar Instance Klien (Session File Collision)

**Lokasi File yang Terdampak:** `client/session_manager.py`, `client/screens/screen_login.py`

#### Gejala

Saat menjalankan dua instance klien Pygame dari folder proyek yang sama pada satu perangkat (misalnya untuk menguji permainan 2 pemain secara lokal), pemain yang melakukan reconnect selalu masuk menggunakan identitas pemain lain. Tampilan layar game pemain B tiba-tiba digantikan oleh sesi pemain A, dan sebaliknya. Bug ini hanya muncul ketika kedua klien dijalankan dari direktori yang sama — klien dari folder atau perangkat berbeda tidak terpengaruh.

#### Kronologi Kejadian

1. Pemain A (username: `"bagus"`) menjalankan klien dari folder `D:\FPPROGJAR` dan terhubung ke server. Server memberikan `player_id = "aaa111"` dan `session_token = "token_a"`.
2. Klien A memanggil `save_session("aaa111", "token_a", "bagus", "127.0.0.1", 12345)` yang menulis file `data/session.json`:
   ```json
   {"player_id": "aaa111", "session_token": "token_a", "username": "bagus", "ip": "127.0.0.1", "port": 12345}
   ```
3. Pemain B (username: `"verya"`) menjalankan instance klien kedua dari folder yang sama `D:\FPPROGJAR`. Klien B terhubung dan mendapat `player_id = "bbb222"` dan `session_token = "token_b"`.
4. Klien B memanggil `save_session("bbb222", "token_b", "verya", "127.0.0.1", 12345)` yang **menimpa** file `data/session.json` yang sama:
   ```json
   {"player_id": "bbb222", "session_token": "token_b", "username": "verya", "ip": "127.0.0.1", "port": 12345}
   ```
5. Pemain A disconnect. Layar login klien A muncul kembali.
6. Pemain A menekan tombol **Reconnect** di layar login. Fungsi `_try_reconnect()` memanggil `load_session()` tanpa parameter username, yang membaca file `data/session.json` — tetapi file tersebut sekarang berisi **kredensial pemain B** (`"bbb222"`, `"token_b"`, `"verya"`).
7. Klien A mengirim `C_RECONNECT` dengan `player_id = "bbb222"` dan `session_token = "token_b"` ke server. Server memvalidasi token cocok, dan klien A kini masuk sebagai pemain B.
8. Akibatnya: tampilan game pemain B diambil alih oleh klien A. Pemain B kehilangan kendali atas sesinya.

#### Akar Penyebab

Desain awal menggunakan satu file sesi global (`data/session.json`) untuk seluruh instance klien yang berjalan dari direktori yang sama. Tidak ada mekanisme isolasi berdasarkan identitas pemain. Karena kedua klien berbagi *filesystem* yang sama, penulisan sesi oleh satu klien selalu menimpa sesi klien lain. Ini adalah bentuk klasik dari *race condition* pada shared resource tanpa locking.

#### Solusi

Menerapkan skema **file sesi per-username** sehingga setiap pemain memiliki file sesi independen yang tidak dapat ditimpa oleh pemain lain:

**Perubahan di `client/session_manager.py`:**

Fungsi `_safe_username()` membersihkan username agar aman digunakan sebagai bagian dari nama file:
```python
def _safe_username(username: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9_-]', '_', (username or 'player').strip() or 'player')
    return cleaned[:32]
```

Fungsi `_session_path()` menghasilkan path file unik per pemain:
```python
def _session_path(username: str | None = None) -> str:
    if not username:
        return DEFAULT_SESSION_FILE          # data/session.json (legacy fallback)
    return os.path.join(SESSION_DIR, f'session_{_safe_username(username)}.json')
    # Contoh: data/session_bagus.json, data/session_verya.json
```

`save_session()` kini menulis ke file per-username:
```python
def save_session(player_id, session_token, username, ip, port):
    path = _session_path(username)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
```

`load_session(username)` memuat file spesifik jika username diberikan, atau memindai seluruh direktori sesi dan mengembalikan yang paling baru (berdasarkan `mtime`) jika tidak:
```python
def load_session(username=None):
    if username:
        path = _session_path(username)
        # Hanya baca file milik username ini
    else:
        # Scan seluruh data/session_*.json, kembalikan yang paling baru
```

`clear_session(username)` menghapus file spesifik pemain beserta file legacy:
```python
def clear_session(username=None):
    path = _session_path(username)
    os.remove(path)                    # Hapus file per-username
    if username:
        os.remove(DEFAULT_SESSION_FILE)  # Hapus juga legacy jika ada
```

**Perubahan di `client/screens/screen_login.py`:**

- Field username di-pre-fill dari sesi tersimpan terbaru agar pemain tidak perlu mengetik ulang.
- Tombol **Reconnect** hanya aktif jika field username tidak kosong, mencegah `load_session()` tanpa parameter yang bisa memuat sesi pemain lain.
- Label "Previous session" di bawah tombol Reconnect menampilkan informasi dinamis: `"Previous session: bagus @ 127.0.0.1:12345"` yang berubah sesuai username yang sedang diketik di field input.

**Hasil:** Setelah perbaikan, dua instance klien dari folder yang sama dapat berjalan berdampingan tanpa saling mengganggu. Klien A menyimpan sesi ke `data/session_bagus.json` dan klien B menyimpan sesi ke `data/session_verya.json`. Tombol Reconnect di klien A hanya akan memuat `data/session_bagus.json`, tidak pernah memuat sesi klien B.

---

### Masalah 2: Paket `__DISCONNECTED__` dari Thread Lama Menghentikan Sesi Reconnect

**Lokasi File yang Terdampak:** `client/network.py`, `client/main_client.py`

#### Gejala

Setelah pemain berhasil reconnect (server mengirim `S_RECONNECT_OK` dan `S_GAME_STATE_UPDATE`), klien seharusnya langsung masuk ke layar game. Sebaliknya, klien justru kembali ke layar login dengan pesan "Disconnected from server". Log konsol klien menunjukkan urutan yang tidak masuk akal:
```
[RECONNECT] OK state=menu phase='playing' pid=3a88fd4e6f20
[DISCONNECTED] grace_active=False still_connected=False state=menu
```
Paket `__DISCONNECTED__` diproses beberapa milidetik setelah `S_RECONNECT_OK` diterima, meruntuhkan seluruh state yang baru saja dipulihkan.

#### Kronologi Kejadian

1. Pemain terhubung ke server melalui koneksi TCP pertama. `NetworkClient.connect()` men-spawn **Thread-A** (`_receive_loop`) yang membaca data dari socket secara kontinu di background.
2. Koneksi TCP terputus (kabel jaringan lepas, Wi-Fi terputus, atau pemain menutup laptop). Socket pada Thread-A mengalami `OSError` saat `recv()` dipanggil.
3. Thread-A mendeteksi socket terputus dan mulai mengeksekusi logika akhir: mengatur `self._connected = False` dan memposting `{'type': '__DISCONNECTED__'}` ke inbox queue.
4. Game loop utama memproses `__DISCONNECTED__`, mereset state ke `STATE_LOGIN`, dan menampilkan layar login.
5. Pemain menekan **Reconnect**. `NetworkClient.connect()` dipanggil lagi, membuat koneksi TCP **baru** dan men-spawn **Thread-B** (`_receive_loop` baru).
6. Server menerima `C_RECONNECT`, memvalidasi token, dan mengirim `S_RECONNECT_OK`. Thread-B menerima paket ini dan memasukkannya ke inbox.
7. Game loop memproses `S_RECONNECT_OK`, menetapkan state ke `STATE_MENU`, dan membuka grace window.
8. **Di sinilah bug terjadi:** Thread-A dari langkah 2–3 ternyata belum selesai mengeksekusi logika akhirnya. Karena penundaan penjadwalan thread OS, Thread-A baru sekarang menyelesaikan eksekusinya dan memposting `__DISCONNECTED__` ke inbox — tepat setelah `S_RECONNECT_OK` diproses.
9. Game loop memproses `__DISCONNECTED__` dari Thread-A ini, mereset seluruh state, dan mengembalikan klien ke layar login.

Secara visual, ini terlihat seperti:
```
Thread-A (lama):    [socket mati] ........... [posting __DISCONNECTED__] ← terlambat!
Thread-B (baru):    [kirim C_RECONNECT] → [terima S_RECONNECT_OK]
Game Loop:          [proses RECONNECT_OK ✓] → [proses DISCONNECTED ✗] → reset ke login!
```

#### Akar Penyebab

Arsitektur thread penerima (`_receive_loop`) tidak memiliki mekanisme untuk membedakan apakah dirinya masih relevan atau sudah kedaluwarsa. Setiap thread yang mendeteksi socket terputus akan secara unconditional memposting `__DISCONNECTED__` ke inbox, tanpa memeriksa apakah koneksi baru sudah terbentuk. Dengan adanya delay penjadwalan thread di level OS, thread lama bisa menyelesaikan eksekusinya kapan saja — bahkan setelah sesi baru sudah berjalan.

#### Solusi

**Penerapan Generation Counter Pattern di `client/network.py`:**

Setiap koneksi baru diberi "generasi" unik berupa angka yang naik secara monoton. Thread penerima membawa salinan generasi saat ia dimulai, dan hanya boleh memposting event diskoneksi jika generasinya masih cocok dengan generasi aktif:

```python
class NetworkClient:
    def __init__(self):
        self._generation = 0       # Counter generasi koneksi
        # ...

    def connect(self, ip, port):
        self._generation += 1      # Naikkan generasi untuk koneksi baru
        gen = self._generation     # Thread baru membawa salinan generasi ini
        # ... buat socket, spawn thread ...
        thread = threading.Thread(target=self._receive_loop, args=(gen,), daemon=True)
        thread.start()

    def disconnect(self):
        self._generation += 1      # Naikkan generasi agar thread lama berhenti
        # ... tutup socket ...

    def _receive_loop(self, gen: int):
        while True:
            # ... baca data dari socket ...
            if not chunk:  # socket terputus
                break
            # ... parse paket ...

        # Di akhir thread, sebelum memposting __DISCONNECTED__:
        with self._lock:
            still_current = (self._generation == gen)  # Apakah saya masih thread aktif?
            if still_current:
                self._connected = False
        if still_current:
            self.inbox.put({'type': '__DISCONNECTED__'})  # Hanya jika masih current
        # Jika tidak current (generasi sudah naik), thread diam-diam berakhir
```

Dengan pola ini, ketika Thread-B dimulai dengan generasi = 2, Thread-A yang membawa generasi = 1 akan memeriksa `self._generation == 1` → `False`, sehingga **tidak memposting `__DISCONNECTED__`**.

**Penerapan Reconnect Grace Window di `client/main_client.py`:**

Sebagai lapisan pertahanan tambahan (defense in depth), ditambahkan grace window selama 3 detik setelah `S_RECONNECT_OK` diterima. Selama jendela ini, setiap paket `__DISCONNECTED__` yang masuk akan diabaikan:

```python
# Saat S_RECONNECT_OK diterima:
elif ptype == S_RECONNECT_OK:
    self._reconnect_grace_until = time.time() + 3.0  # Grace window 3 detik
    self.state = STATE_MENU
    # ... simpan sesi, buat menu screen ...

# Saat __DISCONNECTED__ diterima:
if ptype == '__DISCONNECTED__':
    grace_active = time.time() < self._reconnect_grace_until
    still_connected = self.net.is_connected
    if grace_active:
        return   # Abaikan — kita sedang dalam periode grace setelah reconnect
    if still_connected:
        return   # Abaikan — socket masih terhubung, ini false alarm
    # Baru proses disconnect secara normal
    self.state = STATE_LOGIN
    self.gs.reset()
```

**Hasil:** Setelah perbaikan, thread penerima lama tidak lagi dapat mengganggu sesi baru. Bahkan jika thread lama berhasil memposting `__DISCONNECTED__` (misalnya karena race condition yang sangat sempit), grace window akan menangkap dan mengabaikannya. Reconnect kini berjalan mulus tanpa gangguan.

---

### Masalah 3: Room Tidak Ditemukan Saat Reconnect Karena Status Room Tidak Diatur (`RECONN_NO_ROOM`)

**Lokasi File yang Terdampak:** `server/client_handler.py` (`_start_match`), `server/main_server.py` (`start_match`)

#### Gejala

Pemain yang disconnect di tengah pertandingan aktif dan mencoba reconnect dalam batas waktu 60 detik menerima pesan error "Room not found" atau "Session expired" di klien. Di sisi server, log menunjukkan:
```
[2026-06-14 05:25:30] INFO     RECONN   player=3a88fd4e6f20 user=bagus
[2026-06-14 05:25:30] INFO     RECONN_NO_ROOM player=3a88fd4e6f20
```
Padahal room seharusnya masih aktif karena pemain lain masih bermain. Ketika pemain yang tidak disconnect memeriksa log server-nya, terlihat bahwa room pernah dibuat tetapi kemudian dihapus karena handler disconnect menganggap room tersebut masih dalam fase WAITING.

#### Kronologi Kejadian

1. Pemain A dan Pemain B masuk ke antrean matchmaking (quick match). `LobbyManager` mengumpulkan cukup pemain dan memanggil `_start_match(player_list)`.
2. `_start_match` memanggil `self.rooms.create_room(player_list)` yang membuat objek `Room` baru. Secara default, konstruktor `Room` dataclass menetapkan `status = 'WAITING'`:
   ```python
   @dataclass
   class Room:
       room_id: str
       players: dict
       game_engine: GameEngine
       status: str = 'WAITING'    # ← Default status
   ```
3. `_start_match` melanjutkan dengan memanggil `room.game_engine.start_game()` yang mengubah `engine.phase` menjadi `PHASE_PLAYING`. Namun, **`room.status` tidak pernah diubah** dari `'WAITING'`. Ini adalah bug — ada dua konsep "status" yang berbeda:
   - `engine.phase` = fase internal game engine (PLAYING, ROULETTE, GAME_OVER)
   - `room.status` = status room di level RoomManager (WAITING, IN_GAME)
4. Pertandingan berjalan normal. Kedua pemain bermain beberapa ronde.
5. Pemain A kehilangan koneksi jaringan. `_handle_disconnect()` dipanggil di thread ClientHandler pemain A.
6. Handler disconnect memeriksa apakah pemain berada di room berstatus WAITING (yang berarti belum mulai bermain dan boleh dikeluarkan):
   ```python
   waiting_room = self.rooms.get_room_by_player(self.player_id)
   if waiting_room and waiting_room.status == 'WAITING':  # ← Kondisi ini True!
       self.rooms.remove_player_from_room(waiting_room.room_id, self.player_id)
   ```
7. Karena `room.status` masih `'WAITING'` (tidak pernah diubah ke `'IN_GAME'`), kondisi ini bernilai `True`. Handler disconnect **mengeluarkan pemain A dari room** dan menghapus room jika kosong.
8. Ketika pemain A mencoba reconnect, `get_room_by_player(self.player_id)` mengembalikan `None` karena pemain A sudah dikeluarkan dari room. Server mengirim `RECONN_NO_ROOM`.

Diagram alur yang menunjukkan bug:
```
_start_match():
  room = create_room(players)     ← room.status = 'WAITING' (default)
  engine.start_game()             ← engine.phase = 'PHASE_PLAYING'
  [TIDAK ADA: room.status = 'IN_GAME']  ← BUG: baris ini hilang!

_handle_disconnect() [dipanggil saat pemain disconnect]:
  room = get_room_by_player(pid)  ← room ditemukan
  if room.status == 'WAITING':    ← True! (seharusnya 'IN_GAME')
      remove_player_from_room()   ← Pemain dikeluarkan dari room aktif!
```

#### Akar Penyebab

Ketidakkonsistenan antara `engine.phase` (yang benar berubah ke `PHASE_PLAYING`) dan `room.status` (yang tetap `'WAITING'`). Fungsi `_start_match` berhasil mengatur fase game engine tetapi lupa mengatur status room di level RoomManager. Handler disconnect menggunakan `room.status` sebagai indikator apakah room masih dalam fase menunggu (boleh dikeluarkan) atau sudah bermain (jangan dikeluarkan), sehingga membuat keputusan yang salah.

#### Solusi

Menambahkan satu baris `room.status = 'IN_GAME'` segera setelah `create_room()` berhasil di **kedua lokasi** kode yang membuat room:

**Di `server/client_handler.py` — fungsi `_start_match`:**
```python
def _start_match(self, player_list):
    room = self.rooms.create_room(player_list)
    if not room:
        for p in player_list:
            h = p.get('handler')
            if h:
                h.send_packet({'type': S_ERROR, 'message': 'Server full'})
        return
    room.status = 'IN_GAME'    # ← BARIS YANG DITAMBAHKAN
    # ... lanjutkan inisialisasi session, start_game, dll ...
```

**Di `server/main_server.py` — fungsi `start_match`:**
```python
def start_match(self, player_list):
    room = self.rooms.create_room(player_list)
    if not room:
        return
    room.status = 'IN_GAME'    # ← BARIS YANG DITAMBAHKAN (sinkron dengan client_handler)
    # ... lanjutkan inisialisasi ...
```

Perbaikan yang sama juga diterapkan di `_handle_start_room_game` (untuk room privat yang dimulai oleh host):
```python
def _handle_start_room_game(self, packet):
    room.status = 'IN_GAME'    # ← Sudah ada di kode ini
    # ... buat GameEngine baru, start_game, dll ...
```

**Verifikasi:** Setelah perbaikan, handler disconnect memeriksa `room.status == 'WAITING'` dan mendapatkan `False` (karena status sudah `'IN_GAME'`), sehingga pemain tidak dikeluarkan dari room saat disconnect. Saat reconnect, `get_room_by_player()` berhasil menemukan room dan server mengirim `S_GAME_STATE_UPDATE` untuk memulihkan state permainan.

---

### Masalah 4: Referensi Handler Kedaluwarsa di `room.players` Menyebabkan Seluruh Broadcast Paket Hilang Pasca-Reconnect

**Lokasi File yang Terdampak:** `server/client_handler.py` (`_handle_reconnect`)

#### Gejala

Setelah pemain berhasil reconnect dan masuk kembali ke game, permainan tampaknya berjalan normal — pemain dapat melihat kartunya dan bermain seperti biasa. Namun, ketika lawan memanggil "Call Liar" dan server memasuki fase ROULETTE, pemain yang baru reconnect **tidak melihat overlay roulette** maupun tombol PULL TRIGGER. Layar game tetap menampilkan fase PLAYING biasa. Pemain tersebut bahkan terus mengirim paket `PLAY_CARDS` yang ditolak server dengan error "Cannot play cards in phase ROULETTE".

Log server menunjukkan:
```
[2026-06-14 05:25:44] INFO     LIAR     room=1e6c3b5ad025 caller=28599fbaf122 target=3a88fd4e6f20
[2026-06-14 05:25:44] INFO     REVEAL   room=1e6c3b5ad025 player=3a88fd4e6f20 cards=['ACE'] lying=True
[2026-06-14 05:25:53] WARNING  INVALID  player=3a88fd4e6f20 reason=Cannot play cards in phase ROULETTE (×4)
```

Server berhasil memproses LIAR, menjalankan REVEAL, dan memasuki ROULETTE. Server juga mem-broadcast semua paket transisi (`S_LIAR_CALLED`, `S_REVEAL_CARDS`, `S_ROULETTE_START`, `S_GAME_STATE_UPDATE`) ke semua pemain di room. Namun, pemain `3a88fd4e6f20` (pemain yang baru reconnect) tidak pernah menerima paket-paket tersebut — buktinya ia masih mengirim `PLAY_CARDS` 9 detik kemudian, yang hanya mungkin dilakukan jika klien masih berpikir fase game adalah `PHASE_PLAYING`.

#### Kronologi Kejadian

**Fase 1 — Pembuatan Room (sebelum disconnect):**

1. LobbyManager menemukan match untuk Pemain A dan Pemain B, memanggil `_start_match(player_list)`.
2. `_start_match` memanggil `create_room(player_list)` di RoomManager. Di dalam fungsi ini, dict pemain dibuat dari list yang diberikan:
   ```python
   def create_room(self, player_list):
       players = {p['player_id']: p for p in player_list}
       # player_list[0] = {'player_id': 'aaa111', 'username': 'bagus', 'handler': handler_A_v1}
       # player_list[1] = {'player_id': 'bbb222', 'username': 'verya', 'handler': handler_B}
       # Hasil: room.players = {
       #   'aaa111': {'player_id': 'aaa111', ..., 'handler': handler_A_v1},
       #   'bbb222': {'player_id': 'bbb222', ..., 'handler': handler_B}
       # }
   ```
   Perhatikan bahwa `room.players['aaa111']['handler']` menyimpan referensi ke `handler_A_v1` — instance `ClientHandler` pertama yang menangani koneksi Pemain A.
3. Pertandingan dimulai dan berjalan normal.

**Fase 2 — Disconnect dan Reconnect:**

4. Pemain A kehilangan koneksi. Thread `handler_A_v1` berakhir. Server mempertahankan sesi Pemain A selama 60 detik.
5. Pemain A melakukan reconnect. Instance `ClientHandler` baru (`handler_A_v2`) dibuat untuk koneksi TCP baru ini.
6. `_handle_reconnect` di `handler_A_v2` dieksekusi:
   ```python
   def _handle_reconnect(self, packet):
       # Validasi token...
       with self.sessions_lock:
           session['handler'] = self          # session['handler'] = handler_A_v2 ✓
           session['_current_handler'] = self # _current_handler = handler_A_v2 ✓
       # Tutup socket handler_A_v1...
       # Kirim S_RECONNECT_OK ke handler_A_v2...
       room = self.rooms.get_room_by_player(self.player_id)
       if room:
           state = room.game_engine.build_state_for_player(self.player_id)
           self.send_packet({'type': S_GAME_STATE_UPDATE, 'state': state})
           # ↑ Menggunakan self.send_packet() yang mengirim via handler_A_v2 — BERHASIL! ✓
   ```
7. Pemain A menerima `S_RECONNECT_OK` dan `S_GAME_STATE_UPDATE`. Klien masuk ke game screen. Hingga titik ini, semuanya berjalan benar.

**Namun, perhatikan bahwa `room.players['aaa111']['handler']` masih menunjuk ke `handler_A_v1`** (yang socket-nya sudah ditutup). Hanya `session['handler']` yang diperbarui — bukan `room.players['handler']`.

**Fase 3 — Broadcast Gagal (saat Call Liar):**

8. Pemain B memanggil "Call Liar". Server memprosesnya di `_handle_call_liar`:
   ```python
   def _handle_call_liar(self, packet):
       result = engine.call_liar(self.player_id)
       # Broadcast ke SEMUA pemain di room:
       self.broadcast_room({'type': S_LIAR_CALLED, ...})
       self.broadcast_room({'type': S_REVEAL_CARDS, ...})
       self.broadcast_room({'type': S_ROULETTE_START, ...})
       self.send_game_state(room)  # Juga broadcast S_GAME_STATE_UPDATE
   ```
9. Fungsi `broadcast_room` melakukan iterasi pada `room.players`:
   ```python
   def broadcast_room(self, packet):
       room = self.rooms.get_room_by_player(self.player_id)
       for pid, psess in room.players.items():
           handler = psess.get('handler')    # Untuk 'aaa111': handler_A_v1 (MATI!)
           if handler:
               handler.send_packet(packet)   # ← Mengirim ke handler_A_v1 yang sudah mati
   ```
10. Untuk Pemain B (`'bbb222'`), `psess.get('handler')` mengembalikan `handler_B` yang masih aktif — paket terkirim dengan sukses.
11. Untuk Pemain A (`'aaa111'`), `psess.get('handler')` mengembalikan `handler_A_v1` yang socket-nya sudah ditutup. `handler.send_packet()` memanggil `self.sock.sendall(data)` yang memicu `BrokenPipeError` atau `OSError`, ditangkap oleh except block di `send_packet` yang hanya mengatur `self._running = False` — **paket hilang tanpa notifikasi error ke server atau klien**.
12. Fungsi `send_game_state(room)` memiliki masalah yang sama — juga menggunakan `room.players` untuk mendapatkan handler.

Diagram referensi handler sebelum dan sesudah reconnect:
```
SEBELUM RECONNECT:
  session['handler']        → handler_A_v1 (socket hidup) ✓
  room.players['aaa111']['handler'] → handler_A_v1 (socket hidup) ✓

SETELAH RECONNECT (sebelum fix):
  session['handler']        → handler_A_v2 (socket hidup) ✓
  room.players['aaa111']['handler'] → handler_A_v1 (socket MATI!) ✗ ← STALE!

SETELAH RECONNECT (setelah fix):
  session['handler']        → handler_A_v2 (socket hidup) ✓
  room.players['aaa111']['handler'] → handler_A_v2 (socket hidup) ✓
```

Fungsi-fungsi server yang terpengaruh oleh referensi handler yang kedaluwarsa:
| Fungsi | Menggunakan Referensi | Dampak |
|--------|----------------------|--------|
| `broadcast_room()` | `room.players[pid]['handler']` | Semua broadcast room (LIAR_CALLED, REVEAL_CARDS, ROULETTE_START, PLAY_ACCEPTED, ROUND_RESET, GAME_OVER) tidak sampai ke pemain yang reconnect |
| `send_to_opponent()` | `room.players[pid]['handler']` | Notifikasi ke lawan (OPPONENT_DISCONNECTED, OPPONENT_RECONNECTED, CHAT_MSG) tidak sampai |
| `send_game_state()` | `room.players[pid]['handler']` | Sinkronisasi state permainan (GAME_STATE_UPDATE) tidak sampai — klien terjebak di fase yang salah |
| `send_your_turn()` | `room.players[pid]['handler']` | Notifikasi giliran (YOUR_TURN) tidak sampai — pemain tidak tahu gilirannya |

#### Akar Penyebab

Ada **dua lokasi penyimpanan referensi handler** yang terpisah dan tidak tersinkronisasi:
1. `sessions[pid]['handler']` — dict sesi global yang dikelola oleh `ClientHandler` saat connect/reconnect.
2. `room.players[pid]['handler']` — dict pemain di dalam objek `Room` yang dibuat saat `create_room()` dipanggil.

`_handle_reconnect` hanya memperbarui referensi di lokasi pertama (`session`) tetapi tidak di lokasi kedua (`room.players`). Seluruh fungsi broadcast di server menggunakan referensi dari lokasi kedua, yang masih menunjuk ke handler lama dengan socket mati.

Ini adalah bug *stale reference* klasik — dua salinan dari pointer yang sama, tetapi hanya satu yang diperbarui saat objek berubah.

#### Solusi

Di `_handle_reconnect`, setelah menutup socket handler lama dan sebelum mengirim `S_RECONNECT_OK`, tambahkan pembaruan referensi handler di `room.players`:

```python
def _handle_reconnect(self, packet):
    # ... validasi token, ambil old_handler ...

    with self.sessions_lock:
        session['handler'] = self
        session['connected'] = True
        session['_current_handler'] = self

    # Tutup socket handler lama...
    if old_handler is not None:
        old_handler._running = False
        old_sock = old_handler.sock
        if old_sock is not None:
            old_sock.shutdown(socket.SHUT_RDWR)
            old_sock.close()

    # ═══════════════════════════════════════════════════════════
    # FIX: Perbarui referensi handler di room.players agar
    # broadcast_room, send_to_opponent, send_game_state, dan
    # send_your_turn menggunakan handler baru.
    # ═══════════════════════════════════════════════════════════
    room = self.rooms.get_room_by_player(self.player_id)
    if room and self.player_id in room.players:
        room.players[self.player_id]['handler'] = self

    # Baru kirim S_RECONNECT_OK dan S_GAME_STATE_UPDATE...
    self.send_packet({'type': S_RECONNECT_OK, ...})
    if room:
        room.game_engine.set_player_connected(self.player_id, True)
        state = room.game_engine.build_state_for_player(self.player_id)
        self.send_packet({'type': S_GAME_STATE_UPDATE, 'state': state})
        self.send_to_opponent({'type': S_OPPONENT_RECONNECTED, 'player_id': self.player_id})
```

**Catatan:** Pembaruan `room.players[self.player_id]['handler'] = self` dilakukan **sebelum** pengiriman `S_GAME_STATE_UPDATE` dan `send_to_opponent()` agar paket-paket tersebut sudah menggunakan handler baru. Jika pembaruan dilakukan setelahnya, `send_to_opponent()` masih akan menggunakan handler lama.

**Hasil:** Setelah perbaikan, seluruh broadcast dari server — termasuk transisi fase dari PLAYING ke ROULETTE, hasil Call Liar, notifikasi giliran, dan pesan chat — sampai ke pemain yang baru reconnect secara real-time. Overlay roulette dan tombol PULL TRIGGER muncul dengan benar di klien yang baru reconnect.

---

### Ringkasan Perubahan File untuk Perbaikan Bug

| File | Perubahan | Masalah yang Diatasi |
|------|-----------|---------------------|
| `client/session_manager.py` | **File baru.** Skema file sesi per-username (`data/session_<username>.json`) dengan fungsi `_safe_username()`, `_session_path()`, `save_session()`, `load_session()`, dan `clear_session()`. | Masalah 1 |
| `client/network.py` | Penambahan variabel `_generation` pada `NetworkClient` yang dinaikkan di setiap `connect()` dan `disconnect()`. Thread `_receive_loop(gen)` menerima parameter generation dan hanya memposting `__DISCONNECTED__` jika `gen == self._generation`. | Masalah 2 |
| `client/main_client.py` | Penambahan fungsi `_do_reconnect()` untuk alur reconnect dari sesi tersimpan. Penambahan variabel `_reconnect_grace_until` (grace window 3 detik) di handler `S_RECONNECT_OK` untuk mengabaikan `__DISCONNECTED__` kedaluwarsa. Sintesis `roulette_state` fallback saat `S_GAME_STATE_UPDATE` diterima di fase ROULETTE tanpa data roulette. Handler baru untuk paket room system (`S_ROOM_CREATED`, `S_ROOM_JOINED`, `S_ROOM_UPDATE`, `S_ROOM_PLAYER_JOINED`, `S_ROOM_PLAYER_LEFT`, `S_ROOM_ERROR`). State machine baru `STATE_ROOM` untuk layar lobi room privat. | Masalah 2, 4 |
| `client/screens/screen_login.py` | Pre-fill field username/IP/port dari sesi tersimpan terbaru saat layar login diinisialisasi. Tombol Reconnect hanya aktif jika field username tidak kosong. Label "Previous session" dinamis yang memperbarui teksnya berdasarkan username yang sedang diketik. Fungsi `_try_reconnect()` memanggil `load_session(username)` dengan parameter username spesifik. | Masalah 1 |
| `client/screens/screen_menu.py` | **File baru.** Layar menu utama dengan kelas `MenuScreen` dan komponen internal `_RoomCodeField`. Menyediakan tombol Quick Match (matchmaking otomatis), Create Room (buat room privat), Join Room (input kode room 6 karakter), dan Disconnect. | — (fitur baru) |
| `client/screens/screen_room.py` | **File baru.** Layar lobi room privat dengan kelas `RoomScreen`. Menampilkan kode room dalam kotak besar, daftar pemain dengan indikator host (bintang emas), slot kosong ("Waiting..."), animasi titik bergerak, tombol Start Game (hanya untuk host, aktif jika ≥ 2 pemain), dan tombol Leave Room. | — (fitur baru) |
| `server/client_handler.py` | **`_handle_reconnect`:** Penutupan socket handler lama secara eksplisit (`shutdown` + `close`). Pembaruan referensi handler di `session` (`session['handler'] = self`) dan di `room.players` (`room.players[pid]['handler'] = self`). Pengiriman `S_GAME_STATE_UPDATE` pasca-reconnect dengan state lengkap termasuk `roulette_state`. **`_start_match`:** Penambahan `room.status = 'IN_GAME'` setelah `create_room()` berhasil. **Handler baru:** `_handle_create_room`, `_handle_join_room`, `_handle_leave_room`, `_handle_start_room_game` untuk mendukung room privat dengan kode. **`_handle_disconnect`:** Proteksi `is_superseded` yang memeriksa `_current_handler` — jika handler ini bukan handler terkini (sudah digantikan oleh handler reconnect baru), seluruh logika disconnect dilewati agar tidak merusak sesi baru. | Masalah 3, 4 |
| `server/game_engine.py` | **`build_state_for_player`:** Selalu menyertakan `roulette_state` (berisi `target_player_id`, `pull_number`, `chamber_count`, `survived: None`) saat engine berada di `PHASE_ROULETTE`. Sebelumnya, `roulette_state` hanya dikirim via paket `S_ROULETTE_START` yang bisa hilang jika broadcast gagal. Dengan selalu menyertakannya di state update, klien yang reconnect mendapat data roulette lengkap meskipun melewatkan paket broadcast sebelumnya. | Masalah 4 |
| `server/room_manager.py` | Penambahan `_player_room_map` (dict `player_id → room_id`) untuk pencarian room O(1) tanpa scan seluruh room aktif. Fungsi baru: `create_private_room()` (membuat room privat dengan kode unik dan status WAITING), `get_room_by_code()` (pencarian room case-insensitive berdasarkan kode), `add_player_to_room()` (menambahkan pemain ke room WAITING yang sudah ada), `remove_player_from_room()` (menghapus pemain, mengalihkan host jika perlu, menghapus room jika kosong), `get_room_players()` (mengembalikan info pemain di room). | Masalah 3 |
| `server/main_server.py` | **`start_match`:** Penambahan `room.status = 'IN_GAME'` setelah `create_room()` berhasil, sinkron dengan perbaikan yang sama di `client_handler.py`. | Masalah 3 |
