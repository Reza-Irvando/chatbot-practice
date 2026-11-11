# Dokumen Evaluasi & Benchmark: Tanya Jawab UU Perlindungan Data Pribadi (UU No. 27 Tahun 2022)

Dokumen ini berisi daftar pertanyaan uji (test questions), dasar hukum rujukan, serta harapan jawaban AI (*expected response*) yang komprehensif, presisi secara yuridis, dan berlandaskan pada **Undang-Undang Republik Indonesia Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)**.

Dokumen ini dirancang sebagai acuan pengujian (benchmark) kualitas implementasi Retrieval-Augmented Generation (RAG) dan respon LLM.

---

## Standar Penilaian Evaluasi (Evaluation Rubric)

Setiap respon AI dinilai berdasarkan 4 kriteria utama:
2. **Ketepatan Sitasi (*Citation Grounding*)**: Apakah AI mencantumkan nomor Pasal, Ayat, atau Huruf yang relevan secara eksplisit?
3. **Pembedaan Peran & Konsep (*Concept Disambiguation*)**: Apakah AI membedakan secara tegas antara Subjek Data, Pengendali Data, dan Prosesor Data, serta antara Data Umum vs Data Spesifik?
4. **Resistensi Halusinasi (*Hallucination Resistance*)**: Apakah AI menolak mengarang aturan saat ditanyakan hal di luar cakupan UU PDP?

---

## Daftar Pertanyaan dan Harapan Jawaban

### Bagian 1: Definisi & Ketentuan Umum

#### Pertanyaan 1.1
> **User**: "Apa definisi Data Pribadi menurut UU PDP?"
- **Dasar Hukum**: Pasal 1 angka 1 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 1 angka 1 UU PDP**.
  - Menyatakan bahwa *Data Pribadi adalah data tentang orang perseorangan yang teridentifikasi atau dapat diidentifikasi secara tersendiri atau dikombinasi dengan informasi lainnya baik secara langsung maupun tidak langsung melalui sistem elektronik atau nonelektronik*.
  - Menyebutkan bahwa orang perseorangan yang memiliki data tersebut dinamakan **Subjek Data Pribadi** (Pasal 1 angka 2).

#### Pertanyaan 1.2
> **User**: "Apa perbedaan antara Pengendali Data Pribadi dan Prosesor Data Pribadi?"
- **Dasar Hukum**: Pasal 1 angka 4 dan angka 5 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 1 angka 4 dan angka 5**.
  - **Pengendali Data Pribadi (*Data Controller*)**: Setiap orang, badan publik, atau organisasi internasional yang bertindak sendiri-sendiri atau bersama-sama dalam menentukan tujuan dan melakukan kendali pemrosesan Data Pribadi.
  - **Prosesor Data Pribadi (*Data Processor*)**: Setiap orang, badan publik, atau organisasi internasional yang bertindak sendiri-sendiri atau bersama-sama dalam melakukan pemrosesan Data Pribadi atas nama Pengendali Data Pribadi.
  - Menjelaskan perbedaannya: Pengendali menentukan tujuan dan kendali kebijakan pemrosesan, sedangkan Prosesor mengeksekusi pemrosesan atas nama/instruksi Pengendali.

#### Pertanyaan 1.3
> **User**: "Apakah UU PDP berlaku jika perusahaan asing di luar negeri memproses data warga negara Indonesia?"
- **Dasar Hukum**: Pasal 2 UU No. 27 Tahun 2022 (Asas Ekstrateritorialitas).
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 2 ayat (1) dan ayat (2) UU PDP**.
  - Menjelaskan bahwa UU PDP memiliki asas ekstrateritorial. UU ini berlaku bagi setiap orang, badan publik, dan organisasi internasional yang berada di luar wilayah hukum Republik Indonesia apabila perbuatannya:
    1. Memiliki akibat hukum di wilayah hukum Indonesia; dan/atau
    2. Berlaku bagi Subjek Data Pribadi warga negara Indonesia di luar wilayah hukum Negara Republik Indonesia.
  - Menyimpulkan: Ya, perusahaan asing di luar negeri tetap tunduk pada ketentuan UU PDP jika memenuhi kriteria tersebut.

---

### Bagian 2: Jenis Data Pribadi (Umum vs Spesifik)

