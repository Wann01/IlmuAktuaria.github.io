from flask import Flask, render_template, request
import locale
import csv

app = Flask(__name__, template_folder='templates')

# Inisialisasi tabel mortalitas dari file CSV
mortalita_data = {}
with open('mortalita.csv', mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        if 'n' in row:
            try:
                n = int(row['n'])
                mortalita_data[n] = {
                    'q': float(row['q']),
                    'p': float(row['p']),
                    'l': float(row['l']),
                    'v': float(row['v']),
                    'd': float(row['d'])
                }
            except ValueError:
                pass

def format_as_currency(value):
    return locale.currency(value, grouping=True)

# Definisi jumlah maksimal tabel mortalitas
n111 = 111

def calculate_brpvfb(k, y, r, sr_minus_1, x):
    # Hitung Br menggunakan rumus yang sesuai
    br = k * (r - y) * sr_minus_1

    # Hitung nilai a (N/D)
    N = 0
    D = mortalita_data[r]['d']
    for n_value in range(r, n111 + 1):
        if n_value in mortalita_data:
            N += mortalita_data[n_value]['d']
    a = N / D

    # Hitung v^r-x value
    v = 1
    if x < r:
        n = r - x
        v = 1 / ((1 + 0.025) ** n)

    # Hitung x-rPx value
    Lr = mortalita_data[r]['l']
    Lx = mortalita_data[x]['l']
    p = Lr / Lx

    # Hitung PVFB
    pvfb = br * a * v * p

    return br, pvfb

def calculate_pvfb(k, y, r, sr_minus_1, x):
    # Hitung Br menggunakan rumus yang sesuai
    br = k * (r - y) * sr_minus_1

    # Hitung nilai a (N/D)
    N = 0
    D = mortalita_data[r]['d']
    for n_value in range(r, n111 + 1):
        if n_value in mortalita_data:
            N += mortalita_data[n_value]['d']
    a = N / D

    # Hitung x-rPx value
    Lr = mortalita_data[r]['l']
    p_values = [Lr / mortalita_data[x]['l'] for x in range(x, r + 1)]

    # Hitung PVFB
    pvfb_values = []
    for age in range(x, r + 1):
        br_age = k * (r - y) * sr_minus_1
        a_age = N / D
        v_age = 1 / ((1 + 0.025) ** (r - age))
        p_age = p_values[age - x]
        pvfb_age = br_age * a_age * v_age * p_age
        pvfb_values.append(pvfb_age)

    return pvfb_values

def calculate_normal_contributions(pvfb_values, r, y):
    normal_contributions = {}
    total_normal_contributions = 0
    for age, pvfb in enumerate(pvfb_values, start=1):
        age_key = f'{age}'
        if age == 46:
            age_key = '1'
        normal_contributions[age_key] = pvfb / (r - y)
        total_normal_contributions += normal_contributions[age_key]
    normal_contributions['Total'] = total_normal_contributions
    return normal_contributions

def calculate_ean(pvfb_values, r, y):
    ean_contributions = {}
    for age, pvfb in enumerate(pvfb_values, start=y):
        age_key = f'{age}'
        ean_contributions[age_key] = pvfb / (r - y)
    return ean_contributions

def calculate_pensiun_benefits(pvfb_values, r, y, x):
    pensiun_benefits = {}
    total_pensiun_benefits = 0
    for age, pvfb in enumerate(pvfb_values, start=1):
        age_key = f'{age}'
        if age == 46:
            age_key = '1'
        pensiun_benefits[age_key] = ((x - y) / (r - y)) * pvfb
        total_pensiun_benefits += pensiun_benefits[age_key]
    pensiun_benefits['Total'] = total_pensiun_benefits
    return pensiun_benefits

@app.route('/', methods=['GET', 'POST'])
def index():
    br_value = None
    pvfb_value = None
    pvfb_values_result = {}
    normal_contributions_result = {}
    ean_contributions_result = {}
    pensiun_benefits_result = {}

    if request.method == 'POST':
        try:
            k_percent_str = request.form['k_percent']
            k_percent_str = k_percent_str.replace(',', '.')
            k = float(k_percent_str) / 100.0

            y = int(request.form['y'])
            r = int(request.form['r'])
            sr_minus_1_str = request.form['sr_minus_1']
            sr_minus_1_str = sr_minus_1_str.replace('.', '').replace(',', '.')
            sr_minus_1 = float(sr_minus_1_str)

            x = int(request.form['x'])

            if k < 0 or k > 1 or y < 0 or r <= y or sr_minus_1 < 0:
                return "Masukan tidak valid. Pastikan k dalam rentang 0-100%, y >= 0, r > y, dan sr_minus_1 >= 0."

            pvfb_values = calculate_pvfb(k, y, r, sr_minus_1, x)

            pvfb_values_formatted = {f'PVFB{age}': locale.currency(pvfb, grouping=True, symbol='Rp') for age, pvfb in enumerate(pvfb_values, start=x)}

            normal_contributions = calculate_normal_contributions(pvfb_values, r, y)
            ean_contributions = calculate_ean(pvfb_values, r, y)
            pensiun_benefits = calculate_pensiun_benefits(pvfb_values, r, y, x)

            pvfb_values_result = pvfb_values_formatted
            normal_contributions_result = normal_contributions
            ean_contributions_result = ean_contributions
            pensiun_benefits_result = pensiun_benefits

            br, pvfb = calculate_brpvfb(k, y, r, sr_minus_1, x)
            br_value = locale.currency(br, grouping=True, symbol='Rp')
            pvfb_value = locale.currency(pvfb, grouping=True, symbol='Rp')
            

        except ValueError:
            return "Masukan tidak valid. Pastikan k (persentase), y, r, x, dan sr_minus_1 adalah angka."

    return render_template('index.html',br_value=br_value, pvfb_value=pvfb_value, pvfb_values=pvfb_values_result, normal_contributions=normal_contributions_result, ean_contributions=ean_contributions_result, pensiun_benefits=pensiun_benefits_result)

if __name__ == '__main__':
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
    app.jinja_env.filters['format_as_currency'] = format_as_currency
    app.run(debug=True)