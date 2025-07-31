from flask import Flask, render_template, request, redirect, flash
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import traceback
import json

app = Flask(__name__)
app.secret_key = 'rahasia'  # Untuk flash messages

# Setup koneksi ke Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]
import os
creds_dict = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    SPREADSHEET_ID = "1u15SGd-ihsXwHMbw6kfWZzsfZnqaf2qIH-kFeNmQb4g"
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        sheet = spreadsheet.worksheet("JenisLomba")
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title="JenisLomba", rows=100, cols=2)
        sheet.append_row(["Nama Lomba"])
except Exception as e:
    client = None
    sheet = None
    print(f"❌ Gagal autentikasi atau membuka spreadsheet: {str(e)}")
    traceback.print_exc()


@app.route('/lomba', methods=['GET', 'POST'])
def jenis_lomba():
    if request.method == 'POST':
        nama_jenis = request.form.get('jenis')
        if nama_jenis:
            try:
                sheet.append_row([nama_jenis])
                flash("✅ Jenis lomba berhasil ditambahkan", "success")
            except Exception as e:
                flash(f"❌ Gagal menambahkan jenis lomba: {e}", "danger")
        return redirect('/lomba')

    jenis_values = sheet.get_all_values()[1:] if sheet else []
    jenis_list = [{"jenis": row[0]} for row in jenis_values if row]
    return render_template('lomba.html', jenis_list=jenis_list)


@app.route('/register', methods=['GET', 'POST'])
def register_team():
    if request.method == 'POST':
        nama_tim = request.form.get('nama_tim')
        jenis_lomba = request.form.get('jenis_lomba')

        anggota = []
        for i in range(1, 8):
            anggota_i = request.form.get(f'anggota{i}')
            anggota.append(anggota_i if anggota_i else "")  # Isi kosong jika tidak diisi

        try:
            reg_sheet = client.open_by_key(SPREADSHEET_ID).worksheet("Registrasi")
            headers = reg_sheet.row_values(1)
            expected_headers = ["Nama Tim", "Jenis Lomba"] + [f"Anggota {i}" for i in range(1, 8)]
            if headers != expected_headers:
                reg_sheet.clear()
                reg_sheet.append_row(expected_headers)

            reg_sheet.append_row([nama_tim, jenis_lomba] + anggota)
            flash(f"✅ Tim '{nama_tim}' berhasil didaftarkan!", "success")
        except Exception as e:
            flash(f"❌ Gagal menyimpan data: {e}", "danger")
            traceback.print_exc()

        return redirect('/register')

    # Ambil list jenis lomba dari worksheet
    try:
        jenis_sheet = client.open_by_key(SPREADSHEET_ID).worksheet("JenisLomba")
        jenis_list = jenis_sheet.col_values(1)[1:]  # Skip header
    except Exception as e:
        print("❌ Gagal mengambil jenis lomba:", e)
        jenis_list = []

    return render_template('register.html', jenis_list=jenis_list)


@app.route('/')
def home():
    return redirect('/home')

@app.route('/home')
def landing_page():
    return render_template('home.html')

@app.route('/skoring', methods=['GET', 'POST'])
def skoring():
    jenis_list = []
    tim_by_jenis = {}

    try:
        jenis_sheet = client.open_by_key(SPREADSHEET_ID).worksheet("JenisLomba")
        jenis_list = jenis_sheet.col_values(1)[1:]  # Skip header

        reg_sheet = client.open_by_key(SPREADSHEET_ID).worksheet("Registrasi")
        data = reg_sheet.get_all_values()[1:]  # Skip header
        for row in data:
            if len(row) >= 2:
                jenis = row[1]
                nama_tim = row[0]
                if jenis not in tim_by_jenis:
                    tim_by_jenis[jenis] = []
                tim_by_jenis[jenis].append(nama_tim)
    except Exception as e:
        print("❌ Gagal mengambil data registrasi atau jenis:", e)
        traceback.print_exc()

    if request.method == 'POST':
        jenis_lomba = request.form.get('jenis_lomba')
        babak = request.form.get('babak')
        tim_a = request.form.get('tim_a')
        tim_b = request.form.get('tim_b')
        pemenang = request.form.get('pemenang')

        try:
            skor_sheet = client.open_by_key(SPREADSHEET_ID).worksheet("Skoring")
        except gspread.exceptions.WorksheetNotFound:
            skor_sheet = spreadsheet.add_worksheet(title="Skoring", rows=100, cols=6)
            skor_sheet.append_row(["Jenis Lomba", "Babak", "Tim A", "Tim B", "Pemenang"])

        try:
            skor_sheet.append_row([jenis_lomba, babak, tim_a, tim_b, pemenang])
            flash("✅ Skor berhasil disimpan!", "success")
        except Exception as e:
            flash(f"❌ Gagal menyimpan skor: {e}", "danger")
            traceback.print_exc()

        return redirect('/skoring')

    return render_template("skoring.html", jenis_list=jenis_list, tim_by_jenis=tim_by_jenis)

if __name__ == '__main__':
    app.run(debug=True)