#### Pertanyaan 2.1
> **User**: "Apa saja jenis data pribadi menurut UU PDP dan bagaimana pembagiannya?"
- **Dasar Hukum**: Pasal 4 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 4 UU PDP**.
  - Menjelaskan bahwa Data Pribadi terbagi menjadi 2 jenis:
    1. **Data Pribadi yang bersifat Spesifik** (Pasal 4 ayat 2):
       - Data dan informasi kesehatan;
       - Data biometrik;
       - Data genetika;
       - Catatan kejahatan;
       - Data anak;
       - Data keuangan pribadi; dan/atau
       - Data lainnya sesuai dengan ketentuan peraturan perundang-undangan.
    2. **Data Pribadi yang bersifat Umum** (Pasal 4 ayat 3):
       - Nama lengkap;
       - Jenis kelamin;
       - Kewarganegaraan;
       - Agama;
       - Status perkawinan; dan/atau
       - Data Pribadi yang dikombinasikan untuk mengidentifikasi seseorang.

#### Pertanyaan 2.2
> **User**: "Apakah riwayat rekam medis dan data sidik jari termasuk data yang bersifat spesifik?"
- **Dasar Hukum**: Pasal 4 ayat (2) huruf a dan b UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 4 ayat (2) huruf a dan b UU PDP**.
  - Menjelaskan bahwa **rekam medis** tergolong dalam *data dan informasi kesehatan* (huruf a) dan **sidik jari** tergolong dalam *data biometrik* (huruf b).
  - Menegaskan bahwa keduanya merupakan **Data Pribadi yang bersifat Spesifik**, yang pemrosesannya memerlukan perlakuan dan pengamanan khusus serta persetujuan eksplisit.

---

### Bagian 3: Hak-Hak Subjek Data Pribadi (Pasal 5 - 15)

#### Pertanyaan 3.1
> **User**: "Sebutkan hak-hak yang dimiliki oleh pemilik data pribadi menurut UU PDP!"
- **Dasar Hukum**: Bab IV (Pasal 5 s.d. Pasal 14) UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Bab IV Hak Subjek Data Pribadi (Pasal 5 - Pasal 14)**.
  - Merinci hak-hak utama:
    1. **Hak Kejelasan Informasi** (Pasal 5): Mengetahui kejelasan identitas, dasar kepentingan hukum, tujuan permintaan dan penggunaan data, serta akuntabilitas pihak yang meminta data.
    2. **Hak Melengkapi & Memperbaiki** (Pasal 6): Melengkapi, memperbarui, atau memperbaiki kesalahan/ketidakakuratan data miliknya.
    3. **Hak Akses & Salinan** (Pasal 7): Mendapatkan akses dan memperoleh salinan data pribadinya sesuai perundang-undangan.
    4. **Hak Mengakhiri, Menghapus, & Memusnahkan** (Pasal 8): Mengakhiri pemrosesan, menghapus, dan/atau memusnahkan data pribadi miliknya (*right to erasure/forgotten*).
    5. **Hak Menarik Kembali Persetujuan** (Pasal 9): Menarik persetujuan pemrosesan yang pernah diberikan (*withdrawal of consent*).
    6. **Hak Menolak Otomatisasi & Profiling** (Pasal 10): Menolak tindakan pengambilan keputusan yang hanya didasarkan pada pemrosesan otomatis (seperti profiling) yang menimbulkan akibat hukum.
    7. **Hak Menunda atau Membatasi Pemrosesan** (Pasal 11): Menunda atau membatasi pemrosesan secara proporsional.
    8. **Hak Menggugat & Ganti Rugi** (Pasal 12): Menggugat dan menerima ganti rugi atas pelanggaran pemrosesan data pribadinya.
    9. **Hak Portabilitas Data** (Pasal 13): Mendapatkan dan/atau mentransfer data pribadinya ke pengendali data lain dalam format yang terstruktur dan umum digunakan.

#### Pertanyaan 3.2
> **User**: "Apakah hak subjek data pribadi bersifat mutlak, atau ada pengecualiannya?"
- **Dasar Hukum**: Pasal 15 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 15 UU PDP**.
  - Menjelaskan bahwa hak-hak subjek data pribadi (khususnya Pasal 8, Pasal 9, Pasal 10 ayat (1), Pasal 11, dan Pasal 13 ayat (1) dan (2)) **dikecualikan untuk kepentingan tertentu**, yaitu:
    1. Kepentingan pertahanan dan keamanan nasional;
    2. Kepentingan proses penegakan hukum;
    3. Kepentingan umum dalam rangka penyelenggaraan negara;
    4. Kepentingan pengawasan sektor jasa keuangan, moneter, sistem pembayaran, dan stabilitas sistem keuangan; atau
    5. Kepentingan statistik dan penelitian ilmiah.
  - Menjelaskan bahwa pengecualian tersebut hanya dapat dilakukan dalam rangka pelaksanaan ketentuan undang-undang.

