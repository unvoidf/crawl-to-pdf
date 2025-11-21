# Website PDF Crawler

Headless Chrome kullanarak bir website'deki tüm sayfaları crawl edip PDF formatına çeviren Python CLI aracı.

## Özellikler

- **Otomatik Crawling**: Verilen URL'den başlayarak domain içindeki tüm sayfaları otomatik keşfeder
- **Domain Sınırlaması**: Sadece aynı domain içindeki sayfaları crawl eder
- **PDF Dönüşümü**: Her sayfayı PDF formatına çevirir
- **Akıllı İsimlendirme**: Sayfa başlığı ve URL'den otomatik dosya adı oluşturur
- **Progress Tracking**: İşlem ilerlemesini gösterir
- **Hata Yönetimi**: Hataları loglar ve işleme devam eder

## Kurulum

1. Gerekli bağımlılıkları yükleyin:

```bash
pip install -r requirements.txt
```

2. Playwright browser'ları yükleyin:

```bash
playwright install chromium
```

## Kullanım

### Temel Kullanım

```bash
python crawl_to_pdf.py www.example.com
```

### Örnekler

```bash
# HTTPS ile
python crawl_to_pdf.py https://example.com

# Özel çıktı klasörü ile
python crawl_to_pdf.py www.example.com --output my-pdfs

# Kısa form
python crawl_to_pdf.py example.com -o pdfs
```

## Çıktı

- PDF'ler varsayılan olarak `results/{domain}-pdfs` klasörüne kaydedilir
- Örnek: `www.example.com` → `results/www-example-com-pdfs/` klasörü
- PDF isimleri: `{Title}_{URL_segment}.pdf` formatındadır
- Örnek: `Hakkimizda_about.pdf`

## Nasıl Çalışır?

1. Verilen URL'den başlar
2. Domain'i çıkarır ve klasör oluşturur
3. Headless Chrome'u başlatır
4. BFS (Breadth-First Search) algoritması ile sayfaları crawl eder:
   - Her sayfayı yükler (DOMContentLoaded)
   - Sayfadaki linkleri çıkarır
   - Aynı domain'deki yeni linkleri queue'ya ekler
   - Sayfayı PDF'e çevirir
5. Tüm sayfalar işlendiğinde özet gösterir

## Teknik Detaylar

### URL Normalizasyonu
- Eksik protokol otomatik eklenir (https)
- Fragment (#) kaldırılır
- Query parametreleri korunur
- Trailing slash normalize edilir

### Domain Kontrolü
- Sadece aynı domain'deki linkler takip edilir
- Subdomain'ler dahil edilmez (www.example.com ≠ api.example.com)

### PDF İsimlendirme
- Sayfa başlığından ve URL'nin son segmentinden oluşturulur
- Özel karakterler temizlenir
- Türkçe karakterler ASCII'ye dönüştürülür
- Duplicate isimler için sıra numarası eklenir

### Hata Yönetimi
- Sayfa yüklenemezse: loglanır, atlanır, devam edilir
- PDF oluşturulamazsa: loglanır, atlanır, devam edilir
- Tüm hatalar konsola ve özete yazılır

## Gereksinimler

- Python 3.7+
- Playwright
- Unidecode

## Dosya Yapısı

```
BBB/
├── crawl_to_pdf.py          # Ana CLI script
├── crawler_components/
│   ├── __init__.py          # Yardımcı paket tanımı
│   ├── url_manager.py       # URL yönetimi ve domain kontrolü
│   ├── web_crawler.py       # Web crawling mantığı
│   ├── pdf_generator.py     # PDF oluşturma
│   ├── file_name_generator.py # PDF isimlendirme
│   └── progress_tracker.py  # İlerleme takibi
├── results/                 # PDF çıktıları (gitignore)
├── requirements.txt         # Bağımlılıklar
└── README.md               # Bu dosya
```

## Notlar

- İlk çalıştırmada Playwright browser'ları indirilecektir (birkaç yüz MB)
- Büyük website'ler için işlem uzun sürebilir
- Rate limiting yoktur, dikkatli kullanın
- Bazı sayfalar JavaScript ile dinamik içerik yükleyebilir, bu durumda içerik eksik olabilir

## Lisans

Bu proje eğitim amaçlıdır.