---

### Bagian 4: Pemrosesan & Dasar Pemrosesan Data Pribadi

#### Pertanyaan 4.1
> **User**: "Apa saja dasar hukum (legal basis) yang sah bagi Pengendali untuk memproses data pribadi?"
- **Dasar Hukum**: Pasal 20 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 20 ayat (2) UU PDP**.
  - Menguraikan bahwa Pengendali Data Pribadi wajib memiliki setidaknya salah satu dasar pemrosesan berikut:
    a. **Persetujuan yang sah dan eksplisit** dari Subjek Data Pribadi untuk 1 (satu) atau beberapa tujuan tertentu;
    b. **Pemenuhan kewajiban perjanjian/kontrak** di mana Subjek Data Pribadi merupakan salah satu pihak;
    c. **Pemenuhan kewajiban hukum** dari Pengendali Data Pribadi sesuai ketentuan perundang-undangan;
    d. **Pemenuhan pelindungan kepentingan vital** Subjek Data Pribadi;
    e. **Pelaksanaan tugas dalam rangka kepentingan umum**, pelayanan publik, atau kewenangan Pengendali Data Pribadi berdasarkan undang-undang; dan/atau
    f. **Pemenuhan kepentingan yang sah lainnya** (*legitimate interest*) dengan tetap memperhatikan tujuan, kebutuhan, dan keseimbangan kepentingan antara Pengendali dan hak Subjek Data.

#### Pertanyaan 4.2
> **User**: "Bagaimana aturan pemrosesan data pribadi anak menurut UU PDP?"
- **Dasar Hukum**: Pasal 24 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 24 UU PDP**.
  - Pemrosesan data pribadi anak diselenggarakan secara khusus.
  - Pemrosesan data pribadi anak **wajib mendapatkan persetujuan dari orang tua dan/atau wali anak** sesuai dengan ketentuan peraturan perundang-undangan.

---

### Bagian 5: Kewajiban Pengendali Data & Penanganan Kebocoran Data

#### Pertanyaan 5.1
> **User**: "Apa yang wajib dilakukan Pengendali Data jika terjadi kegagalan pelindungan data pribadi (kebocoran data), dan berapa batas waktunya?"
- **Dasar Hukum**: Pasal 46 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 46 ayat (1) dan ayat (2) UU PDP**.
  - Dalam hal terjadi kegagalan pelindungan Data Pribadi, Pengendali Data Pribadi **wajib menyampaikan pemberitahuan secara tertulis paling lambat 3 x 24 (tiga kali dua puluh empat) jam** kepada:
    1. Subjek Data Pribadi; dan
    2. Lembaga pengawas pelindungan data pribadi.
  - Isi pemberitahuan tertulis tersebut minimal memuat:
    - Data pribadi yang terungkap/bocor;
    - Kapan dan bagaimana data pribadi terungkap; dan
    - Upaya penanganan dan pemulihan atas terungkapnya data oleh Pengendali Data Pribadi.
  - Pada kasus tertentu, Pengendali juga wajib memberitahukan kepada masyarakat mengenai insiden tersebut (Pasal 46 ayat 3).

#### Pertanyaan 5.2
> **User**: "Kapan sebuah organisasi atau perusahaan wajib menunjuk Pejabat/Petugas Pelindung Data Pribadi (Data Protection Officer / DPO)?"
- **Dasar Hukum**: Pasal 53 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 53 ayat (1) dan ayat (2) UU PDP**.
  - Pengendali Data Pribadi dan Prosesor Data Pribadi wajib menunjuk Pejabat/Petugas yang menjalankan fungsi Pelindungan Data Pribadi (DPO) jika:
    1. Pemrosesan Data Pribadi dilakukan untuk kepentingan pelayanan publik;
    2. Kegiatan inti Pengendali Data memiliki sifat, ruang lingkup, dan/atau tujuan yang memerlukan pengawasan secara teratur dan sistematis atas Data Pribadi dalam skala besar; dan/atau
    3. Kegiatan inti Pengendali Data terdiri dari pemrosesan Data Pribadi dalam skala besar untuk Data Pribadi yang bersifat spesifik dan/atau data yang berkaitan dengan tindak pidana.
  - Pejabat ini ditunjuk berdasarkan profesionalitas, pengetahuan hukum, dan praktik pelindungan data.

---

### Bagian 6: Transfer Data Pribadi Lintas Batas Negara

#### Pertanyaan 6.1
> **User**: "Apakah boleh mentransfer data pribadi ke luar negeri, dan apa saja syaratnya?"
- **Dasar Hukum**: Pasal 56 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 56 UU PDP**.
  - Menjelaskan bahwa transfer data ke luar wilayah Indonesia diperbolehkan dengan mekanisme bertingkat:
    1. **Tingkat Kesetaraan Perlindungan** (Pasal 56 ayat 2): Pengendali wajib memastikan negara tujuan transfer memiliki tingkat pelindungan data pribadi yang setara atau lebih tinggi dari UU PDP.
    2. **Pelindungan Memadai dan Mengikat** (Pasal 56 ayat 3): Jika syarat kesetaraan di atas tidak terpenuhi, Pengendali wajib memastikan terdapat instrumen pelindungan data pribadi yang memadai dan bersifat mengikat (*binding legal instrument* / BCR / SCC).
    3. **Persetujuan Subjek Data** (Pasal 56 ayat 4): Jika kedua syarat di atas tidak terpenuhi, transfer hanya dapat dilakukan setelah mendapatkan persetujuan eksplisit dari Subjek Data Pribadi.

---

### Bagian 7: Kelembagaan

#### Pertanyaan 7.1
> **User**: "Lembaga apa yang bertugas mengawasi pelaksanaan UU PDP di Indonesia?"
- **Dasar Hukum**: Pasal 58, 59, dan 60 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 58 ayat (1) s.d. ayat (3) UU PDP**.
  - Penyelenggaraan Pelindungan Data Pribadi diawasi oleh **Lembaga** yang ditetapkan oleh Presiden.
  - Lembaga tersebut **bertanggung jawab langsung kepada Presiden**.
  - Wewenang lembaga (Pasal 60) meliputi perumusan kebijakan, pengawasan kepatuhan, penjatuhan sanksi administratif, dan fasilitasi penyelesaian sengketa di luar pengadilan.

---

### Bagian 8: Sanksi Administratif

#### Pertanyaan 8.1
> **User**: "Apa saja sanksi administratif bagi pihak yang melanggar ketentuan UU PDP dan berapa batas denda maksimalnya?"
- **Dasar Hukum**: Pasal 57 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 57 ayat (1) s.d. ayat (3) UU PDP**.
  - Bentuk sanksi administratif:
    a. Peringatan tertulis;
    b. Penghentian sementara kegiatan pemrosesan Data Pribadi;
    c. Penghapusan atau pemusnahan Data Pribadi; dan/atau
    d. **Denda administratif**.
  - Batas maksimal denda administratif (Pasal 57 ayat 3): **Paling tinggi 2% (dua persen) dari pendapatan tahunan atau penerimaan tahunan** terhadap variabel pelanggaran.

---

### Bagian 9: Ketentuan Pidana (Pasal 65 - 73)

#### Pertanyaan 9.1
> **User**: "Apa ancaman hukuman bagi orang yang mengumpulkan atau menjual data pribadi milik orang lain secara ilegal?"
- **Dasar Hukum**: Pasal 65 ayat (1) dan ayat (3) jo Pasal 67 ayat (1) dan ayat (3) UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 65 jo Pasal 67 UU PDP**.
  - **Memperoleh atau Mengumpulkan Data Pribadi Secara Melawan Hukum** (Pasal 65 ayat 1):
    - Diancam pidana penjara paling lama **5 (lima) tahun** dan/atau pidana denda paling banyak **Rp5.000.000.000,00 (lima miliar rupiah)** (Pasal 67 ayat 1).
  - **Memperjualbelikan atau Memperdagangkan Data Pribadi** (Pasal 65 ayat 3):
    - Diancam pidana penjara paling lama **5 (lima) tahun** dan/atau pidana denda paling banyak **Rp5.000.000.000,00 (lima miliar rupiah)** (Pasal 67 ayat 3).

#### Pertanyaan 9.2
> **User**: "Berapa sanksi pidana untuk pemalsuan data pribadi yang merugikan orang lain?"
- **Dasar Hukum**: Pasal 66 jo Pasal 68 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 66 jo Pasal 68 UU PDP**.
  - Setiap orang yang dengan sengaja membuat Data Pribadi palsu atau memalsukan Data Pribadi dengan maksud untuk menguntungkan diri sendiri atau orang lain yang dapat mengakibatkan kerugian bagi orang lain:
    - Diancam pidana penjara paling lama **6 (enam) tahun** dan/atau pidana denda paling banyak **Rp6.000.000.000,00 (enam miliar rupiah)**.

#### Pertanyaan 9.3
> **User**: "Jika tindak pidana PDP dilakukan oleh Korporasi, siapa yang dipidana dan berapa dendanya?"
- **Dasar Hukum**: Pasal 69 dan Pasal 70 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 69 dan Pasal 70 UU PDP**.
  - Jika tindak pidana dilakukan oleh Korporasi, pidana dapat dijatuhkan kepada **pengurus, pemegang kendali, pemberi perintah, pemilik manfaat (*beneficial owner*), dan/atau Korporasi itu sendiri**.
  - Terhadap korporasi, dijatuhkan pidana denda.
  - Besaran pidana denda bagi Korporasi: **Paling banyak 10 (sepuluh) kali lipat dari maksimal pidana denda yang diancamkan kepada orang perseorangan** (dapat mencapai puluhan miliar rupiah).
  - Selain denda, korporasi dapat dijatuhi pidana tambahan seperti perampasan keuntungan, pembekuan seluruh atau sebagian usaha, penutupan, atau pembubaran korporasi.

---

### Bagian 10: Ketentuan Peralihan

#### Pertanyaan 10.1
> **User**: "Berapa lama masa transisi penyesuaian bagi perusahaan sejak UU PDP diundangkan?"
- **Dasar Hukum**: Pasal 74 UU No. 27 Tahun 2022.
- **Harapan Jawaban AI**:
  - Menyebutkan rujukan **Pasal 74 UU PDP**.
  - Pada saat Undang-Undang ini mulai berlaku, Pengendali Data Pribadi, Prosesor Data Pribadi, dan pihak lain yang terkait dengan pemrosesan Data Pribadi, wajib menyesuaikan dengan ketentuan pemrosesan Data Pribadi berdasarkan Undang-Undang ini **paling lama 2 (dua) tahun** terhitung sejak Undang-Undang ini diundangkan (diundangkan pada 17 Oktober 2022, sehingga batas penyesuaian hingga Oktober 2024).

---

### Bagian 11: Uji Ketahanan Negatif & Resistensi Halusinasi (*Out-of-Scope Test*)

#### Pertanyaan 11.1
> **User**: "Berapa denda pelanggaran GDPR menurut UU Perlindungan Data Pribadi Indonesia?"
- **Dasar Hukum**: Non-cakupan (GDPR adalah regulasi Uni Eropa, bukan bagian dari UU No. 27 Tahun 2022 Indonesia).
- **Harapan Jawaban AI**:
  - AI **tidak boleh mengarang** bahwa UU PDP mengatur besaran denda GDPR.
  - AI secara jujur menyatakan bahwa **GDPR (*General Data Protection Regulation*) adalah undang-undang perlindungan data Uni Eropa**, bukan bagian dari naskah UU No. 27 Tahun 2022 Indonesia.
  - AI menegaskan bahwa dalam UU PDP Indonesia, sanksi denda administratif maksimal adalah 2% dari pendapatan/penjualan tahunan (Pasal 57) dan denda pidana maksimal adalah Rp4 miliar s.d. Rp6 miliar untuk orang atau 10x lipat untuk korporasi (Pasal 67 - 70).

#### Pertanyaan 11.2
> **User**: "Apakah UU PDP mengatur tentang legalitas hukuman mati bagi koruptor data?"
- **Dasar Hukum**: Non-cakupan / aturan tidak ada.
- **Harapan Jawaban AI**:
  - AI menyatakan secara tegas bahwa **UU No. 27 Tahun 2022 TIDAK mengatur hukuman mati**.
  - Ancaman pidana tertinggi dalam UU PDP adalah pidana penjara paling lama 6 (enam) tahun dan denda maksimal Rp6 miliar (Pasal 68) atau pidana tambahan perampasan aset dan pembubaran korporasi (Pasal 70).
